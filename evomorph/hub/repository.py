import json
import os
import time
import hashlib
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class LocusPackage:
    name: str
    version: str
    author: str = ""
    description: str = ""
    genes_data: List[Dict] = field(default_factory=list)
    fitness_history: Dict[str, List[float]] = field(default_factory=dict)
    platform_scores: Dict[str, float] = field(default_factory=dict)
    cross_pool: str = "default"
    created_at: float = 0.0
    updated_at: float = 0.0
    checksum: str = ""

    def compute_checksum(self) -> str:
        data = json.dumps(self.genes_data, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]


class EvoHub:
    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = repo_path or os.path.expanduser("~/.evomorph/evohub")
        self.local_cache: Dict[str, LocusPackage] = {}
        self.remote_registry: Dict[str, Dict] = {}
        self._ensure_repo()

    def _ensure_repo(self):
        os.makedirs(self.repo_path, exist_ok=True)
        os.makedirs(os.path.join(self.repo_path, "packages"), exist_ok=True)
        os.makedirs(os.path.join(self.repo_path, "meta"), exist_ok=True)

    def publish(self, package: LocusPackage) -> bool:
        package.updated_at = time.time()
        if package.created_at == 0:
            package.created_at = package.updated_at
        package.checksum = package.compute_checksum()
        pkg_dir = os.path.join(self.repo_path, "packages", package.name)
        os.makedirs(pkg_dir, exist_ok=True)
        pkg_file = os.path.join(pkg_dir, f"{package.version}.json")
        with open(pkg_file, "w", encoding="utf-8") as f:
            json.dump(self._package_to_dict(package), f, ensure_ascii=False, indent=2)
        self.local_cache[package.name] = package
        return True

    def pull(self, name: str, version: Optional[str] = None) -> Optional[LocusPackage]:
        pkg_dir = os.path.join(self.repo_path, "packages", name)
        if not os.path.exists(pkg_dir):
            return None
        if version:
            pkg_file = os.path.join(pkg_dir, f"{version}.json")
        else:
            versions = [f for f in os.listdir(pkg_dir) if f.endswith(".json")]
            if not versions:
                return None
            versions.sort(reverse=True)
            pkg_file = os.path.join(pkg_dir, versions[0])
        if not os.path.exists(pkg_file):
            return None
        with open(pkg_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        package = self._dict_to_package(data)
        self.local_cache[name] = package
        return package

    def search(self, query: str) -> List[LocusPackage]:
        results = []
        pkg_base = os.path.join(self.repo_path, "packages")
        if not os.path.exists(pkg_base):
            return results
        for name in os.listdir(pkg_base):
            pkg_dir = os.path.join(pkg_base, name)
            if not os.path.isdir(pkg_dir):
                continue
            if query.lower() in name.lower():
                pkg = self.pull(name)
                if pkg:
                    results.append(pkg)
        return results

    def list_packages(self) -> List[str]:
        pkg_base = os.path.join(self.repo_path, "packages")
        if not os.path.exists(pkg_base):
            return []
        return [d for d in os.listdir(pkg_base)
                if os.path.isdir(os.path.join(pkg_base, d))]

    def upload_fitness_data(self, package_name: str, platform: str,
                            fitness_score: float, anonymous: bool = True):
        meta_dir = os.path.join(self.repo_path, "meta", package_name)
        os.makedirs(meta_dir, exist_ok=True)
        fitness_file = os.path.join(meta_dir, "fitness_history.json")
        history = []
        if os.path.exists(fitness_file):
            with open(fitness_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        entry = {
            "platform": platform,
            "fitness": fitness_score,
            "timestamp": time.time(),
            "anonymous": anonymous,
        }
        history.append(entry)
        with open(fitness_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def get_fitness_history(self, package_name: str) -> List[Dict]:
        fitness_file = os.path.join(self.repo_path, "meta", package_name, "fitness_history.json")
        if not os.path.exists(fitness_file):
            return []
        with open(fitness_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_best_variant(self, package_name: str, platform: str) -> Optional[Dict]:
        history = self.get_fitness_history(package_name)
        platform_entries = [e for e in history if e.get("platform") == platform]
        if not platform_entries:
            return None
        return max(platform_entries, key=lambda x: x.get("fitness", 0))

    def _package_to_dict(self, package: LocusPackage) -> Dict:
        return {
            "name": package.name,
            "version": package.version,
            "author": package.author,
            "description": package.description,
            "genes_data": package.genes_data,
            "fitness_history": package.fitness_history,
            "platform_scores": package.platform_scores,
            "cross_pool": package.cross_pool,
            "created_at": package.created_at,
            "updated_at": package.updated_at,
            "checksum": package.checksum,
        }

    def _dict_to_package(self, data: Dict) -> LocusPackage:
        return LocusPackage(
            name=data.get("name", ""),
            version=data.get("version", "0.1.0"),
            author=data.get("author", ""),
            description=data.get("description", ""),
            genes_data=data.get("genes_data", []),
            fitness_history=data.get("fitness_history", {}),
            platform_scores=data.get("platform_scores", {}),
            cross_pool=data.get("cross_pool", "default"),
            created_at=data.get("created_at", 0),
            updated_at=data.get("updated_at", 0),
            checksum=data.get("checksum", ""),
        )
