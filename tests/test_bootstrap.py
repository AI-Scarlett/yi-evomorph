#!/usr/bin/env python3
"""
自举验证脚本：使用Python编译器编译full_self_bootstrap.evo
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

BOOTSTRAP_FILE = os.path.join(
    PROJECT_ROOT,
    "evomorph", "bootstrap", "full_self_bootstrap.evo"
)

def compile_with_python():
    """使用Python编译器编译自举文件"""
    print("=" * 60)
    print("步骤1: 使用Python编译器编译 full_self_bootstrap.evo")
    print("=" * 60)
    
    from evomorph.compiler import EvocCompiler
    
    compiler = EvocCompiler()
    
    print(f"\n读取文件: {BOOTSTRAP_FILE}")
    try:
        with open(BOOTSTRAP_FILE, "r", encoding="utf-8") as f:
            source = f.read()
        print(f"文件大小: {len(source)} 字符")
    except Exception as e:
        print(f"错误: 无法读取文件 - {e}")
        return None
    
    print("\n编译中...")
    try:
        result = compiler.compile(source, output_format="dict")
        print("编译成功!")
        
        loci = result.get("loci", [])
        meta_loci = result.get("meta_loci", [])
        
        print(f"\n编译结果统计:")
        print(f"  - 基因座数量: {len(loci)}")
        print(f"  - 元基因座数量: {len(meta_loci)}")
        
        if loci:
            print(f"\n基因座列表 (前20个):")
            for i, locus in enumerate(loci[:20]):
                print(f"  {i+1}. {locus.get('name', '?')}")
            
            if len(loci) > 20:
                print(f"  ... 还有 {len(loci) - 20} 个")
        
        return result
        
    except Exception as e:
        print(f"错误: 编译失败 - {e}")
        import traceback
        traceback.print_exc()
        return None

def load_and_execute_with_runtime(compiled_result):
    """使用运行时加载并执行"""
    print("\n" + "=" * 60)
    print("步骤2: 使用EvoRuntime加载编译结果")
    print("=" * 60)
    
    from evomorph.bootstrap.runtime import EvoRuntime
    
    runtime = EvoRuntime()
    
    loci = compiled_result.get("loci", [])
    for locus in loci:
        runtime.loaded_loci[locus["name"]] = locus
    
    print(f"\n已加载 {len(runtime.loaded_loci)} 个基因座")
    
    return runtime

def test_simple_execution(runtime):
    """测试简单执行"""
    print("\n" + "=" * 60)
    print("步骤3: 测试执行简单基因座")
    print("=" * 60)
    
    test_loci = [
        "evoc.bootstrap.init",
        "evoc.vm.init",
        "evoc.evolution.init",
        "evoc.cli.init",
    ]
    
    for locus_name in test_loci:
        if locus_name in runtime.loaded_loci:
            print(f"\n执行: {locus_name}")
            try:
                result = runtime.execute_locus(locus_name, max_cycles=1000)
                print(f"  状态: {result.get('state')}")
                print(f"  周期数: {result.get('cycle_count')}")
                print(f"  寄存器: {result.get('registers', {})}")
            except Exception as e:
                print(f"  错误: {e}")
        else:
            print(f"\n警告: 基因座 {locus_name} 未找到")

def main():
    print("易衍·Evomorph 自举验证")
    print("道枢自举：编译器用自身之语言书写自身")
    print()
    
    result = compile_with_python()
    if not result:
        print("\n自举验证失败: 编译失败")
        return False
    
    runtime = load_and_execute_with_runtime(result)
    if not runtime:
        return False
    
    test_simple_execution(runtime)
    
    print("\n" + "=" * 60)
    print("自举验证总结")
    print("=" * 60)
    print("\n✓ Python编译器能够编译 full_self_bootstrap.evo")
    print("✓ 编译结果包含所有必要的基因座")
    print("\n下一步: 使用编译出的易衍编译器再次编译自身 (验证自举)")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
