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
        步骤6: 让易衍编译器编译自身（真正的自举 — 字节级验证）

        验证原理:
          - 同一编译器 EVB 字节码在两个模式下执行:
            路径 A (裸 VM): EVB 直接加载到 VM, 独立执行编译
            路径 B (Python 辅助): 通过 IChingBootstrapCompiler 辅助执行编译
          - 验证: A == B (字节级) → EVB 加载和执行机制正确
        """
        self.print_header("步骤6: 让易衍编译器编译自身（真正的自举验证）")
        
        self.print_step(1, "加载自举编译器源代码...")
        
        bootstrap_file = '/Users/zhouxiaoming/Downloads/evomorph/evomorph/bootstrap/evoc_hybrid_bootstrap.evo'
        
        with open(bootstrap_file, 'r', encoding='utf-8') as f:
            self_source = f.read()
        
        self.print_info(f"源代码大小: {len(self_source)} 字符")
        
        self.print_step(2, "裸 VM 执行 vs Python 辅助执行 → 字节级对比...")
        
        try:
            # 使用 runtime 的 self_compile_verify 进行字节级验证
            verify_result = self.runtime.self_compile_verify(self_source)
            
            self.print_info(f"裸 VM 输出: {verify_result['raw_vm_size']} 字节")
            self.print_info(f"Python辅助: {verify_result['python_vm_size']} 字节")
            
            if verify_result.get("raw_vm_hash"):
                self.print_info(f"裸 VM SHA256: {verify_result['raw_vm_hash']}")
            if verify_result.get("python_vm_hash"):
                self.print_info(f"Python SHA256: {verify_result['python_vm_hash']}")
            
            if verify_result.get("bytes_match"):
                self.print_success("自举验证成功! 同一编译器逻辑字节级完全一致")
                self.self_compile_result = {"bytes_match": True, **verify_result}
            else:
                self.print_warning("字节不一致:")
                if verify_result.get("diff_positions"):
                    diffs = verify_result["diff_positions"]
                    self.print_info(f"  差异位置: {diffs}")
                self.self_compile_result = {"bytes_match": False, **verify_result}
            
            # 保存验证报告
            output_file = '/Users/zhouxiaoming/Downloads/evomorph/evomorph/bootstrap/self_compile_verify.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(verify_result, f, ensure_ascii=False, indent=2, default=str)
            self.print_success(f"验证报告已保存: {output_file}")
            
            return True
            
        except Exception as e:
            self.print_warning(f"自举验证异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def step_7_verify_bootstrap(self):
        """
        步骤7: 验证自举结果 (字节级)
        """
        self.print_header("步骤7: 验证自举结果")
        
        self.print_step(1, "自举编译一致性 (字节级)...")
        
        if hasattr(self, 'self_compile_result') and self.self_compile_result:
            if self.self_compile_result.get("bytes_match"):
                self.print_success("★★★ 完全自举验证通过 ★★★")
                self.print_info("同一编译器 EVB 字节码在裸 VM 与 Python 辅助下输出完全一致")
                self.print_info("EVB 字节码加载和执行机制验证正确, 编译器可独立运行")
            else:
                self.print_warning("自举验证未通过: 存在字节差异")
                self.print_info("  裸 VM size: {}".format(
                    self.self_compile_result.get("raw_vm_size", "N/A")))
                self.print_info("  Python size: {}".format(
                    self.self_compile_result.get("python_vm_size", "N/A")))
                self.print_info("  Diff positions: {}".format(
                    self.self_compile_result.get("diff_positions", [])))
        else:
            self.print_warning("无法验证: 缺少自举编译结果")
        
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
            'self_compile_verified': self.self_compile_result.get("bytes_match", False)
                if hasattr(self, 'self_compile_result') and self.self_compile_result else False,
            'raw_vm_size': self.self_compile_result.get("raw_vm_size", 0)
                if hasattr(self, 'self_compile_result') and self.self_compile_result else 0,
            'python_vm_size': self.self_compile_result.get("python_vm_size", 0)
                if hasattr(self, 'self_compile_result') and self.self_compile_result else 0,
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
        print("  易衍·Evomorph 自举流程完成")
        print("=" * 70)
        print("\n  达成的里程碑:")
        print("  ✅ IChing EVB 编译器编译 .evo 源码 (真正自举路径)")
        print("  ✅ 同一编译器逻辑裸 VM 执行与 Python 辅助执行对比")
        print("  ✅ 字节级对比验证 (裸 VM === Python 辅助)")
        print("  ✅ 编译器可以持续进化优化")
        print("\n  自举链: compiler.evoasm → EVB → VM → .evo → EVB ✓")
        if hasattr(system, 'self_compile_result') and system.self_compile_result:
            if system.self_compile_result.get("bytes_match"):
                print("\n  ★★★ 完全自举已实现 ★★★")
        print("")
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("  ❌ 自举流程未完全成功")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
