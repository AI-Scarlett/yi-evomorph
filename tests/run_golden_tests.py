#!/usr/bin/env python3
"""
Evomorph 黄金样例测试运行器

验证 golden .evo 样例能稳定编译，并与预期 EVB hash 对比。
这是自举验证的核心测试工具。
"""

import sys
import os
import hashlib
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

GOLDEN_DIR = os.path.join(PROJECT_ROOT, "tests", "evo", "golden")


def get_primitive_compiler():
    """获取 Evomorph primitive 编译器"""
    from evomorph.bootstrap.runtime.enhanced_runtime import EnhancedEvoRuntime
    return EnhancedEvoRuntime()


def run_golden_tests(compiler=None, verbose=True):
    """运行所有黄金样例测试"""
    if compiler is None:
        compiler = get_primitive_compiler()

    if not os.path.exists(GOLDEN_DIR):
        print(f"✗ Golden test directory not found: {GOLDEN_DIR}")
        return 1

    passed = 0
    failed = 0
    skipped = 0
    results = []

    for fname in sorted(os.listdir(GOLDEN_DIR)):
        if not fname.endswith(".evo"):
            continue

        path = os.path.join(GOLDEN_DIR, fname)
        hash_path = path.replace(".evo", ".sha256")
        name = fname.replace(".evo", "")

        with open(path, "r", encoding="utf-8") as f:
            source = f.read()

        # 编译
        try:
            result = compiler.full_compile(source)
            loci = result.get("loci", [])
            meta_loci = result.get("meta_loci", [])
            success = len(loci) > 0 or len(meta_loci) > 0

            if not success:
                failed += 1
                results.append((name, "FAIL", "编译成功但无基因座"))
                continue

        except Exception as e:
            failed += 1
            results.append((name, "ERROR", str(e)[:60]))
            continue

        # 验证 EVB hash
        if os.path.exists(hash_path):
            try:
                tokens = compiler.compile_with_evo_lexer(source)
                ast = compiler.compile_with_evo_parser(tokens)
                evb_bytes = compiler._prim_codegen_generate_evb(ast)
                actual_hash = hashlib.sha256(evb_bytes).hexdigest()

                with open(hash_path, "r") as f:
                    expected_line = f.read().strip().split()[0]

                if actual_hash == expected_line:
                    passed += 1
                    results.append((name, "PASS", f"hash匹配, {len(loci)}基因座"))
                else:
                    failed += 1
                    results.append((name, "HASH", f"hash不匹配"))
            except Exception as e:
                failed += 1
                results.append((name, "ERROR", str(e)[:60]))
        else:
            passed += 1
            results.append((name, "PASS", f"无hash文件, {len(loci)}基因座"))

    # 输出结果
    if verbose:
        print(f"\n黄金样例测试结果 ({len(results)} 个):")
        print("-" * 60)
        for name, status, detail in results:
            icon = "✓" if status == "PASS" else "✗"
            print(f"  {icon} {name}: [{status}] {detail}")
        print("-" * 60)
        print(f"总计: {passed} 通过, {failed} 失败, {skipped} 跳过")

    return 0 if failed == 0 else 1


def main():
    """CLI 入口"""
    import argparse
    parser = argparse.ArgumentParser(description="Evomorph 黄金样例测试")
    parser.add_argument("-v", "--verbose", action="store_true", default=True)
    parser.add_argument("--no-verbose", dest="verbose", action="store_false")
    args = parser.parse_args()

    sys.exit(run_golden_tests(verbose=args.verbose))


if __name__ == "__main__":
    main()
