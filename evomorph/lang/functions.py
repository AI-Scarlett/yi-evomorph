import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional, Set, Any, Callable


class FunctionVisibility(Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    EXTERNAL = "external"
    INTERNAL = "internal"


class CallingConvention(Enum):
    DEFAULT = "default"
    FASTCALL = "fastcall"
    CDECL = "cdecl"
    OPTIMIZED = "optimized"


@dataclass
class FunctionParameter:
    name: str
    type_hint: Optional[str] = None
    register: Optional[int] = None
    is_output: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type_hint": self.type_hint,
            "register": self.register,
            "is_output": self.is_output,
        }


@dataclass
class FunctionSignature:
    name: str
    parameters: List[FunctionParameter] = field(default_factory=list)
    return_type: Optional[str] = None
    visibility: FunctionVisibility = FunctionVisibility.PUBLIC
    calling_convention: CallingConvention = CallingConvention.DEFAULT
    is_pure: bool = False
    is_leaf: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "parameters": [p.to_dict() for p in self.parameters],
            "return_type": self.return_type,
            "visibility": self.visibility.value,
            "calling_convention": self.calling_convention.value,
            "is_pure": self.is_pure,
            "is_leaf": self.is_leaf,
        }


@dataclass
class CallFrame:
    return_address: int
    frame_pointer: int
    saved_registers: Dict[int, int] = field(default_factory=dict)
    local_variables: Dict[str, Any] = field(default_factory=dict)
    function_name: str = ""
    parameter_values: List[Any] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "return_address": self.return_address,
            "frame_pointer": self.frame_pointer,
            "saved_registers": copy.deepcopy(self.saved_registers),
            "local_variables": copy.deepcopy(self.local_variables),
            "function_name": self.function_name,
            "parameter_values": copy.deepcopy(self.parameter_values),
        }


class FunctionDefinition:
    def __init__(self, signature: FunctionSignature, instructions: List = None):
        self.signature = signature
        self.instructions = instructions or []
        self.labels: Dict[str, int] = {}
        self.start_address: Optional[int] = None
        self.size: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "signature": self.signature.to_dict(),
            "instructions_count": len(self.instructions),
            "labels": copy.deepcopy(self.labels),
            "start_address": self.start_address,
            "size": self.size,
        }


class FunctionRegistry:
    def __init__(self):
        self.functions: Dict[str, FunctionDefinition] = {}
        self.imported_functions: Dict[str, str] = {}
        self.function_addresses: Dict[int, str] = {}
    
    def register(self, func: FunctionDefinition):
        self.functions[func.signature.name] = func
        if func.start_address is not None:
            self.function_addresses[func.start_address] = func.signature.name
    
    def get(self, name: str) -> Optional[FunctionDefinition]:
        return self.functions.get(name)
    
    def get_by_address(self, address: int) -> Optional[FunctionDefinition]:
        if address in self.function_addresses:
            return self.functions.get(self.function_addresses[address])
        
        func_by_addrs = {f.start_address: name for name, f in self.functions.items() 
                          if f.start_address is not None}
        
        sorted_addrs = sorted(func_by_addrs.keys())
        for i in range(len(sorted_addrs) - 1):
            if sorted_addrs[i] <= address < sorted_addrs[i + 1]:
                return self.functions.get(func_by_addrs[sorted_addrs[i]])
        
        if sorted_addrs and address >= sorted_addrs[-1]:
            return self.functions.get(func_by_addrs[sorted_addrs[-1]])
        
        return None
    
    def list_functions(self) -> List[str]:
        return list(self.functions.keys())
    
    def import_function(self, name: str, external_name: str):
        self.imported_functions[name] = external_name
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "functions": {name: f.to_dict() for name, f in self.functions.items()},
            "imported_functions": copy.deepcopy(self.imported_functions),
        }


class CallStack:
    def __init__(self, max_depth: int = 256):
        self.frames: List[CallFrame] = []
        self.max_depth = max_depth
    
    def push(self, frame: CallFrame) -> bool:
        if len(self.frames) >= self.max_depth:
            return False
        self.frames.append(frame)
        return True
    
    def pop(self) -> Optional[CallFrame]:
        if not self.frames:
            return None
        return self.frames.pop()
    
    def top(self) -> Optional[CallFrame]:
        if not self.frames:
            return None
        return self.frames[-1]
    
    def depth(self) -> int:
        return len(self.frames)
    
    def is_empty(self) -> bool:
        return len(self.frames) == 0
    
    def clear(self):
        self.frames.clear()
    
    def to_list(self) -> List[Dict[str, Any]]:
        return [f.to_dict() for f in self.frames]


class FunctionCallABI:
    def __init__(self):
        self.parameter_registers = [0, 1, 2, 3, 4, 5]
        self.return_register = 0
        self.preserved_registers = [6, 7, 8, 9]
        self.caller_saved_registers = [0, 1, 2, 3, 4, 5, 10, 11]
        self.frame_pointer_reg = 12
        self.stack_pointer_reg = 13
        self.link_register = 14
        self.arg_pointer_reg = 15
    
    def get_parameter_register(self, index: int) -> Optional[int]:
        if index < len(self.parameter_registers):
            return self.parameter_registers[index]
        return None
    
    def needs_stack_parameter(self, index: int) -> bool:
        return index >= len(self.parameter_registers)
    
    def get_preserved_registers(self) -> List[int]:
        return list(self.preserved_registers)
    
    def get_caller_saved_registers(self) -> List[int]:
        return list(self.caller_saved_registers)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter_registers": self.parameter_registers,
            "return_register": self.return_register,
            "preserved_registers": self.preserved_registers,
            "caller_saved_registers": self.caller_saved_registers,
            "frame_pointer_reg": self.frame_pointer_reg,
            "stack_pointer_reg": self.stack_pointer_reg,
            "link_register": self.link_register,
            "arg_pointer_reg": self.arg_pointer_reg,
        }


class FunctionCallGenerator:
    def __init__(self, abi: Optional[FunctionCallABI] = None):
        self.abi = abi or FunctionCallABI()
    
    def generate_call_sequence(self, 
                                 func_name: str, 
                                 arguments: List[Tuple[int, Any]],
                                 function_def: Optional[FunctionDefinition] = None) -> List[Dict]:
        instructions = []
        
        for i, (arg_type, arg_value) in enumerate(arguments):
            reg = self.abi.get_parameter_register(i)
            if reg is not None:
                instructions.append({
                    "opcode": 59,
                    "mnemonic": "YIELD",
                    "symbol": "䷊",
                    "modifier": 0,
                    "operands": [reg, arg_value if isinstance(arg_value, int) else 0],
                    "comment": f"参数 {i} -> R{reg}"
                })
            else:
                stack_offset = (i - len(self.abi.parameter_registers)) * 4
                instructions.append({
                    "opcode": 47,
                    "mnemonic": "ABUNDANCE",
                    "symbol": "䷍",
                    "modifier": 0,
                    "operands": [self.abi.stack_pointer_reg, stack_offset],
                    "comment": f"参数 {i} 入栈"
                })
        
        for reg in self.abi.get_caller_saved_registers():
            instructions.append({
                "opcode": 47,
                "mnemonic": "ABUNDANCE",
                "symbol": "䷍",
                "modifier": 0,
                "operands": [self.abi.stack_pointer_reg, 0],
                "comment": f"保存 R{reg}"
            })
        
        instructions.append({
            "opcode": 63,
            "mnemonic": "CREA",
            "symbol": "䷀",
            "modifier": 0,
            "operands": [self.abi.link_register, 0],
            "comment": f"调用 {func_name}"
        })
        
        for reg in reversed(self.abi.get_caller_saved_registers()):
            instructions.append({
                "opcode": 0,
                "mnemonic": "RECV",
                "symbol": "䷁",
                "modifier": 0,
                "operands": [reg, self.abi.stack_pointer_reg],
                "comment": f"恢复 R{reg}"
            })
        
        return instructions
    
    def generate_prologue(self, func_def: FunctionDefinition) -> List[Dict]:
        instructions = []
        
        instructions.append({
            "opcode": 47,
            "mnemonic": "ABUNDANCE",
            "symbol": "䷍",
            "modifier": 0,
            "operands": [self.abi.frame_pointer_reg, 0],
            "comment": "保存帧指针"
        })
        
        instructions.append({
            "opcode": 59,
            "mnemonic": "YIELD",
            "symbol": "䷊",
            "modifier": 0,
            "operands": [self.abi.frame_pointer_reg, self.abi.stack_pointer_reg],
            "comment": "设置新帧指针"
        })
        
        local_size = len(func_def.signature.parameters) * 4 + 32
        if local_size > 0:
            instructions.append({
                "opcode": 17,
                "mnemonic": "ALLOC",
                "symbol": "䷂",
                "modifier": 0,
                "operands": [self.abi.stack_pointer_reg, local_size],
                "comment": "分配局部变量空间"
            })
        
        for reg in self.abi.get_preserved_registers():
            instructions.append({
                "opcode": 47,
                "mnemonic": "ABUNDANCE",
                "symbol": "䷍",
                "modifier": 0,
                "operands": [reg, 0],
                "comment": f"保存被调用者寄存器 R{reg}"
            })
        
        return instructions
    
    def generate_epilogue(self, func_def: FunctionDefinition) -> List[Dict]:
        instructions = []
        
        for reg in reversed(self.abi.get_preserved_registers()):
            instructions.append({
                "opcode": 0,
                "mnemonic": "RECV",
                "symbol": "䷁",
                "modifier": 0,
                "operands": [reg, 0],
                "comment": f"恢复被调用者寄存器 R{reg}"
            })
        
        instructions.append({
            "opcode": 59,
            "mnemonic": "YIELD",
            "symbol": "䷊",
            "modifier": 0,
            "operands": [self.abi.stack_pointer_reg, self.abi.frame_pointer_reg],
            "comment": "恢复栈指针"
        })
        
        instructions.append({
            "opcode": 0,
            "mnemonic": "RECV",
            "symbol": "䷁",
            "modifier": 0,
            "operands": [self.abi.frame_pointer_reg, 0],
            "comment": "恢复帧指针"
        })
        
        instructions.append({
            "opcode": 1,
            "mnemonic": "RETURN",
            "symbol": "䷗",
            "modifier": 0,
            "operands": [self.abi.link_register],
            "comment": "返回"
        })
        
        return instructions
    
    def generate_leaf_function_prologue(self, func_def: FunctionDefinition) -> List[Dict]:
        return []
    
    def generate_leaf_function_epilogue(self, func_def: FunctionDefinition) -> List[Dict]:
        return [{
            "opcode": 1,
            "mnemonic": "RETURN",
            "symbol": "䷗",
            "modifier": 0,
            "operands": [self.abi.link_register],
            "comment": "返回（叶子函数）"
        }]


class InlineExpander:
    def __init__(self):
        self.max_inline_size = 50
        self.max_inline_depth = 3
        self.inline_threshold = 0.7
    
    def should_inline(self, 
                       caller: FunctionDefinition, 
                       callee: FunctionDefinition,
                       call_count: int = 1) -> bool:
        if callee.signature.is_leaf and len(callee.instructions) < 10:
            return True
        
        if call_count > 1 and len(callee.instructions) < 20:
            return True
        
        if callee.signature.is_pure and len(callee.instructions) < self.max_inline_size:
            return True
        
        if len(callee.instructions) < 5:
            return True
        
        return False
    
    def expand_inline(self, 
                       caller: FunctionDefinition, 
                       callee: FunctionDefinition,
                       call_site_index: int,
                       arguments: List[Tuple[int, Any]]) -> Optional[List[Dict]]:
        if not self.should_inline(caller, callee):
            return None
        
        expanded = []
        
        for i, (arg_type, arg_value) in enumerate(arguments):
            expanded.append({
                "opcode": 59,
                "mnemonic": "YIELD",
                "symbol": "䷊",
                "modifier": 0,
                "operands": [i, arg_value if isinstance(arg_value, int) else 0],
                "comment": f"内联参数 {i}"
            })
        
        for instr in callee.instructions:
            if isinstance(instr, dict):
                cloned = copy.deepcopy(instr)
                if "comment" in cloned:
                    cloned["comment"] = f"[内联] {cloned.get('comment', '')}"
                expanded.append(cloned)
        
        return expanded
