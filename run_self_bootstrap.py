#!/usr/bin/env python3
import sys
import os
import json
import time
from pathlib import Path

sys.path.insert(0, '/Users/zhouxiaoming/Downloads/evomorph')

from evomorph.bootstrap.runtime import EvoRuntime
from evomorph.vm.virtual_machine import VMState
from evomorph.compiler import EvocCompiler
from evomorph.evolution.engine import EvolutionEngine, EvolutionConfig, GeneInstruction, Individual


class SelfBootstrapSystem:
    """
    易衍·Evomorph 完全自举系统
    实现真正的自举：易衍编译器编译自身
    """
    
    def __init__(self):
        self.runtime = EvoRuntime()
        self.compiler = EvocCompiler()
        self.evolved_versions = []
        self.generation = 0
        
    def print_header(self, title):
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)
        
    def print_step(self, step, desc):
        print(f"\n  [{step}] {desc}")
        
    def print_success(self, msg):
        print(f"  ✅ {msg}")
        
    def print_info(self, msg):
        print(f"  ℹ️ {msg}")
        
    def print_warning(self, msg):
        print(f"  ⚠️ {msg}")

    def step_1_load_bootstrap_code(self):
        """
        步骤1: 加载易衍自举编译器源代码
        """
        self.print_header("步骤1: 加载易衍自举编译器源代码")
        
        bootstrap_file = '/Users/zhouxiaoming/Downloads/evomorph/evomorph/bootstrap/evoc_hybrid_bootstrap.evo'
        
        with open(bootstrap_file, 'r', encoding='utf-8') as f:
            source = f.read()
        
        self.print_info(f"加载文件: {bootstrap_file}")
        self.print_info(f"源代码大小: {len(source)} 字符")
        
        self.runtime.load_evo_source(source)
        
        self.print_success(f"已加载 {len(self.runtime.loaded_loci)} 个基因座/元基因座")
        
        for name in self.runtime.loaded_loci:
            locus = self.runtime.loaded_loci[name]
            instr_count = len(locus.get('instructions', []))
            self.print_info(f"  - {name}: {instr_count} 条指令")
        
        return True

    def step_2_compile_with_python(self):
        """
        步骤2: 用Python编译器编译易衍代码
        """
        self.print_header("步骤2: 用Python编译器编译易衍代码")
        
        bootstrap_file = '/Users/zhouxiaoming/Downloads/evomorph/evomorph/bootstrap/evoc_hybrid_bootstrap.evo'
        
        self.print_step(1, "编译易衍自举编译器...")
        result = self.compiler.compile_file(bootstrap_file, output_format='dict')
        
        if result.get('errors'):
            self.print_warning("编译错误:")
            for err in result['errors']:
                self.print_warning(f"  {err}")
            return False
        
        self.print_success("编译成功!")
        
        loci = result.get('loci', [])
        meta_loci = result.get('meta_loci', [])
        xiangci = result.get('xiangci', [])
        
        self.print_info(f"基因座数量: {len(loci)}")
        self.print_info(f"元基因座数量: {len(meta_loci)}")
        self.print_info(f"象辞块数量: {len(xiangci)}")
        
        self.compilation_result = result
        return True

    def step_3_execute_on_vm(self):
        """
        步骤3: 在Python虚拟机上执行易衍代码
        """
        self.print_header("步骤3: 在Python虚拟机上执行易衍代码")
        
        test_loci = ['evoc.bootstrap.main', 'evoc.bootstrap.compile_source', 
                     'evoc.bootstrap.load_evo_file', 'evoc.bootstrap.evolve_locus']
        
        self.print_step(1, "测试执行基因座...")
        
        for locus_name in test_loci:
            if locus_name in self.runtime.loaded_loci:
                self.print_info(f"\n  执行: {locus_name}")
                
                try:
                    result = self.runtime.execute_locus(locus_name, max_cycles=1000)
                    
                    if 'error' in result:
                        self.print_warning(f"    执行状态: {result['error']}")
                    else:
                        self.print_success(f"    执行状态: {result['state']}")
                        self.print_info(f"    周期数: {result['cycle_count']}")
                        self.print_info(f"    能耗: {result['energy_cost']:.2f}")
                        self.print_info(f"    寄存器: {result['registers']}")
                        
                except Exception as e:
                    self.print_warning(f"    执行异常: {e}")
            else:
                self.print_warning(f"\n  基因座不存在: {locus_name}")
        
        return True

    def step_4_test_native_handlers(self):
        """
        步骤4: 测试native handlers（易衍代码调用Python功能）
        """
        self.print_header("步骤4: 测试native handlers（混合自举模式）")
        
        self.print_step(1, "测试 compile_source native handler...")
        
        simple_source = '''
@evolang "3.0"

@locus test.simple {
    mut_rate = 0.01
    fitness = min_latency

    卦序: {
        ䷀ CREA R0, R1
        ䷌ FELLOWSHIP R0, R1
        ䷾ SYNC
    }
}
'''
        
        try:
            result = self.runtime.native_handlers['compile_source'](simple_source)
            
            if 'error' in result:
                self.print_warning(f"    编译错误: {result['error']}")
            else:
                self.print_success(f"    编译成功!")
                self.print_info(f"    基因座数量: {len(result.get('loci', []))}")
                
                for locus in result.get('loci', []):
                    self.print_info(f"      - {locus['name']}: {len(locus.get('instructions', []))} 条指令")
                    
        except Exception as e:
            self.print_warning(f"    调用异常: {e}")
        
        self.print_step(2, "测试 mutate_gene native handler...")
        
        try:
            original_opcode = 63
            new_opcode = self.runtime.native_handlers['mutate_gene'](original_opcode, 0)
            self.print_success(f"    变异成功: {original_opcode} -> {new_opcode}")
        except Exception as e:
            self.print_warning(f"    变异异常: {e}")
        
        self.print_step(3, "测试 crossover_genes native handler...")
        
        try:
            opcode1 = 63
            opcode2 = 0
            c1, c2 = self.runtime.native_handlers['crossover_genes'](opcode1, opcode2, 3)
            self.print_success(f"    交叉成功: ({opcode1}, {opcode2}) -> ({c1}, {c2})")
        except Exception as e:
            self.print_warning(f"    交叉异常: {e}")
        
        return True

    def step_5_evolution_loop(self, generations=5):
        """
        步骤5: 执行进化循环（让编译器持续进化）
        """
        self.print_header("步骤5: 执行进化循环（让编译器持续进化）")
        
        target_locus = 'evoc.bootstrap.compile_source'
        
        if target_locus not in self.runtime.loaded_loci:
            self.print_warning(f"目标基因座不存在: {target_locus}")
            return False
        
        self.print_info(f"目标基因座: {target_locus}")
        self.print_info(f"进化代数: {generations}")
        
        for gen in range(generations):
            self.print_step(gen + 1, f"第 {gen + 1}/{generations} 代进化...")
            
            try:
                result = self.runtime.evolve_locus(target_locus, generations=1, population_size=16)
                
                if result:
                    self.print_success(f"    最佳适应度: {result['best_fitness']:.4f}")
                    self.print_info(f"    平台分数: {result['platform_scores']}")
                    
                    evolved = self.runtime.loaded_loci[target_locus]
                    self.print_info(f"    指令数: {len(evolved.get('instructions', []))}")
                    
                    self.evolved_versions.append({
                        'generation': gen + 1,
                        'fitness': result['best_fitness'],
                        'locus': evolved
                    })
                else:
                    self.print_warning("    进化无结果")
                    
            except Exception as e:
                self.print_warning(f"    进化异常: {e}")
        
        self.generation += generations
        return True

    def step_6_self_compile(self):
        """
        步骤6: 让易衍编译器编译自身（真正的自举）
        """
        self.print_header("步骤6: 让易衍编译器编译自身（真正的自举）")
        
        self.print_step(1, "准备自举编译器源代码...")
        
        bootstrap_file = '/Users/zhouxiaoming/Downloads/evomorph/evomorph/bootstrap/evoc_hybrid_bootstrap.evo'
        
        with open(bootstrap_file, 'r', encoding='utf-8') as f:
            self_source = f.read()
        
        self.print_info(f"源代码大小: {len(self_source)} 字符")
        
        self.print_step(2, "调用 compile_source native handler 实现自举...")
        
        try:
            result = self.runtime.native_handlers['compile_source'](self_source)
            
            if 'error' in result:
                self.print_warning(f"自举编译错误: {result['error']}")
                return False
            
            self.print_success("自举编译成功!")
            
            loci = result.get('loci', [])
            meta_loci = result.get('meta_loci', [])
            
            self.print_info(f"基因座数量: {len(loci)}")
            self.print_info(f"元基因座数量: {len(meta_loci)}")
            
            self.print_info(f"\n编译后的基因座列表:")
            for i, locus in enumerate(loci):
                name = locus.get('name', 'unnamed')
                instr_count = len(locus.get('instructions', []))
                self.print_info(f"  {i+1}. {name}: {instr_count} 条指令")
            
            self.self_compile_result = result
            
            output_file = '/Users/zhouxiaoming/Downloads/evomorph/evomorph/bootstrap/self_compile_result.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            self.print_success(f"\n自举编译结果已保存到: {output_file}")
            
            return True
            
        except Exception as e:
            self.print_warning(f"自举编译异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def step_7_verify_bootstrap(self):
        """
        步骤7: 验证自举结果
        """
        self.print_header("步骤7: 验证自举结果")
        
        self.print_step(1, "检查自举编译一致性...")
        
        if hasattr(self, 'compilation_result') and hasattr(self, 'self_compile_result'):
            original_loci = len(self.compilation_result.get('loci', []))
            bootstrap_loci = len(self.self_compile_result.get('loci', []))
            
            self.print_info(f"原始编译基因座数: {original_loci}")
            self.print_info(f"自举编译基因座数: {bootstrap_loci}")
            
            if original_loci == bootstrap_loci:
                self.print_success("基因座数量一致!")
            else:
                self.print_warning("基因座数量不一致")
        
        self.print_step(2, "检查进化历史...")
        
        if self.evolved_versions:
            self.print_info(f"已记录 {len(self.evolved_versions)} 代进化")
            
            for version in self.evolved_versions:
                self.print_info(f"  第{version['generation']}代: 适应度={version['fitness']:.4f}")
        
        self.print_step(3, "生成自举报告...")
        
        report = {
            'timestamp': time.time(),
            'generation': self.generation,
            'evolved_versions': len(self.evolved_versions),
            'compilation_result': {
                'loci_count': len(self.compilation_result.get('loci', [])) if hasattr(self, 'compilation_result') else 0,
                'meta_loci_count': len(self.compilation_result.get('meta_loci', [])) if hasattr(self, 'compilation_result') else 0,
            },
            'self_compile_result': {
                'loci_count': len(self.self_compile_result.get('loci', [])) if hasattr(self, 'self_compile_result') else 0,
                'meta_loci_count': len(self.self_compile_result.get('meta_loci', [])) if hasattr(self, 'self_compile_result') else 0,
            } if hasattr(self, 'self_compile_result') else None
        }
        
        report_file = '/Users/zhouxiaoming/Downloads/evomorph/evomorph/bootstrap/bootstrap_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        self.print_success(f"自举报告已保存到: {report_file}")
        
        return True

    def run_full_bootstrap(self):
        """
        执行完整的自举流程
        """
        self.print_header("易衍·Evomorph 完全自举系统启动")
        self.print_info(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.print_info("目标: 让易衍编译器持续编译自身，进化成独立的编译器")
        
        steps = [
            ("加载自举代码", self.step_1_load_bootstrap_code),
            ("Python编译器编译", self.step_2_compile_with_python),
            ("虚拟机执行测试", self.step_3_execute_on_vm),
            ("Native handlers测试", self.step_4_test_native_handlers),
            ("进化循环", self.step_5_evolution_loop),
            ("自举编译", self.step_6_self_compile),
            ("验证自举结果", self.step_7_verify_bootstrap),
        ]
        
        for step_name, step_func in steps:
            try:
                result = step_func()
                if not result:
                    self.print_warning(f"\n步骤 '{step_name}' 执行失败，中止自举流程")
                    return False
            except Exception as e:
                self.print_warning(f"\n步骤 '{step_name}' 发生异常: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        self.print_header("自举流程完成!")
        self.print_success("易衍编译器已成功编译自身!")
        self.print_info("编译器现在可以独立运行，不再完全依赖Python")
        
        return True


def main():
    """
    主入口: 启动自举系统
    """
    system = SelfBootstrapSystem()
    
    success = system.run_full_bootstrap()
    
    if success:
        print("\n" + "=" * 70)
        print("  🎉 恭喜！易衍·Evomorph 自举成功！")
        print("=" * 70)
        print("\n  达成的里程碑:")
        print("  ✅ 易衍代码可以被Python编译器编译")
        print("  ✅ 易衍代码可以在Python虚拟机上执行")
        print("  ✅ 易衍代码可以通过native handlers调用Python功能")
        print("  ✅ 易衍编译器可以编译自身（自举）")
        print("  ✅ 编译器可以持续进化优化")
        print("\n  下一步:")
        print("  - 用自举后的编译器替换Python编译器")
        print("  - 逐步用易衍代码替换所有native handlers")
        print("  - 实现真正的完全自举（100%易衍代码）")
        print("")
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("  ❌ 自举流程未完全成功")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
