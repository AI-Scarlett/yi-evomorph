#!/usr/bin/env python3
"""
易衍自举编译器 CLI
使用易衍语言编写的编译器进行编译
"""

import sys
import os
import argparse
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evomorph.bootstrap.evo_bootstrap_executor import EvoBootstrapExecutor, run_evo_compiler
from evomorph.bootstrap.complete_bootstrap_runtime import CompleteBootstrapRuntime


def print_header():
    print("╔════════════════════════════════════════════════════════════╗")
    print("║           易衍·Evomorph 自举编译器 v3.0                      ║")
    print("║       用易衍语言编写的编译器 - 真正的自举能力                 ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()


def compile_with_evo_compiler(input_file: str, output_file: str = None, verbose: bool = False) -> dict:
    """使用易衍编译器编译文件"""
    
    if verbose:
        print_header()
        print(f"[编译] 输入文件: {input_file}")
        if output_file:
            print(f"[编译] 输出文件: {output_file}")
        print()
    
    if not os.path.exists(input_file):
        print(f"[错误] 文件不存在: {input_file}")
        return {"success": False, "error": f"File not found: {input_file}"}
    
    with open(input_file, 'r', encoding='utf-8') as f:
        source = f.read()
    
    if verbose:
        print(f"[词法分析] 正在分析源代码...")
    
    runtime = CompleteBootstrapRuntime()
    
    if verbose:
        print(f"[词法分析] 源代码长度: {len(source)} 字符")
    
    result = runtime.full_compile(source)
    
    if verbose:
        print(f"[编译完成] 版本: {result.get('version')}")
        print(f"[编译完成] 基因座数量: {len(result.get('loci', []))}")
        print(f"[编译完成] 象辞数量: {len(result.get('xiangci', []))}")
        
        for locus in result.get('loci', []):
            print(f"\n  基因座: {locus.get('name')}")
            print(f"    - 变异率: {locus.get('mut_rate')}")
            print(f"    - 交叉池: {locus.get('cross_pool')}")
            print(f"    - 目标平台: {locus.get('env_targets')}")
            print(f"    - 指令数量: {len(locus.get('instructions', []))}")
            
            for instr in locus.get('instructions', [])[:5]:
                print(f"      * {instr.get('symbol')} {instr.get('mnemonic')} (opcode={instr.get('opcode')})")
            
            if len(locus.get('instructions', [])) > 5:
                print(f"      ... 还有 {len(locus.get('instructions', [])) - 5} 条指令")
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        if verbose:
            print(f"\n[输出] 结果已保存到: {output_file}")
    
    return {"success": True, "result": result}


def compare_with_python_compiler(input_file: str, verbose: bool = False) -> dict:
    """对比易衍编译器与Python编译器"""
    
    if verbose:
        print_header()
        print(f"[对比] 输入文件: {input_file}")
        print()
    
    if not os.path.exists(input_file):
        print(f"[错误] 文件不存在: {input_file}")
        return {"success": False, "error": f"File not found: {input_file}"}
    
    with open(input_file, 'r', encoding='utf-8') as f:
        source = f.read()
    
    runtime = CompleteBootstrapRuntime()
    
    if verbose:
        print(f"[对比] 正在编译并对比...")
    
    comparison = runtime.compare_compilers(source)
    
    if verbose:
        print(f"\n[对比结果]")
        print(f"  - 易衍编译器基因座数: {comparison.get('evo_loci_count')}")
        print(f"  - Python编译器基因座数: {comparison.get('python_loci_count')}")
        print(f"  - 基因座匹配: {'✓' if comparison.get('loci_match') else '✗'}")
        print(f"  - 指令匹配: {'✓' if comparison.get('all_instruction_match') else '✗'}")
        
        print(f"\n  性能对比:")
        print(f"    - 易衍编译时间: {comparison['timing_comparison']['evo_total']:.4f}s")
        print(f"    - Python编译时间: {comparison['timing_comparison']['python_total']:.4f}s")
        print(f"    - 时间比率: {comparison['timing_comparison']['ratio']:.2f}x")
        
        for comp in comparison.get('instruction_comparison', []):
            print(f"\n  基因座 '{comp['locus_name']}':")
            print(f"    - 易衍指令数: {comp['evo_instr_count']}")
            print(f"    - Python指令数: {comp['python_instr_count']}")
            print(f"    - 匹配: {'✓' if comp['match'] else '✗'}")
    
    return {"success": True, "comparison": comparison}


def run_self_test(verbose: bool = False) -> dict:
    """运行自举测试"""
    
    if verbose:
        print_header()
        print(f"[自举测试] 正在运行...")
        print()
    
    runtime = CompleteBootstrapRuntime()
    
    result = runtime.run_self_compile_test()
    
    if verbose:
        print(f"[自举测试结果]")
        print(f"  - Token数量: {result.get('tokens')}")
        print(f"  - AST有效: {'✓' if result.get('ast_valid') else '✗'}")
        print(f"  - 代码生成有效: {'✓' if result.get('codegen_valid') else '✗'}")
    
    gaps = runtime.analyze_feature_gaps()
    
    if verbose:
        print(f"\n[功能差距分析]")
        print(f"  - 总功能数: {gaps['summary']['total_features']}")
        print(f"  - 已完成: {gaps['summary']['closed_gaps']}")
        print(f"  - 待完成: {gaps['summary']['open_gaps']}")
        print(f"  - 完成度: {gaps['summary']['completion_percentage']:.1f}%")
        
        print(f"\n  按优先级分布:")
        for prio in [1, 2, 3, 4, 5]:
            open_count = len([g for g in gaps['open'] if g['priority'] == prio])
            closed_count = len([g for g in gaps['closed'] if g['priority'] == prio])
            total = open_count + closed_count
            pct = (closed_count / total * 100) if total > 0 else 0
            print(f"    优先级 {prio}: {closed_count}/{total} ({pct:.0f}%)")
    
    return {"success": True, "self_test": result, "gaps": gaps}


def run_continuous_bootstrap(input_file: str = None, max_gens: int = 10, 
                              threshold: float = 90.0, verbose: bool = False) -> dict:
    """运行持续自举循环"""
    
    if verbose:
        print_header()
        print(f"[持续自举] 正在启动...")
        print(f"  - 最大代数: {max_gens}")
        print(f"  - 适应度阈值: {threshold}%")
        print()
    
    runtime = CompleteBootstrapRuntime()
    
    if input_file and os.path.exists(input_file):
        with open(input_file, 'r', encoding='utf-8') as f:
            source = f.read()
    else:
        source = runtime.get_evo_compiler_source()
        if verbose:
            print(f"[持续自举] 使用内置编译器源代码")
    
    if verbose:
        print(f"[持续自举] 源代码长度: {len(source)} 字符")
        print()
    
    result = runtime.continuous_bootstrap_loop(source, max_gens, threshold)
    
    if verbose:
        print(f"\n[持续自举结果]")
        print(f"  - 最佳适应度: {result['best_fitness']:.2f}%")
        print(f"  - 完成代数: {result['generations_completed']}")
        gaps = result.get('feature_gaps', {})
        completion = gaps.get('summary', {}).get('completion_percentage', 0)
        print(f"  - 功能完成度: {completion:.1f}%")
        
        print(f"\n  每代历史:")
        for entry in result['loop_history']:
            print(f"    - 代 {entry['generation']+1}: 适应度={entry['fitness']:.2f}%, 改进={entry['improvements']}")
    
    return {"success": True, "result": result}


def list_evo_compiler_files():
    """列出所有易衍编译器文件"""
    
    evo_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'evoc')
    
    print_header()
    print(f"[易衍编译器文件] 目录: {evo_dir}")
    print()
    
    if os.path.exists(evo_dir):
        files = [f for f in os.listdir(evo_dir) if f.endswith('.evo')]
        for f in sorted(files):
            filepath = os.path.join(evo_dir, f)
            size = os.path.getsize(filepath)
            print(f"  {f} ({size} 字节)")
        
        print(f"\n  总计: {len(files)} 个文件")
    else:
        print(f"  目录不存在: {evo_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='易衍·Evomorph 自举编译器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  evoc compile input.evo -o output.json
  evoc compile input.evo --verbose
  evoc compare input.evo
  evoc self-test
  evoc bootstrap --max-gens 20 --threshold 95
  evoc list
        '''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    compile_parser = subparsers.add_parser('compile', help='编译 .evo 文件')
    compile_parser.add_argument('input', help='输入 .evo 文件')
    compile_parser.add_argument('-o', '--output', help='输出文件 (JSON格式)')
    compile_parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    
    compare_parser = subparsers.add_parser('compare', help='对比易衍编译器与Python编译器')
    compare_parser.add_argument('input', help='输入 .evo 文件')
    compare_parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    
    test_parser = subparsers.add_parser('self-test', help='运行自举测试')
    test_parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    
    bootstrap_parser = subparsers.add_parser('bootstrap', help='运行持续自举循环')
    bootstrap_parser.add_argument('-i', '--input', help='输入 .evo 文件 (可选，使用内置编译器)')
    bootstrap_parser.add_argument('-g', '--max-gens', type=int, default=10, help='最大代数 (默认: 10)')
    bootstrap_parser.add_argument('-t', '--threshold', type=float, default=90.0, help='适应度阈值 (默认: 90)')
    bootstrap_parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    
    list_parser = subparsers.add_parser('list', help='列出所有易衍编译器文件')
    
    args = parser.parse_args()
    
    if args.command == 'compile':
        result = compile_with_evo_compiler(args.input, args.output, args.verbose)
        return 0 if result.get('success') else 1
    
    elif args.command == 'compare':
        result = compare_with_python_compiler(args.input, args.verbose)
        return 0 if result.get('success') else 1
    
    elif args.command == 'self-test':
        result = run_self_test(args.verbose)
        return 0 if result.get('success') else 1
    
    elif args.command == 'bootstrap':
        result = run_continuous_bootstrap(args.input, args.max_gens, args.threshold, args.verbose)
        return 0 if result.get('success') else 1
    
    elif args.command == 'list':
        list_evo_compiler_files()
        return 0
    
    else:
        print_header()
        print("使用方法: evoc <command> [options]")
        print()
        print("可用命令:")
        print("  compile    编译 .evo 文件")
        print("  compare    对比易衍编译器与Python编译器")
        print("  self-test  运行自举测试")
        print("  bootstrap  运行持续自举循环")
        print("  list       列出所有易衍编译器文件")
        print()
        print("使用 'evoc <command> --help' 查看命令详细帮助")
        return 1


if __name__ == "__main__":
    sys.exit(main())
