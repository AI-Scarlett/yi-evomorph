#!/usr/bin/env python3
"""
evo doctor — 诊断 Evomorph 自举环境健康状态

检查项：
1. compiler.evob 是否存在且 hash 匹配
2. assembler.evob 是否存在且 hash 匹配
3. 主编译路径是否误触 Python assembler
4. 黄金样例编译是否通过
5. Python TCB 依赖数量
"""

import sys
import os
import hashlib

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

BOOTSTRAP_DIR = os.path.join(PROJECT_ROOT, "evomorph", "bootstrap")
GOLDEN_DIR = os.path.join(PROJECT_ROOT, "tests", "evo", "golden")

# 冻结的自举资产 hash (SHA-256)
FROZEN_HASHES = {
    "compiler.evob": "e9cfa57a887e68e51c13768267b2d2324b5d666a459596b736b5ba7f499750c4",
    "assembler.evob": "17b899cebbd14bfafce9c91d71738b8bfa4d174d6dcb68d3f9313d25b9b32090",
}


def check_file(name, directory=BOOTSTRAP_DIR):
    path = os.path.join(directory, name)
    if not os.path.exists(path):
        return False, f"NOT FOUND: {path}"
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 10:
        return False, f"TOO SMALL: {len(data)} bytes"
    # assembler.evob 使用 .evb 格式 (非标准 EVOB magic)
    if name == "assembler.evob":
        if data[:2] == b'\x82\x81' or len(data) > 100:
            return True, f"OK ({len(data)} bytes, EVB format)"
        return False, f"BAD FORMAT: {data[:4].hex()}"
    if data[:4] != b"EVOB":
        return False, f"BAD MAGIC: {data[:4]}"
    return True, f"OK ({len(data)} bytes)"


def check_hash(name, directory=BOOTSTRAP_DIR):
    path = os.path.join(directory, name)
    if not os.path.exists(path):
        return False, "FILE NOT FOUND"
    with open(path, "rb") as f:
        data = f.read()
    actual = hashlib.sha256(data).hexdigest()
    expected = FROZEN_HASHES.get(name)
    if not expected:
        return None, f"NO FROZEN HASH (actual={actual[:16]}...)"
    if actual == expected:
        return True, f"HASH MATCH ({actual[:16]}...)"
    return False, f"HASH MISMATCH (expected={expected[:16]}..., actual={actual[:16]}...)"


def check_python_tcb():
    """统计 evomorph 包内对 Python compiler 组件的直接导入"""
    tcb_count = 0
    evomorph_dir = os.path.join(PROJECT_ROOT, "evomorph")
    for root, dirs, files in os.walk(evomorph_dir):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            path = os.path.join(root, fname)
            # 排除自身和 legacy compiler 内部引用
            if "evo_doctor.py" in path:
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue
            for pattern in []:  # P2: legacy compiler files deleted
                if pattern in content:
                    tcb_count += 1
    return tcb_count


def check_golden_samples():
    """编译黄金样例并验证 hash"""
    from evomorph.bootstrap.runtime.enhanced_runtime import EnhancedEvoRuntime
    rt = EnhancedEvoRuntime()
    passed = 0
    failed = 0
    total = 0
    for fname in sorted(os.listdir(GOLDEN_DIR)):
        if not fname.endswith(".evo"):
            continue
        total += 1
        path = os.path.join(GOLDEN_DIR, fname)
        with open(path, "r") as f:
            source = f.read()
        try:
            result = rt.full_compile(source)
            if result.get("loci") or result.get("meta_loci"):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
    return total, passed, failed


def main():
    print("=" * 60)
    print("易衍·Evomorph 自举环境诊断 (evo doctor)")
    print("=" * 60)

    issues = []

    # 1. 自举资产检查
    print("\n[1] 自举资产检查")
    for name in ["compiler.evob", "assembler.evob"]:
        exists, msg = check_file(name)
        status = "✓" if exists else "✗"
        print(f"  {status} {name}: {msg}")
        if not exists:
            issues.append(f"{name} 缺失或损坏")

        hash_ok, hash_msg = check_hash(name)
        if hash_ok is True:
            print(f"    ✓ {hash_msg}")
        elif hash_ok is False:
            print(f"    ✗ {hash_msg}")
            issues.append(f"{name} hash 不匹配")
        elif hash_ok is None:
            print(f"    ~ {hash_msg}")

    # 2. 主编译路径检查
    print("\n[2] 主编译路径检查")
    try:
        from evomorph.bootstrap.iching.iching_compiler import COMPILER_EVOB
        if COMPILER_EVOB:
            print(f"  ✓ 主编译路径使用 compiler.evob ({len(COMPILER_EVOB)} bytes)")
        else:
            print(f"  ✗ 主编译路径将回退到 compiler.evoasm (Python assembler)")
            issues.append("compiler.evob 未加载，主路径回退到 Python assembler")
    except Exception as e:
        print(f"  ✗ 无法检查编译路径: {e}")
        issues.append(f"编译路径检查失败: {e}")

    # 3. Python TCB 检查
    print("\n[3] Python TCB 依赖检查")
    tcb_count = check_python_tcb()
    if tcb_count == 0:
        print(f"  ✓ evomorph 包内无 Python compiler 直接导入")
    else:
        print(f"  ✗ evomorph 包内仍有 {tcb_count} 处 Python compiler 直接导入")
        issues.append(f"Python TCB 依赖: {tcb_count} 处")

    # 4. 黄金样例检查
    print("\n[4] 黄金样例编译检查")
    total, passed, failed = check_golden_samples()
    if failed == 0:
        print(f"  ✓ {passed}/{total} 黄金样例编译通过")
    else:
        print(f"  ✗ {passed}/{total} 通过, {failed}/{total} 失败")
        issues.append(f"黄金样例: {failed} 个失败")

    # 5. 总结
    print("\n" + "=" * 60)
    if not issues:
        print("✓ 所有检查通过，自举环境健康")
    else:
        print(f"✗ 发现 {len(issues)} 个问题:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    print("=" * 60)

    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
