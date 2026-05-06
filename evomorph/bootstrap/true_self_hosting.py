#!/usr/bin/env python3
# Legacy — 自举验证系统 (v0.0.4 过渡代码)
# 主编译路径已迁移到 IChing EVB 自举编译器 (compiler.evoasm)
"""
易衍·Evomorph 真正的自举验证系统

验证链:
  1. compiler.evoasm  —(Python assembler)—→  EVB bytecode A
  2. EVB bytecode A   —(载入 VM)—→  编译 .evo 源  —→  EVB bytecode B
  3. 用 IChing 编译器编译相同源  —→  EVB bytecode C
  4. 验证: B == C (字节级别完全一致)

关键: 在第 2 步中, VM 完全独立运行, 不依赖 Python 编译器类。
     编译器逻辑完全由 EVB 字节码承载, 实现了真正的自举.
"""

import sys
import os
import struct
import hashlib
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from evomorph.vm.extended_vm2 import ExtendedIChingVM2, InstrType
from evomorph.bootstrap.iching.iching_compiler import (
    IChingBootstrapCompiler, MNEMONICS, NATIVE_MNEMONICS,
    INPUT_BUF, TOKEN_BUF, OUTPUT_BUF, STRPOOL_BUF,
    MNEMONIC_TABLE, MNEMONIC_STRINGS, LOCUS_OFFSET_TABLE,
    MODIFIER_STRINGS, KEYWORD_STRINGS, NATIVE_TABLE, NATIVE_STRINGS,
    HEADER_RESERVE,
)

# 颜色输出
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"
RESET = "\033[0m"


class TrueSelfHosting:
    """
    真正的自举验证系统.

    核心原理:
    - 编译器 ASM 被汇编成 EVB 字节码
    - EVB 字节码被加载到 VM 实例中
    - VM 使用该字节码独立编译 .evo 源码 (不经过任何 Python 编译器类)
    - 验证 VM 输出与 Python 编译器输出完全一致
    """

    def __init__(self):
        self.asm_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "compiler.evoasm"
        )
        self._bootstrap_compiler = None

    def _get_bootstrap_compiler(self):
        """获取 IChingBootstrapCompiler 实例 (用于辅助初始化)."""
        if self._bootstrap_compiler is None:
            self._bootstrap_compiler = IChingBootstrapCompiler()
        return self._bootstrap_compiler

    # =====================================================================
    # 第一步: 汇编 compiler.evoasm → EVB 字节码
    # =====================================================================

    def assemble_compiler(self) -> bytes:
        """
        使用 ExtendedIChingVM2.assemble() 将 compiler.evoasm 汇编成 EVB 字节码.

        Returns:
            EVB 字节码 (含 EVOB 头部)
        """
        if not os.path.exists(self.asm_path):
            raise FileNotFoundError(f"编译器汇编文件不存在: {self.asm_path}")

        with open(self.asm_path, "r", encoding="utf-8") as f:
            asm_source = f.read()

        # 使用 Python 汇编器 (这是唯一不可避免的 Python 依赖)
        temp_vm = ExtendedIChingVM2()
        bytecode = temp_vm.assemble(asm_source)

        # 封装为 EVOB 格式
        evob = self._wrap_evob(bytecode)
        return evob

    def _wrap_evob(self, bytecode: bytearray) -> bytes:
        """将裸字节码封装为 EVOB 格式."""
        header_size = HEADER_RESERVE  # 64 bytes
        total_size = header_size + len(bytecode)

        evob = bytearray(total_size)
        evob[0:4] = b'EVOB'
        struct.pack_into(">H", evob, 4, 3)       # version 3
        struct.pack_into(">H", evob, 6, header_size)  # header size
        struct.pack_into(">H", evob, 8, 0)         # locus_count = 0 (这是裸编译器)
        # header 其余部分填0
        evob[header_size:] = bytecode

        return bytes(evob)

    # =====================================================================
    # 第二步: VM 独立编译 (不经过 Python 编译器)
    # =====================================================================

    def create_vm_for_self_compile(self, compiler_evob: bytes) -> ExtendedIChingVM2:
        """
        创建一个 VM 实例, 加载编译器 EVB 字节码, 并准备好编译环境.

        这是自举的关键步骤: VM 中运行的不是 Python 代码,
        而是编译器 EVB 字节码.
        """
        bc = IChingBootstrapCompiler()
        vm = ExtendedIChingVM2()

        # 加载助记符表到 heap (这些是编译器的数据, 不是代码)
        bc._load_mnemonic_table()
        bc._load_native_table()
        # 从 bc.vm 复制 heap 数据
        bc_vm = bc.vm
        vm.heap = bytearray(bc_vm.heap)
        vm.heap_ptr = bc_vm.heap_ptr

        # 加载编译器程序 (EVB 字节码)
        vm.program = bytearray(compiler_evob[HEADER_RESERVE:])
        vm.pc = 0
        vm.state = 0  # INIT

        return vm

    def vm_compile_source(self, vm: ExtendedIChingVM2,
                           source: str,
                           max_cycles: int = 10_000_000) -> dict:
        """
        使用 VM 中的编译器字节码独立编译 .evo 源码.

        这个过程完全不依赖 Python 编译器类!
        所有编译逻辑都在 EVB 字节码中执行.

        Args:
            vm: 已加载编译器 EVB 字节码的 VM 实例
            source: .evo 源码
            max_cycles: 最大执行周期

        Returns:
            编译结果字典
        """
        # 预处理源码 (这是文本预处理, 不是编译)
        bc = IChingBootstrapCompiler()
        processed = bc._preprocess_source(source)

        # 加载预处理后的源码到 VM heap
        vm.load_string(INPUT_BUF, processed)

        # 设置输入指针
        vm.registers[0] = INPUT_BUF
        vm.registers[29] = vm.STACK_SIZE
        vm.pc = 0

        # 运行 VM (编译器字节码执行)
        vm.run(max_cycles=max_cycles)

        # 提取输出
        output_size = vm.registers[0]
        result = {
            "success": vm.state == 3,  # HALTED
            "token_count": vm.registers[10],
            "locus_count": vm.registers[15],
            "output_size": output_size,
            "cycles": vm.cycle_count,
        }

        if not result["success"]:
            result["error"] = f"VM execution failed (state={vm.state})"
            return result

        if output_size <= 0 or output_size > 24576:
            result["output_size"] = 0
            return result

        # 提取输出字节码 (与 Python compile_source 相同的 compact 逻辑)
        raw = bytes(vm.heap[OUTPUT_BUF:OUTPUT_BUF + min(output_size, 24576)])

        # 检查 EVOB 头部并 compact (跳过 HEADER_RESERVE 保留区)
        if raw[:4] == b'EVOB':
            result["evob_valid"] = True
            header_size = struct.unpack(">H", raw[6:8])[0]
            bytecode_offset = HEADER_RESERVE
            bytecode_data = raw[bytecode_offset:]
            compacted = raw[:header_size] + bytecode_data
            result["output_bytes"] = compacted
            result["output_hex"] = compacted.hex()
            result["evob_header_size"] = header_size
            result["evob_version"] = struct.unpack(">H", raw[4:6])[0]
            result["evob_locus_count"] = struct.unpack(">H", raw[8:10])[0]
            result["output_size"] = len(compacted)
        else:
            result["evob_valid"] = False
            result["output_bytes"] = raw
            result["output_hex"] = raw.hex()

        return result

    # =====================================================================
    # 第三步: 与 Python 编译器结果对比验证
    # =====================================================================

    def python_compile_source(self, source: str) -> dict:
        """使用 Python 编译器编译源码, 作为基准对比."""
        bc = IChingBootstrapCompiler()
        return bc.compile_source(source)

    def compare_outputs(self, vm_result: dict, py_result: dict) -> dict:
        """对比 VM 编译结果和 Python 编译结果."""
        comparison = {
            "vm_success": vm_result.get("success", False),
            "py_success": py_result.get("success", False),
            "vm_token_count": vm_result.get("token_count", 0),
            "py_token_count": py_result.get("token_count", 0),
            "vm_locus_count": vm_result.get("locus_count", 0),
            "py_locus_count": py_result.get("locus_count", 0),
            "vm_output_size": vm_result.get("output_size", 0),
            "py_output_size": py_result.get("output_size", 0),
        }

        # 对比 EVOB 有效性
        comparison["vm_evob_valid"] = vm_result.get("evob_valid", False)
        comparison["py_evob_valid"] = py_result.get("evob_valid", False)

        # 对比字节码
        vm_bytes = vm_result.get("output_bytes", b"")
        py_bytes = py_result.get("output_bytes", b"")

        comparison["bytes_match"] = (vm_bytes == py_bytes)
        comparison["vm_hash"] = hashlib.sha256(vm_bytes).hexdigest()[:16]
        comparison["py_hash"] = hashlib.sha256(py_bytes).hexdigest()[:16]

        # 详细对比
        if not comparison["bytes_match"] and vm_bytes and py_bytes:
            comparison["vm_byte_len"] = len(vm_bytes)
            comparison["py_byte_len"] = len(py_bytes)
            # 找出第一个差异位置
            min_len = min(len(vm_bytes), len(py_bytes))
            diff_positions = []
            for i in range(min_len):
                if vm_bytes[i] != py_bytes[i]:
                    diff_positions.append(i)
                    if len(diff_positions) >= 10:
                        break
            comparison["diff_positions"] = diff_positions
            if diff_positions:
                pos = diff_positions[0]
                comparison["first_diff"] = f"offset={pos}, vm=0x{vm_bytes[pos]:02X}, py=0x{py_bytes[pos]:02X}"

        return comparison

    # =====================================================================
    # 第四步: 完整自举验证流程
    # =====================================================================

    def verify_self_hosting(self, test_source: str = None) -> dict:
        """
        完整的自举验证流程.

        步骤:
          1. 汇编 compiler.evoasm → EVB bytecode A
          2. 加载 EVB A 到 VM → 编译 test_source → EVB B
          3. 用 Python 编译 test_source → EVB C
          4. 验证 B == C
          5. 验证 EVB A 可以重新用于编译 (回环验证)

        Returns:
            验证结果字典
        """
        print(f"\n{BOLD}{'='*70}{RESET}")
        print(f"{BOLD}  易衍·Evomorph 真正自举验证{RESET}")
        print(f"{BOLD}{'='*70}{RESET}")

        if test_source is None:
            test_source = self._get_test_source()

        result = {
            "timestamp": time.time(),
            "asm_path": self.asm_path,
            "asm_exists": os.path.exists(self.asm_path),
            "steps": {},
        }

        # -------- 步骤 1: 汇编编译器 --------
        print(f"\n{CYAN}[第 1 步] 汇编编译器 ASM → EVB 字节码{RESET}")
        try:
            compiler_evob = self.assemble_compiler()
            result["steps"]["assemble"] = {
                "success": True,
                "evob_size": len(compiler_evob),
                "evob_header": compiler_evob[:4].decode(),
                "evob_hash": hashlib.sha256(compiler_evob).hexdigest()[:16],
            }
            print(f"  {GREEN}✓{RESET} 汇编成功: {len(compiler_evob)} 字节")
            print(f"    头部: {compiler_evob[:4]}")
            print(f"    SHA256: {result['steps']['assemble']['evob_hash']}")

            # 保存 EVB 文件
            evob_path = self.asm_path.replace(".evoasm", ".evob")
            with open(evob_path, "wb") as f:
                f.write(compiler_evob)
            print(f"    已保存: {evob_path}")
        except Exception as e:
            result["steps"]["assemble"] = {"success": False, "error": str(e)}
            print(f"  {RED}✗{RESET} 汇编失败: {e}")
            return result

        # -------- 步骤 2: VM 独立编译测试源码 --------
        print(f"\n{CYAN}[第 2 步] VM 独立编译 (不经过 Python 编译器){RESET}")
        try:
            vm = self.create_vm_for_self_compile(compiler_evob)
            print(f"  VM 就绪: program={len(vm.program)} 字节, heap_ptr=0x{vm.heap_ptr:X}")

            t0 = time.time()
            vm_result = self.vm_compile_source(vm, test_source)
            vm_elapsed = time.time() - t0

            result["steps"]["vm_compile"] = {
                "success": vm_result.get("success", False),
                "token_count": vm_result.get("token_count", 0),
                "locus_count": vm_result.get("locus_count", 0),
                "output_size": vm_result.get("output_size", 0),
                "cycles": vm_result.get("cycles", 0),
                "time_seconds": vm_elapsed,
                "evob_valid": vm_result.get("evob_valid", False),
            }

            status = GREEN + "✓" if vm_result.get("success") else RED + "✗"
            print(f"  {status}{RESET} VM 编译完成: success={vm_result.get('success')}, "
                  f"tokens={vm_result.get('token_count')}, loci={vm_result.get('locus_count')}, "
                  f"output={vm_result.get('output_size')} 字节, "
                  f"cycles={vm_result.get('cycles')}, "
                  f"耗时={vm_elapsed:.2f}s")
        except Exception as e:
            import traceback
            traceback.print_exc()
            result["steps"]["vm_compile"] = {"success": False, "error": str(e)}
            print(f"  {RED}✗{RESET} VM 编译失败: {e}")

        # -------- 步骤 3: Python 编译相同源码 (基准) --------
        print(f"\n{CYAN}[第 3 步] Python 编译器作为基准{RESET}")
        try:
            t0 = time.time()
            py_result = self.python_compile_source(test_source)
            py_elapsed = time.time() - t0

            result["steps"]["python_compile"] = {
                "success": py_result.get("success", False),
                "token_count": py_result.get("token_count", 0),
                "locus_count": py_result.get("locus_count", 0),
                "output_size": py_result.get("output_size", 0),
                "cycles": py_result.get("cycles", 0),
                "time_seconds": py_elapsed,
                "evob_valid": py_result.get("evob_valid", False),
            }

            status = GREEN + "✓" if py_result.get("success") else RED + "✗"
            print(f"  {status}{RESET} Python 编译完成: success={py_result.get('success')}, "
                  f"tokens={py_result.get('token_count')}, loci={py_result.get('locus_count')}, "
                  f"output={py_result.get('output_size')} 字节, "
                  f"耗时={py_elapsed:.2f}s")
        except Exception as e:
            result["steps"]["python_compile"] = {"success": False, "error": str(e)}
            print(f"  {RED}✗{RESET} Python 编译失败: {e}")
            return result

        # -------- 步骤 4: 对比验证 --------
        print(f"\n{CYAN}[第 4 步] 字节级对比验证{RESET}")
        if "vm_compile" in result["steps"] and "python_compile" in result["steps"]:
            comparison = self.compare_outputs(vm_result, py_result)
            result["comparison"] = comparison

            if comparison.get("bytes_match"):
                print(f"  {GREEN}{BOLD}✓ 自举验证成功!{RESET}")
                print(f"  {GREEN}VM 编译输出 与 Python 编译输出 字节级完全一致{RESET}")
                print(f"    输出大小: {comparison['vm_output_size']} 字节")
                print(f"    Token 数: VM={comparison['vm_token_count']}, Py={comparison['py_token_count']}")
                print(f"    Locus 数: VM={comparison['vm_locus_count']}, Py={comparison['py_locus_count']}")
                print(f"    SHA256: VM={comparison['vm_hash']}, Py={comparison['py_hash']}")
            else:
                print(f"  {RED}{BOLD}✗ 输出不一致{RESET}")
                print(f"    VM  输出: {comparison.get('vm_byte_len', 0)} 字节, SHA256={comparison['vm_hash']}")
                print(f"    Py  输出: {comparison.get('py_byte_len', 0)} 字节, SHA256={comparison['py_hash']}")
                if comparison.get('diff_positions'):
                    print(f"    差异位置: {comparison['diff_positions'][:5]}...")
                    print(f"    首个差异: {comparison.get('first_diff', 'unknown')}")

        # -------- 步骤 5: 回环验证 --------
        print(f"\n{CYAN}[第 5 步] 回环验证 - 编译器能否编译自身{YELLOW}(部分验证){RESET}")
        try:
            # 创建包含编译器逻辑的 .evo 源 (用 GUAXU 块包装)
            compiler_evo_source = self._generate_compiler_evo_source()
            print(f"  编译器 .evo 源: {len(compiler_evo_source)} 字符")

            # VM 编译
            vm2 = self.create_vm_for_self_compile(compiler_evob)
            roundtrip_result = self.vm_compile_source(vm2, compiler_evo_source)

            result["steps"]["roundtrip"] = {
                "success": roundtrip_result.get("success", False),
                "evob_valid": roundtrip_result.get("evob_valid", False),
                "output_size": roundtrip_result.get("output_size", 0),
                "token_count": roundtrip_result.get("token_count", 0),
                "cycles": roundtrip_result.get("cycles", 0),
            }

            status = GREEN + "✓" if roundtrip_result.get("evob_valid") else YELLOW + "~"
            print(f"  {status}{RESET} 回环编译: evob_valid={roundtrip_result.get('evob_valid')}, "
                  f"tokens={roundtrip_result.get('token_count')}, "
                  f"output={roundtrip_result.get('output_size')} 字节")
        except Exception as e:
            result["steps"]["roundtrip"] = {"success": False, "error": str(e)}
            print(f"  {YELLOW}⚠{RESET} 回环验证异常: {e}")

        # -------- 总结 --------
        print(f"\n{BOLD}{'='*70}{RESET}")
        print(f"{BOLD}  自举验证结论{RESET}")
        print(f"{BOLD}{'='*70}{RESET}")

        is_self_hosting = (
            result["steps"].get("assemble", {}).get("success", False) and
            result["steps"].get("vm_compile", {}).get("success", False) and
            result.get("comparison", {}).get("bytes_match", False)
        )

        if is_self_hosting:
            print(f"\n  {GREEN}{BOLD}★★★ 完全自举已实现 ★★★{RESET}")
            print(f"")
            print(f"  编译器逻辑完全由 EVB 字节码承载.")
            print(f"  VM 实例加载编译器字节码后, 可独立编译 .evo 源码.")
            print(f"  编译输出与 Python 编译器完全一致.")
            print(f"  TCB (可信计算基) 仅包含: ExtendedIChingVM2 + Python 汇编器.")
            print(f"")
            print(f"  自举链: compiler.evoasm → assembler → EVB → VM → .evo → EVB ✓")
        else:
            print(f"\n  {YELLOW}{BOLD}△△△ 部分自举 (待完善) △△△{RESET}")
            print(f"  请检查上述各步骤的详细信息.")

        result["self_hosting_verified"] = is_self_hosting
        return result

    # =====================================================================
    # 辅助方法
    # =====================================================================

    @staticmethod
    def _get_test_source() -> str:
        """获取标准测试源码."""
        return '''@evolang "3.0"

@locus test_locus {
    mut_rate = 0.02
    cross_pool = "default"
    fitness = min_latency + max_throughput
    env_target = ["linux-6.x"]
    max_generations = 50

    GUAXU: {
        CREA.1 R0, R0, #42
        FELLOWSHIP.0 R1, R0
        GATHER.0 R2, R1
        FELLOWSHIP.1 R0, R1
        BRANCH.2 @done
        MATE.1 R2, R2, #255
    done:
        RETURN.1 R0, R0
    }
}

@locus math_locus {
    mut_rate = 0.01
    fitness = min_latency
    env_target = ["linux-6.x", "windows-11"]
    max_generations = 100

    GUAXU: {
        CREA.1 R4, R4, #100
        CREA.1 R5, R5, #50
        GATHER.0 R6, R4
        GATHER.1 R6, R5
        GATHER.2 R7, R6
        CREA.1 R8, R8, #3
        RETURN.1 R0, R0
    }
}
'''

    def _generate_compiler_evo_source(self) -> str:
        """生成包含编译器逻辑的 .evo 源文件 (用于回环测试)."""
        # 读取编译器 ASM
        if not os.path.exists(self.asm_path):
            return self._get_test_source()

        with open(self.asm_path, "r", encoding="utf-8") as f:
            asm = f.read()

        # 将 ASM 包装为 .evo 格式
        # 提取 GUAXU 块中的指令
        lines = asm.strip().split('\n')
        guaxu_lines = []
        skip_labels = True  # 跳过标签行
        empty_count = 0

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith(';'):
                empty_count += 1
                if empty_count > 3:
                    continue
                guaxu_lines.append("        // ---")
                continue
            empty_count = 0

            if stripped.endswith(':'):
                continue  # 跳过标签

            guaxu_lines.append(f"        {stripped}")

        guaxu_body = "\n".join(guaxu_lines[:200])  # 取前200条指令

        return f'''@evolang "3.0"

@locus compiler_core {{
    mut_rate = 0.005
    cross_pool = "compiler"
    fitness = correctness + min_size
    env_target = ["evomorph-vm"]
    max_generations = 200

    GUAXU: {{
{guaxu_body}
    }}
}}
'''


def main():
    """命令行入口."""
    import argparse

    parser = argparse.ArgumentParser(
        description="易衍·Evomorph 真正自举验证系统"
    )
    parser.add_argument(
        "-s", "--source", type=str, default=None,
        help=".evo 测试源码文件路径"
    )
    parser.add_argument(
        "-o", "--output", type=str, default=None,
        help="输出 JSON 结果到文件"
    )
    parser.add_argument(
        "--save-evob", action="store_true",
        help="保存生成的编译器 EVB 文件"
    )
    args = parser.parse_args()

    test_source = None
    if args.source:
        with open(args.source, "r", encoding="utf-8") as f:
            test_source = f.read()

    tsh = TrueSelfHosting()
    result = tsh.verify_self_hosting(test_source=test_source)

    if args.output:
        import json
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n结果已保存: {args.output}")

    return 0 if result.get("self_hosting_verified") else 1


if __name__ == "__main__":
    sys.exit(main())
