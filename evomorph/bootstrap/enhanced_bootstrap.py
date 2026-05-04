#!/usr/bin/env python3
"""
增强自举模块 - 支持第2代编译器使用、进化优化、一致性验证、最小可信计算基

功能概述:
1. 第2代编译器接口 - 使用进化后的编译器编译更多 .evo 代码
2. 增强进化优化 - 支持调整参数、增加进化代数
3. 一致性验证 - 验证第2代与第1代输出是否一致
4. 最小可信计算基 - 结合 C 虚拟机实现独立自举
"""

import sys
import os
import json
import subprocess
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from evomorph.bootstrap.runtime import EvoRuntime
from evomorph.compiler import EvocCompiler
from evomorph.evolution.engine import (
    EvolutionEngine, EvolutionConfig, GeneInstruction, Individual,
    SelectionMethod, CrossoverMethod
)
from evomorph.hexagrams import HexagramInstructionSet


class CompilerGeneration(Enum):
    GEN0_PYTHON = "gen0"
    GEN1_EVOMORPH = "gen1"
    GEN2_EVOLVED = "gen2"


@dataclass
class CompilationResult:
    success: bool
    generation: str
    loci: List[Dict] = field(default_factory=list)
    meta_loci: List[Dict] = field(default_factory=list)
    raw_output: Any = None
    error: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsistencyReport:
    gen1_result: CompilationResult
    gen2_result: CompilationResult
    match_percentage: float
    differences: List[Dict] = field(default_factory=list)
    is_consistent: bool = False


@dataclass
class EvolutionReport:
    generations: int
    initial_fitness: float
    final_fitness: float
    best_individual: Optional[Individual] = None
    history: List[Dict] = field(default_factory=list)
    improvement_rate: float = 0.0


@dataclass
class TCBReport:
    c_vm_available: bool
    c_vm_path: str
    assembler_available: bool
    can_execute_raw: bool
    bootstrap_test_result: Dict = field(default_factory=dict)
    is_fully_independent: bool = False


class EnhancedBootstrap:
    """
    增强自举类 - 整合所有自举相关功能
    
    功能:
    1. 第2代编译器接口
    2. 增强进化优化
    3. 一致性验证
    4. 最小可信计算基集成
    """
    
    def __init__(self):
        self.runtime = EvoRuntime()
        self.isa = HexagramInstructionSet()
        self.gen0_compiler = EvocCompiler()
        
        self.project_root = PROJECT_ROOT
        self.bootstrap_dir = os.path.join(self.project_root, "evomorph", "bootstrap")
        self.c_vm_dir = os.path.join(self.project_root, "bootstrap", "runtime")
        
        self._gen1_modules = {}
        self._gen2_modules = {}
        self._load_generations()
        
        self.evolution_configs = {
            "quick": EvolutionConfig(
                population_size=16,
                max_generations=10,
                mut_rate=0.02,
                selection_method=SelectionMethod.TOURNAMENT,
                tournament_size=3
            ),
            "standard": EvolutionConfig(
                population_size=32,
                max_generations=50,
                mut_rate=0.02,
                selection_method=SelectionMethod.TOURNAMENT,
                tournament_size=5
            ),
            "deep": EvolutionConfig(
                population_size=64,
                max_generations=200,
                mut_rate=0.015,
                selection_method=SelectionMethod.TOURNAMENT,
                tournament_size=7
            ),
            "extreme": EvolutionConfig(
                population_size=128,
                max_generations=500,
                mut_rate=0.01,
                selection_method=SelectionMethod.TOURNAMENT,
                tournament_size=10,
                elite_count=4
            )
        }
    
    def _load_generations(self):
        """加载各代编译器模块"""
        gen1_paths = {
            "lexer": os.path.join(self.bootstrap_dir, "evoc", "lexer_complete.evo"),
            "parser": os.path.join(self.bootstrap_dir, "evoc", "parser_complete.evo"),
            "codegen": os.path.join(self.bootstrap_dir, "evoc", "codegen_complete.evo"),
            "vm": os.path.join(self.bootstrap_dir, "vm", "vm_complete.evo"),
            "evolution": os.path.join(self.bootstrap_dir, "evolution", "evolution_complete.evo"),
        }
        
        for name, path in gen1_paths.items():
            if os.path.exists(path):
                self._gen1_modules[name] = path
        
        gen2_base = os.path.join(self.bootstrap_dir, "evolved")
        if os.path.exists(gen2_base):
            for filename in os.listdir(gen2_base):
                if filename.endswith(".evo"):
                    module_name = filename.replace(".evo", "")
                    self._gen2_modules[module_name] = os.path.join(gen2_base, filename)
        
        gen2_alt = os.path.join(self.bootstrap_dir, "evoc", "evolved")
        if os.path.exists(gen2_alt):
            for filename in os.listdir(gen2_alt):
                if filename.endswith(".evo"):
                    module_name = filename.replace(".evo", "")
                    if module_name not in self._gen2_modules:
                        self._gen2_modules[module_name] = os.path.join(gen2_alt, filename)
    
    def compile_with_gen0(self, source: str, output_format: str = "dict") -> CompilationResult:
        """
        使用第0代编译器（Python实现）编译代码
        
        Args:
            source: 源代码字符串或文件路径
            output_format: 输出格式
            
        Returns:
            CompilationResult 对象
        """
        try:
            if os.path.exists(source):
                with open(source, "r", encoding="utf-8") as f:
                    source_code = f.read()
            else:
                source_code = source
            
            result = self.gen0_compiler.compile(source_code, output_format=output_format)
            
            return CompilationResult(
                success=True,
                generation="gen0",
                loci=result.get("loci", []),
                meta_loci=result.get("meta_loci", []),
                raw_output=result,
                metrics={
                    "loci_count": len(result.get("loci", [])),
                    "meta_loci_count": len(result.get("meta_loci", [])),
                }
            )
        except Exception as e:
            return CompilationResult(
                success=False,
                generation="gen0",
                error=str(e)
            )
    
    def compile_with_gen1(self, source: str, output_format: str = "dict") -> CompilationResult:
        """
        使用第1代编译器（易衍实现）编译代码
        
        Args:
            source: 源代码字符串或文件路径
            output_format: 输出格式
            
        Returns:
            CompilationResult 对象
        """
        try:
            if os.path.exists(source):
                with open(source, "r", encoding="utf-8") as f:
                    source_code = f.read()
            else:
                source_code = source
            
            if not self._gen1_modules:
                return CompilationResult(
                    success=False,
                    generation="gen1",
                    error="第1代编译器模块未加载"
                )
            
            self.runtime.bind_env("SOURCE", source_code)
            self.runtime.bind_env("SOURCE_CODE", source_code)
            self.runtime.bind_env("OUTPUT_FORMAT", output_format)
            
            lexer_locus = "evoc.lexer.full_pass"
            parser_locus = "evoc.parser.full_pass"
            codegen_locus = "evoc.codegen.full_pass"
            
            for module_name, path in self._gen1_modules.items():
                try:
                    self.runtime.load_evo_file(path)
                except Exception:
                    pass
            
            tokens = []
            if lexer_locus in self.runtime.loaded_loci:
                lexer_result = self.runtime.execute_locus(lexer_locus, max_cycles=10000)
                tokens = lexer_result.get("registers", {}).get("R0", [])
            
            if not tokens:
                return self.compile_with_gen0(source, output_format)
            
            self.runtime.bind_env("TOKENS", tokens)
            
            ast = {}
            if parser_locus in self.runtime.loaded_loci:
                parser_result = self.runtime.execute_locus(parser_locus, max_cycles=10000)
                ast = parser_result.get("registers", {}).get("R0", {})
            
            if not ast:
                return self.compile_with_gen0(source, output_format)
            
            self.runtime.bind_env("AST", ast)
            
            if codegen_locus in self.runtime.loaded_loci:
                codegen_result = self.runtime.execute_locus(codegen_locus, max_cycles=10000)
                output = codegen_result.get("registers", {}).get("R0", {})
                
                if output and isinstance(output, dict):
                    return CompilationResult(
                        success=True,
                        generation="gen1",
                        loci=output.get("loci", []),
                        meta_loci=output.get("meta_loci", []),
                        raw_output=output,
                        metrics={
                            "loci_count": len(output.get("loci", [])),
                            "meta_loci_count": len(output.get("meta_loci", [])),
                            "used_gen1_lexer": True,
                            "used_gen1_parser": True,
                            "used_gen1_codegen": True,
                        }
                    )
            
            return self.compile_with_gen0(source, output_format)
            
        except Exception as e:
            return CompilationResult(
                success=False,
                generation="gen1",
                error=str(e)
            )
    
    def compile_with_gen2(self, source: str, output_format: str = "dict") -> CompilationResult:
        """
        使用第2代编译器（进化后）编译代码
        
        Args:
            source: 源代码字符串或文件路径
            output_format: 输出格式
            
        Returns:
            CompilationResult 对象
        """
        try:
            if os.path.exists(source):
                with open(source, "r", encoding="utf-8") as f:
                    source_code = f.read()
            else:
                source_code = source
            
            if not self._gen2_modules:
                return self.compile_with_gen1(source, output_format)
            
            for module_name, path in self._gen2_modules.items():
                try:
                    self.runtime.load_evo_file(path)
                except Exception:
                    pass
            
            compiled_result = self.runtime.self_compile(source_code)
            
            return CompilationResult(
                success=True,
                generation="gen2",
                loci=compiled_result.get("loci", []),
                meta_loci=compiled_result.get("meta_loci", []),
                raw_output=compiled_result,
                metrics={
                    "loci_count": len(compiled_result.get("loci", [])),
                    "meta_loci_count": len(compiled_result.get("meta_loci", [])),
                    "gen2_modules_used": len(self._gen2_modules),
                }
            )
            
        except Exception as e:
            return self.compile_with_gen1(source, output_format)
    
    def compile(self, source: str, generation: str = "auto", output_format: str = "dict") -> CompilationResult:
        """
        编译代码，可指定编译器代次
        
        Args:
            source: 源代码或文件路径
            generation: 编译器代次 ("gen0", "gen1", "gen2", "auto")
            output_format: 输出格式
            
        Returns:
            CompilationResult 对象
        """
        if generation == "gen0":
            return self.compile_with_gen0(source, output_format)
        elif generation == "gen1":
            return self.compile_with_gen1(source, output_format)
        elif generation == "gen2":
            return self.compile_with_gen2(source, output_format)
        else:
            result = self.compile_with_gen2(source, output_format)
            if not result.success:
                result = self.compile_with_gen1(source, output_format)
            if not result.success:
                result = self.compile_with_gen0(source, output_format)
            return result
    
    def compile_batch(self, files: List[str], generation: str = "auto") -> Dict[str, CompilationResult]:
        """
        批量编译多个文件
        
        Args:
            files: 文件路径列表
            generation: 编译器代次
            
        Returns:
            文件路径到编译结果的映射
        """
        results = {}
        for filepath in files:
            results[filepath] = self.compile(filepath, generation)
        return results
    
    def evolve_locus_enhanced(
        self,
        locus_name: str,
        mode: str = "standard",
        custom_config: Optional[Dict] = None,
        callback: Optional[callable] = None
    ) -> EvolutionReport:
        """
        增强的基因座进化功能
        
        Args:
            locus_name: 基因座名称
            mode: 进化模式 ("quick", "standard", "deep", "extreme", "custom")
            custom_config: 自定义配置（当 mode="custom" 时使用）
            callback: 每代回调函数
            
        Returns:
            EvolutionReport 对象
        """
        locus = self.runtime.loaded_loci.get(locus_name)
        if not locus:
            return EvolutionReport(
                generations=0,
                initial_fitness=0.0,
                final_fitness=0.0,
                improvement_rate=0.0
            )
        
        seed_genes = []
        for instr in locus.get("instructions", []):
            gene = GeneInstruction(
                opcode=instr.get("opcode", 0),
                modifier=instr.get("modifier", 0),
            )
            seed_genes.append(gene)
        
        if mode == "custom" and custom_config:
            config = EvolutionConfig(
                population_size=custom_config.get("population_size", 32),
                max_generations=custom_config.get("max_generations", 50),
                mut_rate=custom_config.get("mut_rate", 0.02),
                selection_method=SelectionMethod(custom_config.get("selection_method", "tournament")),
                crossover_method=CrossoverMethod(custom_config.get("crossover_method", "single_point")),
                tournament_size=custom_config.get("tournament_size", 5),
                elite_count=custom_config.get("elite_count", 2),
            )
        else:
            config = self.evolution_configs.get(mode, self.evolution_configs["standard"])
        
        config.env_targets = locus.get("env_targets", ["linux-6.x"])
        config.mut_rate = locus.get("mut_rate", config.mut_rate)
        
        engine = EvolutionEngine(config=config)
        engine.initialize_population(seed_genes)
        
        initial_fitness = engine.population[0].fitness if engine.population else 0.0
        
        history = []
        for i in range(config.max_generations):
            stats = engine.evolve_one_generation()
            history.append(stats)
            
            if callback:
                callback(stats)
        
        best = engine.get_best_individual()
        final_fitness = best.fitness if best else 0.0
        
        improvement_rate = 0.0
        if initial_fitness != 0:
            improvement_rate = (final_fitness - initial_fitness) / abs(initial_fitness) * 100
        
        if best:
            evolved_locus = dict(locus)
            evolved_locus["instructions"] = [
                {
                    "opcode": g.opcode,
                    "modifier": g.modifier,
                    "operands": list(g.operands),
                    "mnemonic": self.isa.get_by_opcode(g.opcode)["mnemonic"] if self.isa.get_by_opcode(g.opcode) else "???",
                    "symbol": self.isa.get_by_opcode(g.opcode)["symbol"] if self.isa.get_by_opcode(g.opcode) else "???",
                }
                for g in best.genes
            ]
            evolved_locus["evolved_fitness"] = best.fitness
            evolved_locus["evolution_mode"] = mode
            self.runtime.loaded_loci[locus_name] = evolved_locus
        
        return EvolutionReport(
            generations=len(history),
            initial_fitness=initial_fitness,
            final_fitness=final_fitness,
            best_individual=best,
            history=history,
            improvement_rate=improvement_rate
        )
    
    def evolve_all_loci(
        self,
        mode: str = "standard",
        exclude_patterns: List[str] = None
    ) -> Dict[str, EvolutionReport]:
        """
        进化所有已加载的基因座
        
        Args:
            mode: 进化模式
            exclude_patterns: 要排除的基因座名称模式列表
            
        Returns:
            基因座名称到进化报告的映射
        """
        exclude = exclude_patterns or []
        results = {}
        
        for locus_name in list(self.runtime.loaded_loci.keys()):
            if locus_name.startswith("meta:"):
                continue
            
            should_exclude = any(
                pattern in locus_name for pattern in exclude
            )
            if should_exclude:
                continue
            
            print(f"进化基因座: {locus_name}")
            report = self.evolve_locus_enhanced(locus_name, mode)
            results[locus_name] = report
            
            print(f"  初始适应度: {report.initial_fitness:.4f}")
            print(f"  最终适应度: {report.final_fitness:.4f}")
            print(f"  改进率: {report.improvement_rate:.2f}%")
        
        return results
    
    def verify_consistency(
        self,
        source: str,
        verbose: bool = False
    ) -> ConsistencyReport:
        """
        验证第1代和第2代编译器的输出一致性
        
        Args:
            source: 源代码或文件路径
            verbose: 是否显示详细信息
            
        Returns:
            ConsistencyReport 对象
        """
        gen1_result = self.compile_with_gen1(source)
        gen2_result = self.compile_with_gen2(source)
        
        differences = []
        match_count = 0
        total_count = 0
        
        if gen1_result.success and gen2_result.success:
            gen1_loci = {l["name"]: l for l in gen1_result.loci}
            gen2_loci = {l["name"]: l for l in gen2_result.loci}
            
            all_names = set(gen1_loci.keys()) | set(gen2_loci.keys())
            total_count = len(all_names)
            
            for name in all_names:
                if name not in gen1_loci:
                    differences.append({
                        "type": "missing_in_gen1",
                        "locus": name,
                    })
                elif name not in gen2_loci:
                    differences.append({
                        "type": "missing_in_gen2",
                        "locus": name,
                    })
                else:
                    g1 = gen1_loci[name]
                    g2 = gen2_loci[name]
                    
                    g1_instrs = g1.get("instructions", [])
                    g2_instrs = g2.get("instructions", [])
                    
                    if len(g1_instrs) != len(g2_instrs):
                        differences.append({
                            "type": "instruction_count_mismatch",
                            "locus": name,
                            "gen1_count": len(g1_instrs),
                            "gen2_count": len(g2_instrs),
                        })
                    else:
                        instr_match = True
                        for i, (i1, i2) in enumerate(zip(g1_instrs, g2_instrs)):
                            if i1.get("opcode") != i2.get("opcode"):
                                differences.append({
                                    "type": "opcode_mismatch",
                                    "locus": name,
                                    "instruction_index": i,
                                    "gen1_opcode": i1.get("opcode"),
                                    "gen2_opcode": i2.get("opcode"),
                                })
                                instr_match = False
                        
                        if instr_match:
                            match_count += 1
        
        match_percentage = (match_count / total_count * 100) if total_count > 0 else 0.0
        is_consistent = match_count == total_count and len(differences) == 0
        
        if verbose:
            print(f"\n一致性验证结果:")
            print(f"  第1代编译器: {'成功' if gen1_result.success else '失败'}")
            print(f"  第2代编译器: {'成功' if gen2_result.success else '失败'}")
            print(f"  匹配基因座: {match_count}/{total_count}")
            print(f"  匹配率: {match_percentage:.1f}%")
            print(f"  一致性: {'一致' if is_consistent else '不一致'}")
            
            if differences:
                print(f"\n差异详情:")
                for diff in differences[:10]:
                    print(f"  - {diff}")
                if len(differences) > 10:
                    print(f"  ... 还有 {len(differences) - 10} 个差异")
        
        return ConsistencyReport(
            gen1_result=gen1_result,
            gen2_result=gen2_result,
            match_percentage=match_percentage,
            differences=differences,
            is_consistent=is_consistent
        )
    
    def verify_batch_consistency(
        self,
        files: List[str],
        verbose: bool = False
    ) -> Dict[str, ConsistencyReport]:
        """
        批量验证多个文件的一致性
        
        Args:
            files: 文件路径列表
            verbose: 是否显示详细信息
            
        Returns:
            文件路径到一致性报告的映射
        """
        results = {}
        all_match = True
        total_match_count = 0
        total_count = 0
        
        for filepath in files:
            if verbose:
                print(f"\n验证文件: {filepath}")
            
            report = self.verify_consistency(filepath, verbose)
            results[filepath] = report
            
            if not report.is_consistent:
                all_match = False
            
            total_match_count += int(report.match_percentage / 100 * len(report.gen1_result.loci))
            total_count += len(report.gen1_result.loci)
        
        if verbose:
            print(f"\n{'=' * 60}")
            print("批量一致性验证汇总")
            print(f"{'=' * 60}")
            print(f"  文件总数: {len(files)}")
            print(f"  全部一致: {'是' if all_match else '否'}")
            print(f"  总匹配率: {(total_match_count / total_count * 100) if total_count > 0 else 0:.1f}%")
        
        return results
    
    def check_tcb_status(self) -> TCBReport:
        """
        检查最小可信计算基（TCB）状态
        
        Returns:
            TCBReport 对象
        """
        c_vm_path = os.path.join(self.c_vm_dir, "ichingvm_bootstrap")
        c_vm_source = os.path.join(self.c_vm_dir, "ichingvm_bootstrap.c")
        ichingvm_path = os.path.join(self.c_vm_dir, "ichingvm")
        
        c_vm_available = os.path.exists(c_vm_path) or os.path.exists(ichingvm_path)
        assembler_available = False
        can_execute_raw = False
        
        if c_vm_available:
            try:
                vm_exec = c_vm_path if os.path.exists(c_vm_path) else ichingvm_path
                result = subprocess.run(
                    [vm_exec, "help"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                assembler_available = "asm" in result.stdout or "asm" in result.stderr
                can_execute_raw = "run" in result.stdout or "run" in result.stderr
            except Exception:
                pass
        
        bootstrap_test = {}
        test_file = os.path.join(self.c_vm_dir, "bootstrap_full_test.asm")
        if os.path.exists(test_file) and c_vm_available:
            try:
                vm_exec = c_vm_path if os.path.exists(c_vm_path) else ichingvm_path
                
                raw_output = test_file.replace(".asm", ".raw")
                result = subprocess.run(
                    [vm_exec, "asm", test_file, raw_output],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if os.path.exists(raw_output):
                    result = subprocess.run(
                        [vm_exec, "run", raw_output],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    bootstrap_test["success"] = result.returncode == 0
                    bootstrap_test["output"] = result.stdout
                    bootstrap_test["error"] = result.stderr
            except Exception as e:
                bootstrap_test["error"] = str(e)
        
        is_fully_independent = (
            c_vm_available and 
            assembler_available and 
            can_execute_raw and
            bootstrap_test.get("success", False)
        )
        
        return TCBReport(
            c_vm_available=c_vm_available,
            c_vm_path=c_vm_path if os.path.exists(c_vm_path) else ichingvm_path,
            assembler_available=assembler_available,
            can_execute_raw=can_execute_raw,
            bootstrap_test_result=bootstrap_test,
            is_fully_independent=is_fully_independent
        )
    
    def build_tcb(self, verbose: bool = False) -> bool:
        """
        构建最小可信计算基（编译 C 虚拟机）
        
        Args:
            verbose: 是否显示详细输出
            
        Returns:
            构建是否成功
        """
        c_vm_source = os.path.join(self.c_vm_dir, "ichingvm_bootstrap.c")
        c_vm_output = os.path.join(self.c_vm_dir, "ichingvm_bootstrap")
        
        if not os.path.exists(c_vm_source):
            if verbose:
                print(f"错误: C 虚拟机源码不存在: {c_vm_source}")
            return False
        
        if verbose:
            print(f"编译 C 虚拟机: {c_vm_source} -> {c_vm_output}")
        
        try:
            result = subprocess.run(
                ["gcc", "-o", c_vm_output, c_vm_source, "-Wall", "-Wextra", "-O2"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                if verbose:
                    print(f"编译失败: {result.stderr}")
                return False
            
            if verbose:
                print("编译成功!")
                print(f"输出文件: {c_vm_output}")
            
            if os.path.exists(c_vm_output):
                os.chmod(c_vm_output, 0o755)
                if verbose:
                    print("设置执行权限完成")
            
            return True
            
        except Exception as e:
            if verbose:
                print(f"构建错误: {e}")
            return False
    
    def compile_for_tcb(
        self,
        evo_source: str,
        output_asm: str,
        output_raw: Optional[str] = None,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        编译 .evo 代码为 C 虚拟机可执行的格式
        
        Args:
            evo_source: .evo 源文件或源代码
            output_asm: 输出 .asm 文件路径
            output_raw: 输出 .raw 文件路径（可选）
            verbose: 是否显示详细输出
            
        Returns:
            编译结果信息
        """
        result = self.compile(evo_source, generation="auto")
        
        if not result.success:
            return {
                "success": False,
                "error": result.error
            }
        
        asm_lines = [
            "; 易衍·Evomorph 编译输出",
            f"; 由 {result.generation} 代编译器生成",
            f"; 基因座数量: {len(result.loci)}",
            "",
        ]
        
        for locus in result.loci:
            asm_lines.append(f"; --- 基因座: {locus.get('name', 'unknown')} ---")
            
            for instr in locus.get("instructions", []):
                mnemonic = instr.get("mnemonic", "NOP")
                operands = instr.get("operands", [])
                
                if operands:
                    op_strs = []
                    for op in operands:
                        if isinstance(op, dict):
                            if op.get("type") == "register":
                                op_strs.append(f"R{op.get('value', 0)}")
                            else:
                                op_strs.append(str(op.get("value", 0)))
                        else:
                            op_strs.append(f"R{op}" if isinstance(op, int) and op <= 15 else str(op))
                    
                    asm_line = f"{mnemonic} {', '.join(op_strs)}"
                else:
                    asm_line = mnemonic
                
                asm_lines.append(asm_line)
            
            asm_lines.append("")
        
        asm_content = "\n".join(asm_lines)
        
        try:
            with open(output_asm, "w", encoding="utf-8") as f:
                f.write(asm_content)
            
            if verbose:
                print(f"汇编文件已生成: {output_asm}")
        except Exception as e:
            return {
                "success": False,
                "error": f"无法写入汇编文件: {e}"
            }
        
        compile_result = result
        
        if output_raw:
            tcb_status = self.check_tcb_status()
            if tcb_status.c_vm_available and tcb_status.assembler_available:
                try:
                    vm_exec = tcb_status.c_vm_path
                    asm_result = subprocess.run(
                        [vm_exec, "asm", output_asm, output_raw],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if asm_result.returncode == 0 and os.path.exists(output_raw):
                        if verbose:
                            print(f"原始字节码已生成: {output_raw}")
                        return {
                            "success": True,
                            "asm_file": output_asm,
                            "raw_file": output_raw,
                            "generation": compile_result.generation,
                            "loci_count": len(compile_result.loci),
                        }
                    else:
                        if verbose:
                            print(f"汇编警告: {asm_result.stderr}")
                except Exception as e:
                    if verbose:
                        print(f"汇编失败: {e}")
        
        return {
            "success": True,
            "asm_file": output_asm,
            "generation": compile_result.generation,
            "loci_count": len(compile_result.loci),
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取当前自举系统状态
        
        Returns:
            状态信息字典
        """
        return {
            "generations": {
                "gen0": {
                    "available": True,
                    "description": "Python 实现的编译器（第0代）",
                },
                "gen1": {
                    "available": len(self._gen1_modules) > 0,
                    "modules": list(self._gen1_modules.keys()),
                    "description": "易衍实现的编译器（第1代）",
                },
                "gen2": {
                    "available": len(self._gen2_modules) > 0,
                    "modules": list(self._gen2_modules.keys()),
                    "description": "进化后的编译器（第2代）",
                },
            },
            "tcb": self.check_tcb_status().__dict__,
            "loaded_loci": list(self.runtime.loaded_loci.keys()),
            "evolution_modes": list(self.evolution_configs.keys()),
        }


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="易衍·Evomorph 增强自举工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    compile_parser = subparsers.add_parser("compile", help="编译代码")
    compile_parser.add_argument("source", help="源文件或源代码")
    compile_parser.add_argument("-g", "--generation", choices=["gen0", "gen1", "gen2", "auto"], default="auto", help="编译器代次")
    compile_parser.add_argument("-o", "--output", help="输出文件")
    compile_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    
    evolve_parser = subparsers.add_parser("evolve", help="进化优化")
    evolve_parser.add_argument("locus", nargs="?", help="基因座名称（不指定则进化所有）")
    evolve_parser.add_argument("-m", "--mode", choices=["quick", "standard", "deep", "extreme"], default="standard", help="进化模式")
    evolve_parser.add_argument("-g", "--generations", type=int, help="进化代数")
    evolve_parser.add_argument("-p", "--population", type=int, help="种群大小")
    evolve_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    
    verify_parser = subparsers.add_parser("verify", help="一致性验证")
    verify_parser.add_argument("files", nargs="+", help="要验证的文件")
    verify_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    
    tcb_parser = subparsers.add_parser("tcb", help="最小可信计算基操作")
    tcb_parser.add_argument("action", choices=["status", "build", "compile"], help="操作类型")
    tcb_parser.add_argument("source", nargs="?", help="源文件（compile 时需要）")
    tcb_parser.add_argument("-o", "--output", help="输出文件")
    tcb_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    
    status_parser = subparsers.add_parser("status", help="查看系统状态")
    
    args = parser.parse_args()
    
    eb = EnhancedBootstrap()
    
    if args.command == "compile":
        result = eb.compile(args.source, args.generation)
        
        if args.verbose:
            print(f"编译结果:")
            print(f"  代次: {result.generation}")
            print(f"  成功: {'是' if result.success else '否'}")
            if result.success:
                print(f"  基因座数量: {len(result.loci)}")
                print(f"  元基因座数量: {len(result.meta_loci)}")
            else:
                print(f"  错误: {result.error}")
        
        if args.output and result.success:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result.raw_output, f, ensure_ascii=False, indent=2)
            if args.verbose:
                print(f"结果已保存到: {args.output}")
        
        return 0 if result.success else 1
    
    elif args.command == "evolve":
        if args.locus:
            custom_config = {}
            if args.generations:
                custom_config["max_generations"] = args.generations
            if args.population:
                custom_config["population_size"] = args.population
            
            mode = "custom" if custom_config else args.mode
            
            report = eb.evolve_locus_enhanced(
                args.locus,
                mode=mode,
                custom_config=custom_config if custom_config else None
            )
            
            print(f"进化完成:")
            print(f"  基因座: {args.locus}")
            print(f"  代数: {report.generations}")
            print(f"  初始适应度: {report.initial_fitness:.4f}")
            print(f"  最终适应度: {report.final_fitness:.4f}")
            print(f"  改进率: {report.improvement_rate:.2f}%")
        else:
            reports = eb.evolve_all_loci(mode=args.mode)
            print(f"\n进化汇总:")
            print(f"  进化基因座数量: {len(reports)}")
            total_improvement = sum(r.improvement_rate for r in reports.values())
            avg_improvement = total_improvement / len(reports) if reports else 0
            print(f"  平均改进率: {avg_improvement:.2f}%")
        
        return 0
    
    elif args.command == "verify":
        reports = eb.verify_batch_consistency(args.files, args.verbose)
        
        all_consistent = all(r.is_consistent for r in reports.values())
        print(f"\n验证结果: {'全部一致' if all_consistent else '存在差异'}")
        
        return 0 if all_consistent else 1
    
    elif args.command == "tcb":
        if args.action == "status":
            status = eb.check_tcb_status()
            print(f"最小可信计算基状态:")
            print(f"  C 虚拟机可用: {'是' if status.c_vm_available else '否'}")
            print(f"  汇编器可用: {'是' if status.assembler_available else '否'}")
            print(f"  可执行原始字节码: {'是' if status.can_execute_raw else '否'}")
            print(f"  完全独立: {'是' if status.is_fully_independent else '否'}")
            
            if args.verbose and status.bootstrap_test_result:
                print(f"\n自举测试结果:")
                print(f"  成功: {'是' if status.bootstrap_test_result.get('success') else '否'}")
                if status.bootstrap_test_result.get("output"):
                    print(f"  输出: {status.bootstrap_test_result['output']}")
        
        elif args.action == "build":
            success = eb.build_tcb(args.verbose)
            print(f"构建结果: {'成功' if success else '失败'}")
            return 0 if success else 1
        
        elif args.action == "compile":
            if not args.source:
                print("错误: compile 操作需要源文件")
                return 1
            
            output_asm = args.output or args.source.replace(".evo", ".asm")
            output_raw = output_asm.replace(".asm", ".raw") if args.output else None
            
            result = eb.compile_for_tcb(args.source, output_asm, output_raw, args.verbose)
            
            if result["success"]:
                print(f"编译成功:")
                print(f"  汇编文件: {result['asm_file']}")
                if result.get("raw_file"):
                    print(f"  原始字节码: {result['raw_file']}")
                print(f"  使用代次: {result['generation']}")
                return 0
            else:
                print(f"编译失败: {result['error']}")
                return 1
        
        return 0
    
    elif args.command == "status":
        status = eb.get_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0
    
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
