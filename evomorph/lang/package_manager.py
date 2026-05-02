import os
import json
import hashlib
import shutil
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional, Set, Any, Callable, Union
from collections import defaultdict
from pathlib import Path


class PackageType(Enum):
    LIBRARY = "library"
    APPLICATION = "application"
    FRAMEWORK = "framework"
    PLUGIN = "plugin"


class DependencyConstraint(Enum):
    EXACT = "exact"
    COMPATIBLE = "compatible"
    AT_LEAST = "at_least"
    AT_MOST = "at_most"
    ANY = "any"


@dataclass
class Dependency:
    name: str
    version: str
    constraint: DependencyConstraint = DependencyConstraint.COMPATIBLE
    optional: bool = False
    dev_only: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "constraint": self.constraint.value,
            "optional": self.optional,
            "dev_only": self.dev_only,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Dependency':
        return cls(
            name=data["name"],
            version=data["version"],
            constraint=DependencyConstraint(data.get("constraint", "compatible")),
            optional=data.get("optional", False),
            dev_only=data.get("dev_only", False),
        )


@dataclass
class PackageManifest:
    name: str
    version: str
    package_type: PackageType = PackageType.LIBRARY
    description: str = ""
    authors: List[str] = field(default_factory=list)
    license: str = ""
    keywords: List[str] = field(default_factory=list)
    
    dependencies: List[Dependency] = field(default_factory=list)
    dev_dependencies: List[Dependency] = field(default_factory=list)
    
    entry_points: Dict[str, str] = field(default_factory=dict)
    exports: List[str] = field(default_factory=list)
    
    targets: List[str] = field(default_factory=lambda: ["linux-6.x"])
    min_evolang_version: str = "3.0"
    
    repository: str = ""
    homepage: str = ""
    documentation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "package_type": self.package_type.value,
            "description": self.description,
            "authors": list(self.authors),
            "license": self.license,
            "keywords": list(self.keywords),
            "dependencies": [d.to_dict() for d in self.dependencies],
            "dev_dependencies": [d.to_dict() for d in self.dev_dependencies],
            "entry_points": dict(self.entry_points),
            "exports": list(self.exports),
            "targets": list(self.targets),
            "min_evolang_version": self.min_evolang_version,
            "repository": self.repository,
            "homepage": self.homepage,
            "documentation": self.documentation,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PackageManifest':
        return cls(
            name=data["name"],
            version=data["version"],
            package_type=PackageType(data.get("package_type", "library")),
            description=data.get("description", ""),
            authors=data.get("authors", []),
            license=data.get("license", ""),
            keywords=data.get("keywords", []),
            dependencies=[Dependency.from_dict(d) for d in data.get("dependencies", [])],
            dev_dependencies=[Dependency.from_dict(d) for d in data.get("dev_dependencies", [])],
            entry_points=data.get("entry_points", {}),
            exports=data.get("exports", []),
            targets=data.get("targets", ["linux-6.x"]),
            min_evolang_version=data.get("min_evolang_version", "3.0"),
            repository=data.get("repository", ""),
            homepage=data.get("homepage", ""),
            documentation=data.get("documentation", ""),
        )
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'PackageManifest':
        return cls.from_dict(json.loads(json_str))


@dataclass
class InstalledPackage:
    manifest: PackageManifest
    install_path: str
    installed_at: float
    checksum: str = ""
    is_symlink: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest": self.manifest.to_dict(),
            "install_path": self.install_path,
            "installed_at": self.installed_at,
            "checksum": self.checksum,
            "is_symlink": self.is_symlink,
        }


class Version:
    def __init__(self, version_str: str):
        self.original = version_str
        self.major = 0
        self.minor = 0
        self.patch = 0
        self.pre_release: Optional[str] = None
        self.build: Optional[str] = None
        
        self._parse(version_str)
    
    def _parse(self, version_str: str):
        parts = version_str.split('+', 1)
        if len(parts) > 1:
            self.build = parts[1]
        
        main_part = parts[0]
        
        parts = main_part.split('-', 1)
        if len(parts) > 1:
            self.pre_release = parts[1]
        
        main_part = parts[0]
        
        parts = main_part.split('.')
        if len(parts) >= 1:
            self.major = int(parts[0])
        if len(parts) >= 2:
            self.minor = int(parts[1])
        if len(parts) >= 3:
            self.patch = int(parts[2])
    
    def to_tuple(self) -> Tuple[int, int, int, Optional[str], Optional[str]]:
        return (self.major, self.minor, self.patch, self.pre_release, self.build)
    
    def satisfies(self, constraint: DependencyConstraint, other: 'Version') -> bool:
        if constraint == DependencyConstraint.EXACT:
            return self.to_tuple() == other.to_tuple()
        
        elif constraint == DependencyConstraint.ANY:
            return True
        
        elif constraint == DependencyConstraint.AT_LEAST:
            return self.to_tuple() >= other.to_tuple()
        
        elif constraint == DependencyConstraint.AT_MOST:
            return self.to_tuple() <= other.to_tuple()
        
        elif constraint == DependencyConstraint.COMPATIBLE:
            if self.major != other.major:
                return False
            if self.major == 0:
                return self.minor == other.minor and self.patch >= other.patch
            return (self.minor > other.minor or 
                    (self.minor == other.minor and self.patch >= other.patch))
        
        return False
    
    def __str__(self) -> str:
        return self.original


class PackageRegistry:
    def __init__(self, registry_url: str = "https://hub.evomorph.org"):
        self.registry_url = registry_url
        self.cache: Dict[str, Dict[str, PackageManifest]] = defaultdict(dict)
    
    async def search(self, query: str) -> List[Dict]:
        return []
    
    async def get_package_info(self, name: str) -> Optional[Dict]:
        return None
    
    async def download_package(self, name: str, version: str, dest_path: str) -> bool:
        return False


class PackageManager:
    def __init__(self, 
                 project_root: Optional[str] = None,
                 registry_url: str = "https://hub.evomorph.org"):
        
        self.project_root = project_root or os.getcwd()
        self.packages_dir = os.path.join(self.project_root, ".evomorph", "packages")
        self.config_dir = os.path.join(self.project_root, ".evomorph")
        self.manifest_path = os.path.join(self.project_root, "evomorph.json")
        self.lock_path = os.path.join(self.project_root, "evomorph-lock.json")
        
        self.registry = PackageRegistry(registry_url)
        self.installed: Dict[str, InstalledPackage] = {}
        
        self._ensure_directories()
    
    def _ensure_directories(self):
        os.makedirs(self.packages_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
    
    def init_project(self, 
                      name: str,
                      version: str = "0.1.0",
                      package_type: PackageType = PackageType.LIBRARY,
                      description: str = "") -> PackageManifest:
        manifest = PackageManifest(
            name=name,
            version=version,
            package_type=package_type,
            description=description,
        )
        
        with open(self.manifest_path, 'w', encoding='utf-8') as f:
            f.write(manifest.to_json())
        
        return manifest
    
    def load_manifest(self) -> Optional[PackageManifest]:
        if not os.path.exists(self.manifest_path):
            return None
        
        with open(self.manifest_path, 'r', encoding='utf-8') as f:
            return PackageManifest.from_json(f.read())
    
    def save_manifest(self, manifest: PackageManifest):
        with open(self.manifest_path, 'w', encoding='utf-8') as f:
            f.write(manifest.to_json())
    
    def add_dependency(self, 
                        name: str,
                        version: str = "*",
                        constraint: DependencyConstraint = DependencyConstraint.COMPATIBLE,
                        dev_only: bool = False) -> bool:
        manifest = self.load_manifest()
        if not manifest:
            manifest = self.init_project(name="unnamed")
        
        dep = Dependency(
            name=name,
            version=version,
            constraint=constraint,
            dev_only=dev_only,
        )
        
        if dev_only:
            manifest.dev_dependencies.append(dep)
        else:
            manifest.dependencies.append(dep)
        
        self.save_manifest(manifest)
        return True
    
    def remove_dependency(self, name: str, dev_only: bool = False) -> bool:
        manifest = self.load_manifest()
        if not manifest:
            return False
        
        if dev_only:
            manifest.dev_dependencies = [
                d for d in manifest.dev_dependencies if d.name != name
            ]
        else:
            manifest.dependencies = [
                d for d in manifest.dependencies if d.name != name
            ]
        
        self.save_manifest(manifest)
        return True
    
    def resolve_dependencies(self) -> Dict[str, Dependency]:
        manifest = self.load_manifest()
        if not manifest:
            return {}
        
        resolved: Dict[str, Dependency] = {}
        
        all_deps = manifest.dependencies + manifest.dev_dependencies
        
        for dep in all_deps:
            if dep.name not in resolved:
                resolved[dep.name] = dep
        
        return resolved
    
    def install(self, 
                name: Optional[str] = None,
                version: Optional[str] = None,
                dev_only: bool = False) -> bool:
        if name:
            self.add_dependency(name, version or "*", dev_only=dev_only)
        
        resolved = self.resolve_dependencies()
        
        for dep_name, dep in resolved.items():
            install_path = os.path.join(self.packages_dir, dep_name)
            
            if not os.path.exists(install_path):
                success = self._install_from_registry(dep_name, dep.version, install_path)
                if not success:
                    success = self._install_from_local_cache(dep_name, dep.version, install_path)
                if not success:
                    return False
            
            checksum = self._compute_checksum(install_path)
            self.installed[dep_name] = InstalledPackage(
                manifest=PackageManifest(name=dep_name, version=dep.version),
                install_path=install_path,
                installed_at=os.path.getmtime(install_path),
                checksum=checksum,
            )
        
        self._save_lock_file()
        return True
    
    def _install_from_registry(self, name: str, version: str, dest_path: str) -> bool:
        return False
    
    def _install_from_local_cache(self, name: str, version: str, dest_path: str) -> bool:
        return False
    
    def _compute_checksum(self, path: str) -> str:
        hasher = hashlib.sha256()
        
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for file_name in sorted(files):
                    file_path = os.path.join(root, file_name)
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(8192), b''):
                            hasher.update(chunk)
        elif os.path.isfile(path):
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def _save_lock_file(self):
        lock_data = {
            "version": "1.0",
            "packages": {
                name: pkg.to_dict() 
                for name, pkg in self.installed.items()
            }
        }
        
        with open(self.lock_path, 'w', encoding='utf-8') as f:
            json.dump(lock_data, f, indent=2, ensure_ascii=False)
    
    def list_installed(self) -> Dict[str, InstalledPackage]:
        return dict(self.installed)
    
    def uninstall(self, name: str) -> bool:
        if name not in self.installed:
            return False
        
        pkg = self.installed[name]
        
        if os.path.exists(pkg.install_path):
            shutil.rmtree(pkg.install_path, ignore_errors=True)
        
        del self.installed[name]
        
        self.remove_dependency(name)
        self.remove_dependency(name, dev_only=True)
        
        self._save_lock_file()
        return True
    
    def update(self, name: Optional[str] = None) -> bool:
        return True
    
    def get_package_path(self, name: str) -> Optional[str]:
        if name in self.installed:
            return self.installed[name].install_path
        return None
    
    def list_exports(self, name: str) -> List[str]:
        if name not in self.installed:
            return []
        
        pkg = self.installed[name]
        
        evo_files = []
        for root, dirs, files in os.walk(pkg.install_path):
            for file_name in files:
                if file_name.endswith('.evo'):
                    evo_files.append(os.path.join(root, file_name))
        
        return evo_files


class ModuleSystem:
    def __init__(self, package_manager: Optional[PackageManager] = None):
        self.package_manager = package_manager or PackageManager()
        self.loaded_modules: Dict[str, Any] = {}
        self.search_paths: List[str] = []
        
        self._init_search_paths()
    
    def _init_search_paths(self):
        stdlib_path = os.path.join(os.path.dirname(__file__), "..", "stdlib")
        self.search_paths.append(os.path.abspath(stdlib_path))
        
        if self.package_manager:
            self.search_paths.append(self.package_manager.packages_dir)
    
    def add_search_path(self, path: str):
        abs_path = os.path.abspath(path)
        if abs_path not in self.search_paths:
            self.search_paths.insert(0, abs_path)
    
    def resolve_module(self, module_name: str) -> Optional[str]:
        for search_path in self.search_paths:
            candidate = os.path.join(search_path, f"{module_name}.evo")
            if os.path.exists(candidate):
                return candidate
            
            candidate = os.path.join(search_path, module_name, "__init__.evo")
            if os.path.exists(candidate):
                return candidate
            
            candidate = os.path.join(search_path, module_name)
            if os.path.isdir(candidate):
                for f in os.listdir(candidate):
                    if f.endswith('.evo'):
                        return os.path.join(candidate, f)
        
        if self.package_manager:
            pkg_path = self.package_manager.get_package_path(module_name)
            if pkg_path:
                for f in os.listdir(pkg_path):
                    if f.endswith('.evo'):
                        return os.path.join(pkg_path, f)
        
        return None
    
    def load_module(self, module_name: str) -> Optional[Any]:
        if module_name in self.loaded_modules:
            return self.loaded_modules[module_name]
        
        file_path = self.resolve_module(module_name)
        if not file_path:
            return None
        
        from evomorph.compiler import EvocCompiler
        from evomorph.bootstrap.runtime import EvoRuntime
        
        compiler = EvocCompiler()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            result = compiler.compile(source)
            
            module_data = {
                "name": module_name,
                "file_path": file_path,
                "compiled": result,
                "loci": {},
            }
            
            if isinstance(result, dict) and "loci" in result:
                for locus in result["loci"]:
                    locus_name = locus.get("name", "")
                    module_data["loci"][locus_name] = locus
            
            self.loaded_modules[module_name] = module_data
            return module_data
            
        except Exception:
            return None
    
    def get_locus(self, module_name: str, locus_name: str) -> Optional[Dict]:
        module = self.load_module(module_name)
        if not module:
            return None
        
        return module.get("loci", {}).get(locus_name)
    
    def list_available_modules(self) -> List[str]:
        modules = set()
        
        for search_path in self.search_paths:
            if not os.path.exists(search_path):
                continue
            
            for item in os.listdir(search_path):
                item_path = os.path.join(search_path, item)
                
                if item.endswith('.evo'):
                    modules.add(item[:-4])
                elif os.path.isdir(item_path):
                    if os.path.exists(os.path.join(item_path, "__init__.evo")):
                        modules.add(item)
                    else:
                        for f in os.listdir(item_path):
                            if f.endswith('.evo'):
                                modules.add(f"{item}.{f[:-4]}")
                                break
        
        return sorted(modules)
