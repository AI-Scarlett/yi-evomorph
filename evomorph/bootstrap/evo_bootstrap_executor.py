#!/usr/bin/env python3
"""
易衍自举编译器执行器
扩展虚拟机，支持系统调用机制，让易衍代码可以调用Python编译原语
"""

import sys
import os
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evomorph.vm.virtual_machine import IChingVM, VMState
from evomorph.bootstrap.complete_bootstrap_runtime import CompleteBootstrapRuntime


class SyscallNumbers:
    LEXER_TOKENIZE = 0x01
    LEXER_INIT = 0x02
    LEXER_ADVANCE = 0x03
    LEXER_PEEK = 0x04
    LEXER_SCAN_IDENTIFIER = 0x05
    LEXER_SCAN_NUMBER = 0x06
    LEXER_SCAN_STRING = 0x07
    LEXER_SKIP_COMMENT = 0x08
    
    PARSER_PARSE = 0x10
    PARSER_INIT = 0x11
    PARSER_ADVANCE = 0x12
    PARSER_PEEK = 0x13
    PARSER_EXPECT = 0x14
    PARSER_MATCH = 0x15
    
    CODEGEN_GENERATE = 0x20
    CODEGEN_ENCODE_OPCODE = 0x21
    CODEGEN_ENCODE_OPERAND = 0x22
    CODEGEN_EMIT_INSTRUCTION = 0x23
    CODEGEN_GENERATE_EVB = 0x24
    
    VM_EXECUTE = 0x30
    VM_RUN = 0x31
    VM_STEP = 0x32
    VM_LOAD_PROGRAM = 0x33
    VM_GET_REG = 0x34
    VM_SET_REG = 0x35
    
    EVO_EVOLVE = 0x40
    EVO_SELECT = 0x41
    EVO_CROSSOVER = 0x42
    EVO_MUTATE = 0x43
    EVO_EVALUATE_FITNESS = 0x44
    
    FULL_COMPILE = 0x50
    COMPARE_COMPILERS = 0x51
    ANALYZE_GAPS = 0x52
    SELF_COMPILE_TEST = 0x53
    CONTINUOUS_BOOTSTRAP = 0x54
    
    MEM_ALLOC = 0x60
    MEM_FREE = 0x61
    MEM_COPY = 0x62
    MEM_SET = 0x63
    
    STR_LEN = 0x70
    STR_CONCAT = 0x71
    STR_SUBSTR = 0x72
    STR_FIND = 0x73
    STR_CMP = 0x74
    STR_PARSE_INT = 0x75
    STR_INT_TO_STR = 0x76
    
    PRINT = 0x80
    INPUT = 0x81
    OPEN_FILE = 0x82
    READ_FILE = 0x83
    WRITE_FILE = 0x84
    CLOSE_FILE = 0x85
    
    LIST_NEW = 0x90
    LIST_APPEND = 0x91
    LIST_GET = 0x92
    LIST_SET = 0x93
    LIST_LEN = 0x94
    LIST_REMOVE = 0x95
    LIST_INSERT = 0x96
    
    MAP_NEW = 0xA0
    MAP_PUT = 0xA1
    MAP_GET = 0xA2
    MAP_CONTAINS = 0xA3
    MAP_REMOVE = 0xA4
    MAP_KEYS = 0xA5
    MAP_VALUES = 0xA6
    
    GET_INPUT_SOURCE = 0xF0
    SET_OUTPUT_RESULT = 0xF1
    GET_ARG_COUNT = 0xF2
    GET_ARG = 0xF3
    EXIT = 0xFF


class EvoBootstrapExecutor:
    def __init__(self):
        self.runtime = CompleteBootstrapRuntime()
        self.vm = IChingVM()
        self.memory: Dict[int, Any] = {}
        self.next_mem_id = 1
        self.input_source: str = ""
        self.output_result: Any = None
        self.args: List[str] = []
        self._setup_syscall_handlers()
        self._setup_io_ports()
    
    def _setup_syscall_handlers(self):
        self.syscall_handlers = {
            SyscallNumbers.LEXER_TOKENIZE: self._sys_lexer_tokenize,
            SyscallNumbers.LEXER_INIT: self._sys_lexer_init,
            SyscallNumbers.LEXER_ADVANCE: self._sys_lexer_advance,
            SyscallNumbers.LEXER_PEEK: self._sys_lexer_peek,
            SyscallNumbers.LEXER_SCAN_IDENTIFIER: self._sys_lexer_scan_identifier,
            SyscallNumbers.LEXER_SCAN_NUMBER: self._sys_lexer_scan_number,
            SyscallNumbers.LEXER_SCAN_STRING: self._sys_lexer_scan_string,
            SyscallNumbers.LEXER_SKIP_COMMENT: self._sys_lexer_skip_comment,
            
            SyscallNumbers.PARSER_PARSE: self._sys_parser_parse,
            SyscallNumbers.PARSER_INIT: self._sys_parser_init,
            SyscallNumbers.PARSER_ADVANCE: self._sys_parser_advance,
            SyscallNumbers.PARSER_PEEK: self._sys_parser_peek,
            SyscallNumbers.PARSER_EXPECT: self._sys_parser_expect,
            SyscallNumbers.PARSER_MATCH: self._sys_parser_match,
            
            SyscallNumbers.CODEGEN_GENERATE: self._sys_codegen_generate,
            SyscallNumbers.CODEGEN_ENCODE_OPCODE: self._sys_codegen_encode_opcode,
            SyscallNumbers.CODEGEN_ENCODE_OPERAND: self._sys_codegen_encode_operand,
            SyscallNumbers.CODEGEN_EMIT_INSTRUCTION: self._sys_codegen_emit_instruction,
            SyscallNumbers.CODEGEN_GENERATE_EVB: self._sys_codegen_generate_evb,
            
            SyscallNumbers.VM_EXECUTE: self._sys_vm_execute,
            SyscallNumbers.VM_RUN: self._sys_vm_run,
            SyscallNumbers.VM_STEP: self._sys_vm_step,
            SyscallNumbers.VM_LOAD_PROGRAM: self._sys_vm_load_program,
            SyscallNumbers.VM_GET_REG: self._sys_vm_get_reg,
            SyscallNumbers.VM_SET_REG: self._sys_vm_set_reg,
            
            SyscallNumbers.EVO_EVOLVE: self._sys_evo_evolve,
            SyscallNumbers.EVO_SELECT: self._sys_evo_select,
            SyscallNumbers.EVO_CROSSOVER: self._sys_evo_crossover,
            SyscallNumbers.EVO_MUTATE: self._sys_evo_mutate,
            SyscallNumbers.EVO_EVALUATE_FITNESS: self._sys_evo_evaluate_fitness,
            
            SyscallNumbers.FULL_COMPILE: self._sys_full_compile,
            SyscallNumbers.COMPARE_COMPILERS: self._sys_compare_compilers,
            SyscallNumbers.ANALYZE_GAPS: self._sys_analyze_gaps,
            SyscallNumbers.SELF_COMPILE_TEST: self._sys_self_compile_test,
            SyscallNumbers.CONTINUOUS_BOOTSTRAP: self._sys_continuous_bootstrap,
            
            SyscallNumbers.MEM_ALLOC: self._sys_mem_alloc,
            SyscallNumbers.MEM_FREE: self._sys_mem_free,
            SyscallNumbers.MEM_COPY: self._sys_mem_copy,
            SyscallNumbers.MEM_SET: self._sys_mem_set,
            
            SyscallNumbers.STR_LEN: self._sys_str_len,
            SyscallNumbers.STR_CONCAT: self._sys_str_concat,
            SyscallNumbers.STR_SUBSTR: self._sys_str_substr,
            SyscallNumbers.STR_FIND: self._sys_str_find,
            SyscallNumbers.STR_CMP: self._sys_str_cmp,
            SyscallNumbers.STR_PARSE_INT: self._sys_str_parse_int,
            SyscallNumbers.STR_INT_TO_STR: self._sys_str_int_to_str,
            
            SyscallNumbers.PRINT: self._sys_print,
            SyscallNumbers.INPUT: self._sys_input,
            SyscallNumbers.OPEN_FILE: self._sys_open_file,
            SyscallNumbers.READ_FILE: self._sys_read_file,
            SyscallNumbers.WRITE_FILE: self._sys_write_file,
            SyscallNumbers.CLOSE_FILE: self._sys_close_file,
            
            SyscallNumbers.LIST_NEW: self._sys_list_new,
            SyscallNumbers.LIST_APPEND: self._sys_list_append,
            SyscallNumbers.LIST_GET: self._sys_list_get,
            SyscallNumbers.LIST_SET: self._sys_list_set,
            SyscallNumbers.LIST_LEN: self._sys_list_len,
            SyscallNumbers.LIST_REMOVE: self._sys_list_remove,
            SyscallNumbers.LIST_INSERT: self._sys_list_insert,
            
            SyscallNumbers.MAP_NEW: self._sys_map_new,
            SyscallNumbers.MAP_PUT: self._sys_map_put,
            SyscallNumbers.MAP_GET: self._sys_map_get,
            SyscallNumbers.MAP_CONTAINS: self._sys_map_contains,
            SyscallNumbers.MAP_REMOVE: self._sys_map_remove,
            SyscallNumbers.MAP_KEYS: self._sys_map_keys,
            SyscallNumbers.MAP_VALUES: self._sys_map_values,
            
            SyscallNumbers.GET_INPUT_SOURCE: self._sys_get_input_source,
            SyscallNumbers.SET_OUTPUT_RESULT: self._sys_set_output_result,
            SyscallNumbers.GET_ARG_COUNT: self._sys_get_arg_count,
            SyscallNumbers.GET_ARG: self._sys_get_arg,
            SyscallNumbers.EXIT: self._sys_exit,
        }
    
    def _setup_io_ports(self):
        port_counter = 0
        
        def make_port_handler(value_func):
            nonlocal port_counter
            port = port_counter
            port_counter += 1
            
            def handler():
                val = value_func()
                if isinstance(val, int):
                    return val
                elif isinstance(val, str):
                    mem_id = self._alloc_mem(val)
                    return mem_id
                return 0
            
            self.vm.register_io_handler(port, handler)
            return port
        
        self.PORT_INPUT_SOURCE = make_port_handler(lambda: self.input_source)
        self.PORT_ARG_COUNT = make_port_handler(lambda: len(self.args))
        self.PORT_NEXT_ARG = make_port_handler(lambda: self.args.pop(0) if self.args else "")
    
    def _alloc_mem(self, value: Any) -> int:
        mem_id = self.next_mem_id
        self.next_mem_id += 1
        self.memory[mem_id] = value
        return mem_id
    
    def _get_mem(self, mem_id: int) -> Any:
        return self.memory.get(mem_id)
    
    def _free_mem(self, mem_id: int):
        if mem_id in self.memory:
            del self.memory[mem_id]
    
    def _sys_lexer_tokenize(self, vm: IChingVM):
        source_mem_id = vm.registers[1]
        source = self._get_mem(source_mem_id)
        if source is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._lexer_tokenize(source)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_lexer_init(self, vm: IChingVM):
        source_mem_id = vm.registers[1]
        source = self._get_mem(source_mem_id)
        if source is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._lexer_init(source)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_lexer_advance(self, vm: IChingVM):
        state_mem_id = vm.registers[1]
        state = self._get_mem(state_mem_id)
        if state is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._lexer_advance(state)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_lexer_peek(self, vm: IChingVM):
        state_mem_id = vm.registers[1]
        offset = vm.registers[2]
        state = self._get_mem(state_mem_id)
        if state is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._lexer_peek(state, offset)
        if isinstance(result, str):
            vm.registers[0] = self._alloc_mem(result)
        else:
            vm.registers[0] = result if result is not None else 0
    
    def _sys_lexer_scan_identifier(self, vm: IChingVM):
        state_mem_id = vm.registers[1]
        state = self._get_mem(state_mem_id)
        if state is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._lexer_scan_identifier(state)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_lexer_scan_number(self, vm: IChingVM):
        state_mem_id = vm.registers[1]
        state = self._get_mem(state_mem_id)
        if state is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._lexer_scan_number(state)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_lexer_scan_string(self, vm: IChingVM):
        state_mem_id = vm.registers[1]
        state = self._get_mem(state_mem_id)
        if state is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._lexer_scan_string(state)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_lexer_skip_comment(self, vm: IChingVM):
        state_mem_id = vm.registers[1]
        state = self._get_mem(state_mem_id)
        if state is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._lexer_skip_comment(state)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_parser_parse(self, vm: IChingVM):
        tokens_mem_id = vm.registers[1]
        tokens = self._get_mem(tokens_mem_id)
        if tokens is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._parser_parse(tokens)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_parser_init(self, vm: IChingVM):
        tokens_mem_id = vm.registers[1]
        tokens = self._get_mem(tokens_mem_id)
        if tokens is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._parser_init(tokens)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_parser_advance(self, vm: IChingVM):
        state_mem_id = vm.registers[1]
        state = self._get_mem(state_mem_id)
        if state is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._parser_advance(state)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_parser_peek(self, vm: IChingVM):
        state_mem_id = vm.registers[1]
        offset = vm.registers[2]
        state = self._get_mem(state_mem_id)
        if state is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._parser_peek(state, offset)
        if result is None:
            vm.registers[0] = 0
        else:
            result_mem_id = self._alloc_mem(result)
            vm.registers[0] = result_mem_id
    
    def _sys_parser_expect(self, vm: IChingVM):
        state_mem_id = vm.registers[1]
        expected_mem_id = vm.registers[2]
        state = self._get_mem(state_mem_id)
        expected = self._get_mem(expected_mem_id)
        if state is None or expected is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._parser_expect(state, expected)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_parser_match(self, vm: IChingVM):
        state_mem_id = vm.registers[1]
        expected_mem_id = vm.registers[2]
        state = self._get_mem(state_mem_id)
        expected = self._get_mem(expected_mem_id)
        if state is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._parser_match(state, expected)
        vm.registers[0] = 1 if result else 0
    
    def _sys_codegen_generate(self, vm: IChingVM):
        ast_mem_id = vm.registers[1]
        ast = self._get_mem(ast_mem_id)
        if ast is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._codegen_generate(ast)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_codegen_encode_opcode(self, vm: IChingVM):
        ast_mem_id = vm.registers[1]
        ast = self._get_mem(ast_mem_id)
        if ast is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._codegen_encode_opcode(ast)
        vm.registers[0] = result
    
    def _sys_codegen_encode_operand(self, vm: IChingVM):
        operand_mem_id = vm.registers[1]
        operand = self._get_mem(operand_mem_id)
        if operand is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._codegen_encode_operand(operand)
        vm.registers[0] = result
    
    def _sys_codegen_emit_instruction(self, vm: IChingVM):
        state_mem_id = vm.registers[1]
        instr_mem_id = vm.registers[2]
        state = self._get_mem(state_mem_id)
        instr = self._get_mem(instr_mem_id)
        if state is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._codegen_emit_instruction(state, instr)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_codegen_generate_evb(self, vm: IChingVM):
        ast_mem_id = vm.registers[1]
        ast = self._get_mem(ast_mem_id)
        if ast is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._codegen_generate_evb(ast)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_vm_execute(self, vm: IChingVM):
        state_mem_id = vm.registers[1]
        opcode = vm.registers[2]
        modifier = vm.registers[3]
        operands_mem_id = vm.registers[4]
        
        state = self._get_mem(state_mem_id)
        operands = self._get_mem(operands_mem_id)
        if state is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._vm_execute(state, opcode, modifier, operands or [])
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_vm_run(self, vm: IChingVM):
        state_mem_id = vm.registers[1]
        max_cycles = vm.registers[2]
        state = self._get_mem(state_mem_id)
        if state is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._vm_run(state, max_cycles if max_cycles > 0 else None)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_vm_step(self, vm: IChingVM):
        state_mem_id = vm.registers[1]
        state = self._get_mem(state_mem_id)
        if state is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._vm_step(state)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_vm_load_program(self, vm: IChingVM):
        bytecode_mem_id = vm.registers[1]
        bytecode = self._get_mem(bytecode_mem_id)
        if bytecode is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._vm_load_program(bytecode)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_vm_get_reg(self, vm: IChingVM):
        state_mem_id = vm.registers[1]
        reg_idx = vm.registers[2]
        state = self._get_mem(state_mem_id)
        if state is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._vm_get_register(state, reg_idx)
        vm.registers[0] = result
    
    def _sys_vm_set_reg(self, vm: IChingVM):
        state_mem_id = vm.registers[1]
        reg_idx = vm.registers[2]
        value = vm.registers[3]
        state = self._get_mem(state_mem_id)
        if state is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._vm_set_register(state, reg_idx, value)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_evo_evolve(self, vm: IChingVM):
        seed_genes_mem_id = vm.registers[1]
        generations = vm.registers[2]
        config_mem_id = vm.registers[3]
        
        seed_genes = self._get_mem(seed_genes_mem_id)
        config = self._get_mem(config_mem_id)
        if seed_genes is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._evo_evolve(seed_genes, generations, config)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_evo_select(self, vm: IChingVM):
        population_mem_id = vm.registers[1]
        method_mem_id = vm.registers[2]
        population = self._get_mem(population_mem_id)
        method = self._get_mem(method_mem_id) or "tournament"
        if population is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._evo_select(population, method)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_evo_crossover(self, vm: IChingVM):
        parent1_mem_id = vm.registers[1]
        parent2_mem_id = vm.registers[2]
        method_mem_id = vm.registers[3]
        parent1 = self._get_mem(parent1_mem_id)
        parent2 = self._get_mem(parent2_mem_id)
        method = self._get_mem(method_mem_id) or "single_point"
        if parent1 is None or parent2 is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._evo_crossover(parent1, parent2, method)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_evo_mutate(self, vm: IChingVM):
        individual_mem_id = vm.registers[1]
        mut_rate = vm.registers[2] / 100.0 if vm.registers[2] > 0 else 0.02
        individual = self._get_mem(individual_mem_id)
        if individual is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._evo_mutate(individual, mut_rate)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_evo_evaluate_fitness(self, vm: IChingVM):
        individual_mem_id = vm.registers[1]
        individual = self._get_mem(individual_mem_id)
        if individual is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime._evo_evaluate_fitness(individual)
        vm.registers[0] = int(result * 100)
    
    def _sys_full_compile(self, vm: IChingVM):
        source_mem_id = vm.registers[1]
        source = self._get_mem(source_mem_id)
        if source is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime.full_compile(source)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_compare_compilers(self, vm: IChingVM):
        source_mem_id = vm.registers[1]
        source = self._get_mem(source_mem_id)
        if source is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime.compare_compilers(source)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_analyze_gaps(self, vm: IChingVM):
        result = self.runtime.analyze_feature_gaps()
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_self_compile_test(self, vm: IChingVM):
        result = self.runtime.run_self_compile_test()
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_continuous_bootstrap(self, vm: IChingVM):
        source_mem_id = vm.registers[1]
        max_gens = vm.registers[2]
        threshold = vm.registers[3] / 100.0 if vm.registers[3] > 0 else 90.0
        source = self._get_mem(source_mem_id)
        if source is None:
            vm.registers[0] = 0
            return
        
        result = self.runtime.continuous_bootstrap_loop(source, max_gens, threshold)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_mem_alloc(self, vm: IChingVM):
        size = vm.registers[1]
        mem_id = self._alloc_mem(bytearray(size if size > 0 else 256))
        vm.registers[0] = mem_id
    
    def _sys_mem_free(self, vm: IChingVM):
        mem_id = vm.registers[1]
        self._free_mem(mem_id)
        vm.registers[0] = 1
    
    def _sys_mem_copy(self, vm: IChingVM):
        dst_mem_id = vm.registers[1]
        src_mem_id = vm.registers[2]
        size = vm.registers[3]
        dst = self._get_mem(dst_mem_id)
        src = self._get_mem(src_mem_id)
        if dst is None or src is None:
            vm.registers[0] = 0
            return
        
        if isinstance(dst, bytearray) and isinstance(src, (bytes, bytearray)):
            copy_size = min(size, len(src), len(dst))
            dst[:copy_size] = src[:copy_size]
        vm.registers[0] = 1
    
    def _sys_mem_set(self, vm: IChingVM):
        dst_mem_id = vm.registers[1]
        value = vm.registers[2]
        size = vm.registers[3]
        dst = self._get_mem(dst_mem_id)
        if dst is None:
            vm.registers[0] = 0
            return
        
        if isinstance(dst, bytearray):
            set_size = min(size, len(dst))
            for i in range(set_size):
                dst[i] = value & 0xFF
        vm.registers[0] = 1
    
    def _sys_str_len(self, vm: IChingVM):
        str_mem_id = vm.registers[1]
        s = self._get_mem(str_mem_id)
        if s is None:
            vm.registers[0] = 0
            return
        vm.registers[0] = len(s) if isinstance(s, str) else 0
    
    def _sys_str_concat(self, vm: IChingVM):
        str1_mem_id = vm.registers[1]
        str2_mem_id = vm.registers[2]
        s1 = self._get_mem(str1_mem_id)
        s2 = self._get_mem(str2_mem_id)
        if s1 is None or s2 is None:
            vm.registers[0] = 0
            return
        
        result = str(s1) + str(s2)
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_str_substr(self, vm: IChingVM):
        str_mem_id = vm.registers[1]
        start = vm.registers[2]
        length = vm.registers[3]
        s = self._get_mem(str_mem_id)
        if s is None or not isinstance(s, str):
            vm.registers[0] = 0
            return
        
        if length > 0:
            result = s[start:start + length]
        else:
            result = s[start:]
        result_mem_id = self._alloc_mem(result)
        vm.registers[0] = result_mem_id
    
    def _sys_str_find(self, vm: IChingVM):
        str_mem_id = vm.registers[1]
        substr_mem_id = vm.registers[2]
        s = self._get_mem(str_mem_id)
        substr = self._get_mem(substr_mem_id)
        if s is None or substr is None:
            vm.registers[0] = 0xFFFFFFFF
            return
        
        try:
            idx = str(s).find(str(substr))
            vm.registers[0] = idx if idx >= 0 else 0xFFFFFFFF
        except:
            vm.registers[0] = 0xFFFFFFFF
    
    def _sys_str_cmp(self, vm: IChingVM):
        str1_mem_id = vm.registers[1]
        str2_mem_id = vm.registers[2]
        s1 = self._get_mem(str1_mem_id)
        s2 = self._get_mem(str2_mem_id)
        if s1 is None or s2 is None:
            vm.registers[0] = -1
            return
        
        s1_str, s2_str = str(s1), str(s2)
        if s1_str == s2_str:
            vm.registers[0] = 0
        elif s1_str < s2_str:
            vm.registers[0] = -1
        else:
            vm.registers[0] = 1
    
    def _sys_str_parse_int(self, vm: IChingVM):
        str_mem_id = vm.registers[1]
        base = vm.registers[2]
        s = self._get_mem(str_mem_id)
        if s is None:
            vm.registers[0] = 0
            return
        
        try:
            if base > 0:
                result = int(str(s), base)
            else:
                result = int(str(s))
            vm.registers[0] = result & 0xFFFFFFFF
        except:
            vm.registers[0] = 0
    
    def _sys_str_int_to_str(self, vm: IChingVM):
        value = vm.registers[1]
        base = vm.registers[2]
        try:
            if base == 16:
                result = hex(value)
            elif base == 2:
                result = bin(value)
            else:
                result = str(value)
            result_mem_id = self._alloc_mem(result)
            vm.registers[0] = result_mem_id
        except:
            vm.registers[0] = 0
    
    def _sys_print(self, vm: IChingVM):
        str_mem_id = vm.registers[1]
        s = self._get_mem(str_mem_id)
        if s is not None:
            print(str(s))
        vm.registers[0] = 1
    
    def _sys_input(self, vm: IChingVM):
        prompt_mem_id = vm.registers[1]
        prompt = self._get_mem(prompt_mem_id) or ""
        try:
            result = input(str(prompt))
            result_mem_id = self._alloc_mem(result)
            vm.registers[0] = result_mem_id
        except:
            vm.registers[0] = 0
    
    def _sys_open_file(self, vm: IChingVM):
        path_mem_id = vm.registers[1]
        mode_mem_id = vm.registers[2]
        path = self._get_mem(path_mem_id)
        mode = self._get_mem(mode_mem_id) or "r"
        if path is None:
            vm.registers[0] = 0
            return
        
        try:
            f = open(str(path), str(mode))
            fd = self._alloc_mem(f)
            vm.registers[0] = fd
        except:
            vm.registers[0] = 0
    
    def _sys_read_file(self, vm: IChingVM):
        fd_mem_id = vm.registers[1]
        size = vm.registers[2]
        f = self._get_mem(fd_mem_id)
        if f is None:
            vm.registers[0] = 0
            return
        
        try:
            if size > 0:
                result = f.read(size)
            else:
                result = f.read()
            result_mem_id = self._alloc_mem(result)
            vm.registers[0] = result_mem_id
        except:
            vm.registers[0] = 0
    
    def _sys_write_file(self, vm: IChingVM):
        fd_mem_id = vm.registers[1]
        data_mem_id = vm.registers[2]
        f = self._get_mem(fd_mem_id)
        data = self._get_mem(data_mem_id)
        if f is None or data is None:
            vm.registers[0] = 0
            return
        
        try:
            f.write(str(data))
            vm.registers[0] = 1
        except:
            vm.registers[0] = 0
    
    def _sys_close_file(self, vm: IChingVM):
        fd_mem_id = vm.registers[1]
        f = self._get_mem(fd_mem_id)
        if f is None:
            vm.registers[0] = 0
            return
        
        try:
            f.close()
            self._free_mem(fd_mem_id)
            vm.registers[0] = 1
        except:
            vm.registers[0] = 0
    
    def _sys_list_new(self, vm: IChingVM):
        lst = []
        lst_mem_id = self._alloc_mem(lst)
        vm.registers[0] = lst_mem_id
    
    def _sys_list_append(self, vm: IChingVM):
        lst_mem_id = vm.registers[1]
        item_mem_id = vm.registers[2]
        lst = self._get_mem(lst_mem_id)
        item = self._get_mem(item_mem_id)
        if lst is None:
            vm.registers[0] = 0
            return
        
        if isinstance(lst, list):
            lst.append(item)
        vm.registers[0] = 1
    
    def _sys_list_get(self, vm: IChingVM):
        lst_mem_id = vm.registers[1]
        index = vm.registers[2]
        lst = self._get_mem(lst_mem_id)
        if lst is None or not isinstance(lst, list):
            vm.registers[0] = 0
            return
        
        try:
            item = lst[index]
            if isinstance(item, int):
                vm.registers[0] = item
            else:
                item_mem_id = self._alloc_mem(item)
                vm.registers[0] = item_mem_id
        except:
            vm.registers[0] = 0
    
    def _sys_list_set(self, vm: IChingVM):
        lst_mem_id = vm.registers[1]
        index = vm.registers[2]
        value_mem_id = vm.registers[3]
        lst = self._get_mem(lst_mem_id)
        value = self._get_mem(value_mem_id)
        if lst is None or not isinstance(lst, list):
            vm.registers[0] = 0
            return
        
        try:
            lst[index] = value
            vm.registers[0] = 1
        except:
            vm.registers[0] = 0
    
    def _sys_list_len(self, vm: IChingVM):
        lst_mem_id = vm.registers[1]
        lst = self._get_mem(lst_mem_id)
        if lst is None or not isinstance(lst, list):
            vm.registers[0] = 0
            return
        vm.registers[0] = len(lst)
    
    def _sys_list_remove(self, vm: IChingVM):
        lst_mem_id = vm.registers[1]
        index = vm.registers[2]
        lst = self._get_mem(lst_mem_id)
        if lst is None or not isinstance(lst, list):
            vm.registers[0] = 0
            return
        
        try:
            del lst[index]
            vm.registers[0] = 1
        except:
            vm.registers[0] = 0
    
    def _sys_list_insert(self, vm: IChingVM):
        lst_mem_id = vm.registers[1]
        index = vm.registers[2]
        value_mem_id = vm.registers[3]
        lst = self._get_mem(lst_mem_id)
        value = self._get_mem(value_mem_id)
        if lst is None or not isinstance(lst, list):
            vm.registers[0] = 0
            return
        
        try:
            lst.insert(index, value)
            vm.registers[0] = 1
        except:
            vm.registers[0] = 0
    
    def _sys_map_new(self, vm: IChingVM):
        mapping = {}
        map_mem_id = self._alloc_mem(mapping)
        vm.registers[0] = map_mem_id
    
    def _sys_map_put(self, vm: IChingVM):
        map_mem_id = vm.registers[1]
        key_mem_id = vm.registers[2]
        value_mem_id = vm.registers[3]
        mapping = self._get_mem(map_mem_id)
        key = self._get_mem(key_mem_id)
        value = self._get_mem(value_mem_id)
        if mapping is None or not isinstance(mapping, dict):
            vm.registers[0] = 0
            return
        
        mapping[key] = value
        vm.registers[0] = 1
    
    def _sys_map_get(self, vm: IChingVM):
        map_mem_id = vm.registers[1]
        key_mem_id = vm.registers[2]
        mapping = self._get_mem(map_mem_id)
        key = self._get_mem(key_mem_id)
        if mapping is None or not isinstance(mapping, dict):
            vm.registers[0] = 0
            return
        
        value = mapping.get(key)
        if value is None:
            vm.registers[0] = 0
        elif isinstance(value, int):
            vm.registers[0] = value
        else:
            value_mem_id = self._alloc_mem(value)
            vm.registers[0] = value_mem_id
    
    def _sys_map_contains(self, vm: IChingVM):
        map_mem_id = vm.registers[1]
        key_mem_id = vm.registers[2]
        mapping = self._get_mem(map_mem_id)
        key = self._get_mem(key_mem_id)
        if mapping is None or not isinstance(mapping, dict):
            vm.registers[0] = 0
            return
        
        vm.registers[0] = 1 if key in mapping else 0
    
    def _sys_map_remove(self, vm: IChingVM):
        map_mem_id = vm.registers[1]
        key_mem_id = vm.registers[2]
        mapping = self._get_mem(map_mem_id)
        key = self._get_mem(key_mem_id)
        if mapping is None or not isinstance(mapping, dict):
            vm.registers[0] = 0
            return
        
        try:
            del mapping[key]
            vm.registers[0] = 1
        except:
            vm.registers[0] = 0
    
    def _sys_map_keys(self, vm: IChingVM):
        map_mem_id = vm.registers[1]
        mapping = self._get_mem(map_mem_id)
        if mapping is None or not isinstance(mapping, dict):
            vm.registers[0] = 0
            return
        
        keys = list(mapping.keys())
        keys_mem_id = self._alloc_mem(keys)
        vm.registers[0] = keys_mem_id
    
    def _sys_map_values(self, vm: IChingVM):
        map_mem_id = vm.registers[1]
        mapping = self._get_mem(map_mem_id)
        if mapping is None or not isinstance(mapping, dict):
            vm.registers[0] = 0
            return
        
        values = list(mapping.values())
        values_mem_id = self._alloc_mem(values)
        vm.registers[0] = values_mem_id
    
    def _sys_get_input_source(self, vm: IChingVM):
        if self.input_source:
            source_mem_id = self._alloc_mem(self.input_source)
            vm.registers[0] = source_mem_id
        else:
            vm.registers[0] = 0
    
    def _sys_set_output_result(self, vm: IChingVM):
        result_mem_id = vm.registers[1]
        result = self._get_mem(result_mem_id)
        self.output_result = result
        vm.registers[0] = 1
    
    def _sys_get_arg_count(self, vm: IChingVM):
        vm.registers[0] = len(self.args)
    
    def _sys_get_arg(self, vm: IChingVM):
        index = vm.registers[1]
        if 0 <= index < len(self.args):
            arg_mem_id = self._alloc_mem(self.args[index])
            vm.registers[0] = arg_mem_id
        else:
            vm.registers[0] = 0
    
    def _sys_exit(self, vm: IChingVM):
        exit_code = vm.registers[1]
        vm.state = VMState.HALTED
        vm.registers[0] = exit_code
    
    def execute_syscall(self, vm: IChingVM, syscall_num: int):
        handler = self.syscall_handlers.get(syscall_num)
        if handler:
            handler(vm)
        else:
            vm.registers[0] = 0
    
    def load_evo_file(self, evo_path: str) -> Dict:
        from evomorph.compiler.lexer import Lexer
        from evomorph.compiler.parser import Parser
        from evomorph.compiler.codegen import CodeGenerator
        
        with open(evo_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        
        parser = Parser(tokens)
        ast = parser.parse()
        
        codegen = CodeGenerator()
        result = codegen.generate(ast)
        
        return result
    
    def compile_and_execute(self, evo_source: str, args: List[str] = None) -> Any:
        self.args = args or []
        self.input_source = evo_source
        self.output_result = None
        
        from evomorph.compiler.lexer import Lexer
        from evomorph.compiler.parser import Parser
        from evomorph.compiler.codegen import CodeGenerator
        
        lexer = Lexer(evo_source)
        tokens = lexer.tokenize()
        
        parser = Parser(tokens)
        ast = parser.parse()
        
        codegen = CodeGenerator()
        result = codegen.generate(ast)
        
        instructions = []
        for locus in result.get('loci', []):
            for instr in locus.get('instructions', []):
                instructions.append({
                    'opcode': instr.get('opcode', 0),
                    'modifier': 0,
                    'operands': instr.get('operands', [])
                })
        
        self.vm = IChingVM()
        self.vm.load_program(instructions)
        
        self._setup_syscall_ports()
        
        self.vm.run(max_cycles=10000)
        
        return self.output_result
    
    def _setup_syscall_ports(self):
        SYSCALL_PORT = 0xFF
        
        def syscall_handler():
            syscall_num = self.vm.registers[0]
            self.execute_syscall(self.vm, syscall_num)
            return self.vm.registers[0]
        
        self.vm.register_io_handler(SYSCALL_PORT, syscall_handler)


def compile_file(evo_path: str, output_path: str = None) -> Dict:
    executor = EvoBootstrapExecutor()
    
    with open(evo_path, 'r', encoding='utf-8') as f:
        source = f.read()
    
    result = executor.runtime.full_compile(source)
    
    if output_path:
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    
    return result


def run_evo_compiler(input_file: str, output_file: str = None) -> Dict:
    print(f"易衍自举编译器 v3.0")
    print(f"正在编译: {input_file}")
    print("-" * 50)
    
    result = compile_file(input_file, output_file)
    
    print(f"\n编译完成:")
    print(f"  - 版本: {result.get('version')}")
    print(f"  - 基因座数量: {len(result.get('loci', []))}")
    print(f"  - 象辞数量: {len(result.get('xiangci', []))}")
    
    if output_file:
        print(f"  - 输出文件: {output_file}")
    
    return result


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='易衍自举编译器')
    parser.add_argument('input', help='输入 .evo 文件')
    parser.add_argument('-o', '--output', help='输出文件')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    parser.add_argument('--compare', action='store_true', help='与Python编译器对比')
    parser.add_argument('--self-test', action='store_true', help='运行自举测试')
    
    args = parser.parse_args()
    
    if args.self_test:
        executor = EvoBootstrapExecutor()
        result = executor.runtime.run_self_compile_test()
        print("自举测试结果:")
        print(f"  - Token数量: {result.get('tokens')}")
        print(f"  - AST有效: {result.get('ast_valid')}")
        print(f"  - 代码生成有效: {result.get('codegen_valid')}")
        return 0 if result.get('ast_valid') and result.get('codegen_valid') else 1
    
    if not os.path.exists(args.input):
        print(f"错误: 文件不存在 - {args.input}")
        return 1
    
    result = run_evo_compiler(args.input, args.output)
    
    if args.compare:
        executor = EvoBootstrapExecutor()
        with open(args.input, 'r', encoding='utf-8') as f:
            source = f.read()
        comparison = executor.runtime.compare_compilers(source)
        print(f"\n编译器对比:")
        print(f"  - 易衍编译器基因座数: {comparison.get('evo_loci_count')}")
        print(f"  - Python编译器基因座数: {comparison.get('python_loci_count')}")
        print(f"  - 基因座匹配: {'✓' if comparison.get('loci_match') else '✗'}")
        print(f"  - 指令匹配: {'✓' if comparison.get('all_instruction_match') else '✗'}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
