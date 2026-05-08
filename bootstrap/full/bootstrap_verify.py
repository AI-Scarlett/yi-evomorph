#!/usr/bin/env python3
"""
EvoASM Bootstrap Verification Tool
===================================
Phase 5 Bootstrap Verification per BOOTSTRAP_FINAL_REPORT.md

Verification steps:
1. Assemble assembler_complete.evoasm using Python assembler v2 → v1.raw
2. Run v1.raw on IChingVM with its own source → v2.raw
3. Run v2.raw on IChingVM with its own source → v3.raw (if v2 works)
4. Verify v2 == v3 (byte-level comparison)

Usage:
  python3 bootstrap_verify.py [--full]
"""

import sys
import os
import hashlib
import subprocess
import shutil
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
VM_PATH = os.path.join(PROJECT_DIR, "bootstrap", "runtime", "ichingvm_bootstrap")
ASM_PATH = os.path.join(SCRIPT_DIR, "evoasm_assembler_v2.py")
GEN_PATH = os.path.join(SCRIPT_DIR, "generate_assembler.py")
EVOASM_PATH = os.path.join(SCRIPT_DIR, "assembler_complete.evoasm")
TMP_DIR = os.path.join(SCRIPT_DIR, "verify_tmp")

# Import Assembler for source preprocessing (macro expansion)
sys.path.insert(0, SCRIPT_DIR)
from evoasm_assembler_v2 import Assembler


def run_cmd(cmd, cwd=None):
    """Run a command and return (returncode, stdout, stderr)."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout, result.stderr


def sha256(filepath):
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(step, success, detail=""):
    status = "✓ PASS" if success else "✗ FAIL"
    print(f"  [{status}] {step}")
    if detail:
        for line in detail.split('\n'):
            if line.strip():
                print(f"         {line.strip()}")


def step1_generate_assembler():
    """Step 1: Generate the EvoASM assembler source."""
    print_header("Step 1: Generate EvoASM Assembler Source")
    
    rc, out, err = run_cmd(f"python3 {GEN_PATH}", cwd=SCRIPT_DIR)
    if rc != 0:
        print_result("Generate assembler source", False, err)
        return False
    
    with open(EVOASM_PATH, 'w') as f:
        f.write(out)
    
    line_count = len(out.split('\n'))
    print_result("Generate assembler source", True, f"Generated {line_count} lines → {EVOASM_PATH}")
    return True


def step2_assemble_v1():
    """Step 2: Assemble with Python assembler v2 → v1.raw."""
    print_header("Step 2: Python Assembler v2 → v1.raw")
    
    os.makedirs(TMP_DIR, exist_ok=True)
    v1_path = os.path.join(TMP_DIR, "v1.raw")
    
    rc, out, err = run_cmd(
        f"python3 {ASM_PATH} {EVOASM_PATH} -o {v1_path}",
        cwd=SCRIPT_DIR
    )
    
    if rc != 0:
        print_result("Python assemble v1", False, err)
        return False
    
    size = os.path.getsize(v1_path)
    v1_hash = sha256(v1_path)
    print_result("Python assemble v1", True,
                 f"{size} bytes, SHA-256: {v1_hash[:16]}...")
    return v1_path


def build_equ_dict(source_lines):
    """Parse EQU definitions from source lines and return {name: value} dict."""
    equ_dict = {}
    for line in source_lines:
        stripped = line.strip()
        if 'EQU' in stripped.upper():
            # Parse "NAME EQU value" lines
            parts = stripped.split()
            # Handle both "NAME EQU value" and "NAME EQU value ; comment"
            equ_idx = None
            for i, p in enumerate(parts):
                if p.upper() == 'EQU':
                    equ_idx = i
                    break
            if equ_idx and equ_idx > 0 and equ_idx + 1 < len(parts):
                name = parts[equ_idx - 1].upper()
                val_str = parts[equ_idx + 1]
                try:
                    if val_str.startswith('0x') or val_str.startswith('0X'):
                        val = int(val_str, 16)
                    elif val_str.startswith('0b') or val_str.startswith('0B'):
                        val = int(val_str, 2)
                    else:
                        val = int(val_str)
                    equ_dict[name] = val
                except ValueError:
                    pass
    return equ_dict


def preprocess_source_for_vm():
    """Preprocess the assembler source: expand macros, remove EQU lines,
    and substitute EQU constants with their numeric values.
    The VM-based assembler expects clean EvoASM code without macros/EQU/names."""
    import re
    
    with open(EVOASM_PATH, 'r') as f:
        source = f.read()
    
    assembler = Assembler()
    lines = source.splitlines()
    
    # Build EQU dictionary from original source (before preprocessing removes them)
    equ_dict = build_equ_dict(lines)
    
    # Preprocess: expand macros, remove EQU lines
    preprocessed = assembler.preprocess(lines)
    result_text = '\n'.join(preprocessed)
    
    # Substitute EQU constants using word-boundary regex
    # Sort by longest name first to avoid partial matches
    for name in sorted(equ_dict.keys(), key=len, reverse=True):
        value = equ_dict[name]
        # Only substitute in non-comment parts (before ';')
        # Use regex to match whole word (not part of another identifier)
        result_text = re.sub(
            r'\b' + re.escape(name) + r'\b',
            str(value),
            result_text
        )
    
    return result_text


def step3_vm_assemble_v2(v1_path):
    """Step 3: Run v1.raw on VM with its own source → v2.raw."""
    print_header("Step 3: VM Run (v1 → v2)")
    
    v2_path = os.path.join(TMP_DIR, "v2.raw")
    output_evob = os.path.join(TMP_DIR, "output.evob")
    input_evoasm = os.path.join(TMP_DIR, "input.evoasm")
    
    # Setup: preprocess source (expand macros) and save as input.evoasm
    preprocessed = preprocess_source_for_vm()
    with open(input_evoasm, 'w') as f:
        f.write(preprocessed)
    print(f"  Preprocessed source: {len(preprocessed.splitlines())} lines → {input_evoasm}")
    
    # Remove old output if exists
    if os.path.exists(output_evob):
        os.remove(output_evob)
    
    # Run VM with the assembler binary (needs ~3M cycles)
    rc, out, err = run_cmd(
        f"{VM_PATH} run {v1_path} 10000000",
        cwd=TMP_DIR
    )
    
    if "HALTED" not in out and "halted" not in out.lower():
        print_result("VM execute v1", False,
                     f"VM did not halt cleanly.\n"
                     f"Return code: {rc}\n"
                     f"VM state:\n{out[-500:] if len(out)>500 else out}")
        # Check if output.evob was created anyway
        if os.path.exists(output_evob):
            shutil.copy(output_evob, v2_path)
            size = os.path.getsize(v2_path)
            print(f"\n  [!] Partial output: {size} bytes written to output.evob")
            return v2_path
        return False
    
    # Check output.evob
    if os.path.exists(output_evob):
        shutil.copy(output_evob, v2_path)
        size = os.path.getsize(v2_path)
        v2_hash = sha256(v2_path)
        print_result("VM execute v1 → v2", True,
                     f"{size} bytes, SHA-256: {v2_hash[:16]}...")
        return v2_path
    else:
        print_result("VM execute v1 → v2", False,
                     "output.evob not created")
        return False


def step4_vm_assemble_v3(v2_path):
    """Step 4: Run v2.raw on VM with source → v3.raw."""
    print_header("Step 4: VM Run (v2 → v3)")
    
    v3_path = os.path.join(TMP_DIR, "v3.raw")
    output_evob = os.path.join(TMP_DIR, "output.evob")
    input_evoasm = os.path.join(TMP_DIR, "input.evoasm")
    
    # Ensure preprocessed source is in place
    preprocessed = preprocess_source_for_vm()
    with open(input_evoasm, 'w') as f:
        f.write(preprocessed)
    
    # Remove old output
    if os.path.exists(output_evob):
        os.remove(output_evob)
    
    rc, out, err = run_cmd(
        f"{VM_PATH} run {v2_path} 10000000",
        cwd=TMP_DIR
    )
    
    if "HALTED" not in out and "halted" not in out.lower():
        print_result("VM execute v2 → v3", False,
                     f"VM did not halt cleanly.\n"
                     f"VM state:\n{out[-500:] if len(out)>500 else out}")
        if os.path.exists(output_evob):
            shutil.copy(output_evob, v3_path)
            return v3_path
        return False
    
    if os.path.exists(output_evob):
        shutil.copy(output_evob, v3_path)
        size = os.path.getsize(v3_path)
        v3_hash = sha256(v3_path)
        print_result("VM execute v2 → v3", True,
                     f"{size} bytes, SHA-256: {v3_hash[:16]}...")
        return v3_path
    else:
        print_result("VM execute v2 → v3", False, "output.evob not created")
        return False


def step5_verify(v2_path, v3_path):
    """Step 5: Verify v2 == v3 (byte-level)."""
    print_header("Step 5: Bootstrap Verification (v2 == v3)")
    
    if not v2_path or not v3_path:
        print_result("Bootstrap verification", False,
                     "Missing v2 or v3 binary")
        return False
    
    with open(v2_path, 'rb') as f:
        v2_data = f.read()
    with open(v3_path, 'rb') as f:
        v3_data = f.read()
    
    v2_hash = hashlib.sha256(v2_data).hexdigest()
    v3_hash = hashlib.sha256(v3_data).hexdigest()
    
    if v2_data == v3_data:
        print_result("v2 == v3 (byte-exact)", True,
                     f"Both {len(v2_data)} bytes, SHA-256: {v2_hash[:16]}...")
        return True
    else:
        print_result("v2 == v3 (byte-exact)", False,
                     f"v2: {len(v2_data)} bytes, SHA-256: {v2_hash[:16]}...\n"
                     f"v3: {len(v3_data)} bytes, SHA-256: {v3_hash[:16]}...")
        # Show first difference
        for i in range(min(len(v2_data), len(v3_data))):
            if v2_data[i] != v3_data[i]:
                print(f"         First diff at offset {i}: "
                      f"v2=0x{v2_data[i]:02X} v3=0x{v3_data[i]:02X}")
                break
        return False


def test_simple_program():
    """Test assembler with a simple program."""
    print_header("Bonus: Test with Simple Program")
    
    test_src = os.path.join(SCRIPT_DIR, "test_hello.evoasm")
    test_input = os.path.join(TMP_DIR, "input.evoasm")
    test_output = os.path.join(TMP_DIR, "test_v2.raw")
    output_evob = os.path.join(TMP_DIR, "output.evob")
    
    shutil.copy(test_src, test_input)
    if os.path.exists(output_evob):
        os.remove(output_evob)
    
    v1_path = os.path.join(TMP_DIR, "v1.raw")
    
    rc, out, err = run_cmd(
        f"{VM_PATH} run {v1_path} 5000000",
        cwd=TMP_DIR
    )
    
    if os.path.exists(output_evob):
        size = os.path.getsize(output_evob)
        print_result("Test program assembly", True,
                     f"Output: {size} bytes")
        return True
    else:
        print_result("Test program assembly", False,
                     f"No output produced\n"
                     f"VM: {out[-300:] if len(out)>300 else out}")
        return False


def print_summary(results):
    """Print verification summary."""
    print_header("Verification Summary")
    total = len(results)
    passed = sum(1 for _, success in results if success)
    
    for step, success in results:
        status = "✓" if success else "✗"
        print(f"  [{status}] {step}")
    
    print(f"\n  {passed}/{total} steps passed")
    
    if passed == total:
        print("\n  🎉 ALL CHECKS PASSED - Bootstrap verification complete!")
    else:
        print("\n  ⚠ Some checks failed - see details above.")


def main():
    print_header("EvoASM Bootstrap Verification v1.0")
    print(f"  Project: {PROJECT_DIR}")
    print(f"  VM: {VM_PATH}")
    print(f"  Assembler: {ASM_PATH}")
    
    results = []
    
    # Step 1: Generate assembler source
    ok = step1_generate_assembler()
    results.append(("Generate assembler source", ok))
    if not ok:
        print_summary(results)
        return 1
    
    # Step 2: Assemble v1 with Python
    v1_path = step2_assemble_v1()
    results.append(("Python assemble v1", bool(v1_path)))
    if not v1_path:
        print_summary(results)
        return 1
    
    # Step 3: VM run v1 → v2
    v2_path = step3_vm_assemble_v2(v1_path)
    results.append(("VM run v1 → v2", bool(v2_path)))
    
    # Step 4: VM run v2 → v3
    v3_path = False
    if v2_path:
        v3_path = step4_vm_assemble_v3(v2_path)
    results.append(("VM run v2 → v3", bool(v3_path)))
    
    # Step 5: Verify v2 == v3
    verified = step5_verify(v2_path, v3_path)
    results.append(("Bootstrap verify (v2==v3)", verified))
    
    # Bonus: test with simple program
    test_ok = test_simple_program()
    results.append(("Simple program test", test_ok))
    
    print_summary(results)
    return 0 if verified else 1


if __name__ == "__main__":
    sys.exit(main())
