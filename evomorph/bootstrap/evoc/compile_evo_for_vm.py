#!/usr/bin/env python3
"""
将易衍 .evo 文件编译为 C 虚拟机可执行的格式
"""

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))
sys.path.insert(0, PROJECT_ROOT)

from evomorph.compiler import EvocCompiler
from evomorph.hexagrams import HexagramInstructionSet


def compile_to_asm(evo_file: str, asm_file: str):
    """将 .evo 文件编译为 .asm 汇编文件"""
    
    print(f"编译: {evo_file} -> {asm_file}")
    
    compiler = EvocCompiler()
    isa = HexagramInstructionSet()
    
    result = compiler.compile_file(evo_file, output_format='dict')
    
    if result.get('errors'):
        print("编译错误:")
        for err in result['errors']:
            print(f"  {err}")
        return False
    
    loci = result.get('loci', [])
    print(f"  基因座数量: {len(loci)}")
    
    asm_lines = [
        "; 易衍·Evomorph 编译输出",
        f"; 源文件: {evo_file}",
        f"; 基因座数量: {len(loci)}",
        "",
        "; 初始化寄存器",
        "ABOUND R0, 0",
        "ABOUND R1, 0",
        "ABOUND R2, 0",
        "ABOUND R3, 0",
        "ABOUND R4, 0",
        "ABOUND R5, 0",
        "ABOUND R6, 0",
        "ABOUND R7, 0",
        "ABOUND R8, 0",
        "ABOUND R9, 0",
        "ABOUND R10, 0",
        "ABOUND R11, 0",
        "ABOUND R12, 0",
        "ABOUND R13, 65536",
        "ABOUND R14, 0",
        "ABOUND R15, 0",
        "",
    ]
    
    for locus in loci:
        locus_name = locus.get('name', 'unknown')
        instructions = locus.get('instructions', [])
        
        asm_lines.append(f"; --- 基因座: {locus_name} ---")
        asm_lines.append(f"; 指令数量: {len(instructions)}")
        
        for instr in instructions:
            if 'error' in instr:
                asm_lines.append(f"; 错误: {instr['error']}")
                continue
            
            mnemonic = instr.get('mnemonic', 'NOP')
            symbol = instr.get('symbol', '?')
            operands = instr.get('operands', [])
            
            op_strs = []
            for op in operands:
                if isinstance(op, dict):
                    kind = op.get('kind', 'unknown')
                    value = op.get('value', 0)
                    if kind == 'register':
                        op_strs.append(f"R{value}")
                    else:
                        op_strs.append(str(value))
                else:
                    op_strs.append(f"R{op}" if isinstance(op, int) and op <= 15 else str(op))
            
            if op_strs:
                asm_line = f"{mnemonic} {', '.join(op_strs)}"
            else:
                asm_line = mnemonic
            
            asm_lines.append(asm_line)
        
        asm_lines.append("")
    
    asm_lines.append("; 停止执行")
    asm_lines.append("HALT")
    
    asm_content = "\n".join(asm_lines)
    
    with open(asm_file, 'w', encoding='utf-8') as f:
        f.write(asm_content)
    
    print(f"  汇编文件已生成: {asm_file}")
    return True


def assemble_and_run(asm_file: str, raw_file: str = None, vm_path: str = None):
    """汇编并运行"""
    
    if raw_file is None:
        raw_file = asm_file.replace('.asm', '.raw')
    
    if vm_path is None:
        vm_path = os.path.join(PROJECT_ROOT, 'bootstrap', 'runtime', 'ichingvm_bootstrap')
    
    print(f"\n汇编: {asm_file} -> {raw_file}")
    
    import subprocess
    
    result = subprocess.run(
        [vm_path, 'asm', asm_file, raw_file],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"汇编失败: {result.stderr}")
        return False
    
    print(f"  {result.stdout.strip()}")
    
    print(f"\n运行: {raw_file}")
    
    result = subprocess.run(
        [vm_path, 'run', raw_file, '100000'],
        capture_output=True,
        text=True
    )
    
    print(f"退出码: {result.returncode}")
    if result.stdout:
        print(f"标准输出:\n{result.stdout}")
    if result.stderr:
        print(f"标准错误:\n{result.stderr}")
    
    return True


def main():
    if len(sys.argv) < 2:
        print("用法: python3 compile_evo_for_vm.py <evo_file> [asm_file] [raw_file]")
        print("示例: python3 compile_evo_for_vm.py evo_cli.evo")
        sys.exit(1)
    
    evo_file = sys.argv[1]
    
    if len(sys.argv) >= 3:
        asm_file = sys.argv[2]
    else:
        asm_file = evo_file.replace('.evo', '.asm')
    
    if len(sys.argv) >= 4:
        raw_file = sys.argv[3]
    else:
        raw_file = asm_file.replace('.asm', '.raw')
    
    if not os.path.exists(evo_file):
        print(f"错误: 文件不存在: {evo_file}")
        sys.exit(1)
    
    if compile_to_asm(evo_file, asm_file):
        assemble_and_run(asm_file, raw_file)


if __name__ == "__main__":
    main()
