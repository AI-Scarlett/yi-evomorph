import os
from typing import Dict, List, Optional, Any, Callable
from .runtime import EvoRuntime


class EvomorphBackend:
    """
    Evomorph 后端兼容性层。
    允许 Python 代码调用 Evomorph 实现，实现无缝切换。
    
    设计理念：
    - 提供与现有 Python 实现相同的接口
    - 内部使用 EvoRuntime 执行 Evomorph 代码
    - 支持在 Python 实现和 Evomorph 实现之间无缝切换
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.runtime = EvoRuntime()
        self.bootstrap_dir = os.path.dirname(os.path.abspath(__file__))
        self._loaded_loci: Dict[str, bool] = {}
        self._use_evomorph = True
        
        self._load_bootstrap_modules()
    
    def _load_bootstrap_modules(self):
        """加载所有自举模块"""
        modules_to_load = [
            # 编译器模块
            os.path.join(self.bootstrap_dir, "evoc", "lexer_complete.evo"),
            os.path.join(self.bootstrap_dir, "evoc", "parser_complete.evo"),
            os.path.join(self.bootstrap_dir, "evoc", "codegen_complete.evo"),
            # 虚拟机模块
            os.path.join(self.bootstrap_dir, "vm", "vm_complete.evo"),
            # 进化引擎模块
            os.path.join(self.bootstrap_dir, "evolution", "evolution_complete.evo"),
            # 语言系统模块
            os.path.join(self.bootstrap_dir, "lang", "types_complete.evo"),
            os.path.join(self.bootstrap_dir, "lang", "functions_complete.evo"),
            # 静态分析器模块
            os.path.join(self.bootstrap_dir, "analysis", "static_analyzer_complete.evo"),
        ]
        
        for module_path in modules_to_load:
            if os.path.exists(module_path):
                try:
                    self.runtime.load_evo_file(module_path)
                    self._loaded_loci[module_path] = True
                    print(f"[EvomorphBackend] 加载模块: {module_path}")
                except Exception as e:
                    print(f"[EvomorphBackend] 加载模块失败: {module_path}, 错误: {e}")
                    self._loaded_loci[module_path] = False
            else:
                print(f"[EvomorphBackend] 模块不存在: {module_path}")
                self._loaded_loci[module_path] = False
    
    def set_mode(self, use_evomorph: bool):
        """设置使用 Evomorph 实现还是 Python 实现"""
        self._use_evomorph = use_evomorph
        print(f"[EvomorphBackend] 切换到 {'Evomorph' if use_evomorph else 'Python'} 实现")
    
    def is_evomorph_available(self, module_name: str) -> bool:
        """检查特定模块的 Evomorph 实现是否可用"""
        return self._use_evomorph and self._is_module_loaded(module_name)
    
    def _is_module_loaded(self, module_name: str) -> bool:
        """检查模块是否已加载"""
        module_map = {
            "lexer": "evoc/lexer_complete.evo",
            "parser": "evoc/parser_complete.evo",
            "codegen": "evoc/codegen_complete.evo",
            "vm": "vm/vm_complete.evo",
            "evolution": "evolution/evolution_complete.evo",
            "types": "lang/types_complete.evo",
            "functions": "lang/functions_complete.evo",
            "static_analyzer": "analysis/static_analyzer_complete.evo",
        }
        
        if module_name in module_map:
            module_path = os.path.join(self.bootstrap_dir, module_map[module_name])
            return self._loaded_loci.get(module_path, False)
        
        return False
    
    def execute_locus(self, locus_name: str, inputs: Optional[Dict[str, Any]] = None, max_cycles: int = 1000) -> Dict[str, Any]:
        """
        执行指定的基因座。
        
        Args:
            locus_name: 基因座名称
            inputs: 输入参数
            max_cycles: 最大执行周期
        
        Returns:
            执行结果
        """
        if inputs:
            for key, value in inputs.items():
                self.runtime.bind_env(key, value)
        
        return self.runtime.execute_locus(locus_name, max_cycles=max_cycles)
    
    def compile_source(self, source: str, output_format: str = "dict") -> Dict[str, Any]:
        """
        编译 Evomorph 源代码。
        
        Args:
            source: 源代码字符串
            output_format: 输出格式（dict、json、evb）
        
        Returns:
            编译结果
        """
        if self.is_evomorph_available("lexer") and self.is_evomorph_available("parser") and self.is_evomorph_available("codegen"):
            return self._compile_using_evomorph(source, output_format)
        else:
            return self.runtime.compiler.compile(source, output_format=output_format)
    
    def _compile_using_evomorph(self, source: str, output_format: str) -> Dict[str, Any]:
        """使用 Evomorph 实现编译源代码"""
        self.runtime.bind_env("SOURCE", source)
        self.runtime.bind_env("SOURCE_CODE", source)
        self.runtime.bind_env("OUTPUT_FORMAT", output_format)
        
        lexer_result = self.execute_locus("evoc.lexer.full_pass", max_cycles=10000)
        if "error" in lexer_result:
            return {"error": f"词法分析失败: {lexer_result['error']}"}
        
        tokens = lexer_result.get("registers", {}).get("R0", [])
        if not tokens:
            tokens = lexer_result.get("registers", {}).get("R4", [])
        self.runtime.bind_env("TOKENS", tokens)
        self.runtime.bind_env("TOKEN_STREAM", tokens)
        
        parser_result = self.execute_locus("evoc.parser.full_pass", max_cycles=10000)
        if "error" in parser_result:
            return {"error": f"语法分析失败: {parser_result['error']}"}
        
        ast = parser_result.get("registers", {}).get("R0", {})
        if not ast:
            ast = parser_result.get("registers", {}).get("R2", {})
        self.runtime.bind_env("AST", ast)
        self.runtime.bind_env("OUTPUT_FORMAT", output_format)
        
        codegen_result = self.execute_locus("evoc.codegen.full_pass", max_cycles=10000)
        if "error" in codegen_result:
            return {"error": f"代码生成失败: {codegen_result['error']}"}
        
        output = codegen_result.get("registers", {}).get("R0", {})
        if not output:
            output = codegen_result.get("registers", {}).get("R4", {})
        
        return output if output else {"error": "代码生成未产生输出"}
    
    def execute_program(self, program: List[Dict[str, Any]], max_cycles: int = 10000) -> Dict[str, Any]:
        """
        执行字节码程序。
        
        Args:
            program: 字节码程序列表
            max_cycles: 最大执行周期
        
        Returns:
            执行结果
        """
        if self.is_evomorph_available("vm"):
            return self._execute_using_evomorph(program, max_cycles)
        else:
            vm = self.runtime.vm
            vm.reset()
            vm.load_program(program)
            state = vm.run(max_cycles=max_cycles)
            return {
                "state": state.name,
                "cycle_count": vm.cycle_count,
                "energy_cost": vm.energy_cost,
                "registers": {f"R{i}": vm.registers[i] for i in range(16)},
            }
    
    def _execute_using_evomorph(self, program: List[Dict[str, Any]], max_cycles: int) -> Dict[str, Any]:
        """使用 Evomorph 实现执行程序"""
        self.runtime.bind_env("PROGRAM", program)
        self.runtime.bind_env("MAX_CYCLES", max_cycles)
        
        result = self.execute_locus("evoc.vm.run", max_cycles=max_cycles + 100)
        return result
    
    def evolve_population(self, seed_genes: List[Dict[str, Any]], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        进化种群。
        
        Args:
            seed_genes: 种子基因列表
            config: 进化配置
        
        Returns:
            进化结果
        """
        if self.is_evomorph_available("evolution"):
            return self._evolve_using_evomorph(seed_genes, config)
        else:
            from evomorph.evolution.engine import EvolutionEngine, EvolutionConfig, GeneInstruction
            
            default_config = {
                "population_size": 32,
                "max_generations": 50,
                "mut_rate": 0.02,
                "env_targets": ["linux-6.x"],
            }
            
            if config:
                default_config.update(config)
            
            genes = [
                GeneInstruction(
                    opcode=g.get("opcode", 0),
                    modifier=g.get("modifier", 0),
                )
                for g in seed_genes
            ]
            
            evo_config = EvolutionConfig(
                population_size=default_config["population_size"],
                max_generations=default_config["max_generations"],
                mut_rate=default_config["mut_rate"],
                env_targets=default_config["env_targets"],
            )
            
            engine = EvolutionEngine(config=evo_config)
            engine.initialize_population(genes)
            best = engine.evolve()
            
            if best:
                return {
                    "best_fitness": best.fitness,
                    "best_genes": [
                        {"opcode": g.opcode, "modifier": g.modifier}
                        for g in best.genes
                    ],
                    "evolution_history": [
                        {"generation": h["generation"], "best_fitness": h["best_fitness"]}
                        for h in engine.get_evolution_history()
                    ],
                }
            return {"error": "进化失败"}
    
    def _evolve_using_evomorph(self, seed_genes: List[Dict[str, Any]], config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """使用 Evomorph 实现进化种群"""
        default_config = {
            "population_size": 32,
            "max_generations": 50,
            "mut_rate": 0.02,
            "env_targets": ["linux-6.x"],
        }
        
        if config:
            default_config.update(config)
        
        self.runtime.bind_env("SEED_GENES", seed_genes)
        self.runtime.bind_env("POPULATION_SIZE", default_config["population_size"])
        self.runtime.bind_env("MAX_GENERATIONS", default_config["max_generations"])
        self.runtime.bind_env("MUT_RATE", default_config["mut_rate"])
        self.runtime.bind_env("ENV_TARGETS", default_config["env_targets"])
        
        result = self.execute_locus("evoc.evolution.full_evolution", max_cycles=100000)
        return result
    
    def analyze_source(self, source: str) -> Dict[str, Any]:
        """
        静态分析源代码。
        
        Args:
            source: 源代码字符串
        
        Returns:
            分析结果
        """
        if self.is_evomorph_available("static_analyzer"):
            return self._analyze_using_evomorph(source)
        else:
            from evomorph.analysis.static_analyzer import StaticAnalyzer
            analyzer = StaticAnalyzer()
            return analyzer.analyze(source)
    
    def _analyze_using_evomorph(self, source: str) -> Dict[str, Any]:
        """使用 Evomorph 实现静态分析"""
        self.runtime.bind_env("SOURCE_CODE", source)
        result = self.execute_locus("evoc.static_analyzer.analyze", max_cycles=10000)
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取后端状态。
        
        Returns:
            状态信息
        """
        return {
            "use_evomorph": self._use_evomorph,
            "loaded_modules": self._loaded_loci.copy(),
            "available_modules": [
                name for name, loaded in self._loaded_loci.items() if loaded
            ],
        }
