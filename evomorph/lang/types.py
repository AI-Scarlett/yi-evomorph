import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional, Set, Any, Union, Callable
from collections import defaultdict


class TypeKind(Enum):
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    STRING = "string"
    POINTER = "pointer"
    ARRAY = "array"
    STRUCT = "struct"
    FUNCTION = "function"
    TUPLE = "tuple"
    UNION = "union"
    BOTTOM = "bottom"
    TOP = "top"
    TYPE_VAR = "type_var"


class TypeCategory(Enum):
    YUAN = "元"
    HENG = "亨"
    LI = "利"
    ZHEN = "贞"


@dataclass(frozen=True)
class TrigramType:
    name: str
    binary: Tuple[bool, bool, bool]
    semantic: str
    category: TypeCategory
    
    def to_int(self) -> int:
        return (int(self.binary[0]) << 2) | (int(self.binary[1]) << 1) | int(self.binary[2])


@dataclass
class EvomorphType:
    kind: TypeKind
    size: int = 0
    alignment: int = 1
    category: Optional[TypeCategory] = None
    trigram: Optional[TrigramType] = None
    type_params: List['EvomorphType'] = field(default_factory=list)
    fields: Dict[str, 'EvomorphType'] = field(default_factory=dict)
    return_type: Optional['EvomorphType'] = None
    param_types: List['EvomorphType'] = field(default_factory=list)
    is_mutable: bool = True
    is_volatile: bool = False
    is_atomic: bool = False
    type_var_id: Optional[str] = None
    array_length: Optional[int] = None
    
    def clone(self) -> 'EvomorphType':
        return copy.deepcopy(self)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "kind": self.kind.value,
            "size": self.size,
            "alignment": self.alignment,
            "is_mutable": self.is_mutable,
            "is_volatile": self.is_volatile,
            "is_atomic": self.is_atomic,
        }
        
        if self.category:
            result["category"] = self.category.value
        if self.trigram:
            result["trigram"] = {
                "name": self.trigram.name,
                "binary": self.trigram.binary,
                "semantic": self.trigram.semantic,
                "category": self.trigram.category.value,
            }
        if self.type_params:
            result["type_params"] = [t.to_dict() for t in self.type_params]
        if self.fields:
            result["fields"] = {k: v.to_dict() for k, v in self.fields.items()}
        if self.return_type:
            result["return_type"] = self.return_type.to_dict()
        if self.param_types:
            result["param_types"] = [t.to_dict() for t in self.param_types]
        if self.array_length is not None:
            result["array_length"] = self.array_length
        if self.type_var_id:
            result["type_var_id"] = self.type_var_id
        
        return result
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, EvomorphType):
            return False
        
        if self.kind != other.kind:
            return False
        
        if self.size != other.size or self.alignment != other.alignment:
            return False
        
        if self.category != other.category:
            return False
        
        if self.kind == TypeKind.POINTER:
            if len(self.type_params) != len(other.type_params):
                return False
            for t1, t2 in zip(self.type_params, other.type_params):
                if t1 != t2:
                    return False
        
        if self.kind == TypeKind.ARRAY:
            if self.array_length != other.array_length:
                return False
            if self.type_params and other.type_params:
                if self.type_params[0] != other.type_params[0]:
                    return False
        
        if self.kind == TypeKind.STRUCT:
            if self.fields.keys() != other.fields.keys():
                return False
            for name in self.fields:
                if self.fields[name] != other.fields[name]:
                    return False
        
        if self.kind == TypeKind.FUNCTION:
            if self.return_type != other.return_type:
                return False
            if len(self.param_types) != len(other.param_types):
                return False
            for t1, t2 in zip(self.param_types, other.param_types):
                if t1 != t2:
                    return False
        
        return True
    
    def __hash__(self) -> int:
        return hash((
            self.kind, self.size, self.alignment, self.category,
            self.array_length, self.type_var_id
        ))


class TrigramTypeSystem:
    TRIGRAMS = {
        "䷀": TrigramType(
            name="乾", binary=(True, True, True), 
            semantic="天·创生·领导者", category=TypeCategory.YUAN
        ),
        "䷁": TrigramType(
            name="坤", binary=(False, False, False), 
            semantic="地·承载·接收者", category=TypeCategory.ZHEN
        ),
        "䷂": TrigramType(
            name="屯", binary=(False, False, True), 
            semantic="难·初始·积累", category=TypeCategory.YUAN
        ),
        "䷃": TrigramType(
            name="蒙", binary=(False, True, False), 
            semantic="蒙·启蒙·学习", category=TypeCategory.HENG
        ),
        "䷄": TrigramType(
            name="需", binary=(False, True, True), 
            semantic="需·等待·准备", category=TypeCategory.YUAN
        ),
        "䷅": TrigramType(
            name="讼", binary=(True, False, False), 
            semantic="讼·争论·裁决", category=TypeCategory.LI
        ),
        "䷆": TrigramType(
            name="师", binary=(True, False, True), 
            semantic="师·群体·组织", category=TypeCategory.YUAN
        ),
        "䷇": TrigramType(
            name="比", binary=(True, True, False), 
            semantic="比·比较·和谐", category=TypeCategory.HENG
        ),
    }
    
    @classmethod
    def get_trigram(cls, symbol: str) -> Optional[TrigramType]:
        return cls.TRIGRAMS.get(symbol)
    
    @classmethod
    def get_trigram_by_int(cls, value: int) -> Optional[TrigramType]:
        for trigram in cls.TRIGRAMS.values():
            if trigram.to_int() == value:
                return trigram
        return None
    
    @classmethod
    def infer_type_category(cls, opcode: int) -> TypeCategory:
        from evomorph.hexagrams.instruction_set import HEXAGRAM_CATEGORIES
        
        for cat_name, category_map in [
            (TypeCategory.YUAN, HEXAGRAM_CATEGORIES.get("元", [])),
            (TypeCategory.HENG, HEXAGRAM_CATEGORIES.get("亨", [])),
            (TypeCategory.LI, HEXAGRAM_CATEGORIES.get("利", [])),
            (TypeCategory.ZHEN, HEXAGRAM_CATEGORIES.get("贞", [])),
        ]:
            if opcode in category_map:
                return cat_name
        
        return TypeCategory.LI


class PrimitiveTypes:
    INT8 = EvomorphType(kind=TypeKind.INTEGER, size=1, alignment=1, category=TypeCategory.LI)
    INT16 = EvomorphType(kind=TypeKind.INTEGER, size=2, alignment=2, category=TypeCategory.LI)
    INT32 = EvomorphType(kind=TypeKind.INTEGER, size=4, alignment=4, category=TypeCategory.LI)
    INT64 = EvomorphType(kind=TypeKind.INTEGER, size=8, alignment=8, category=TypeCategory.LI)
    UINT8 = EvomorphType(kind=TypeKind.INTEGER, size=1, alignment=1, category=TypeCategory.LI)
    UINT16 = EvomorphType(kind=TypeKind.INTEGER, size=2, alignment=2, category=TypeCategory.LI)
    UINT32 = EvomorphType(kind=TypeKind.INTEGER, size=4, alignment=4, category=TypeCategory.LI)
    UINT64 = EvomorphType(kind=TypeKind.INTEGER, size=8, alignment=8, category=TypeCategory.LI)
    
    FLOAT32 = EvomorphType(kind=TypeKind.FLOAT, size=4, alignment=4, category=TypeCategory.LI)
    FLOAT64 = EvomorphType(kind=TypeKind.FLOAT, size=8, alignment=8, category=TypeCategory.LI)
    
    BOOLEAN = EvomorphType(kind=TypeKind.BOOLEAN, size=1, alignment=1, category=TypeCategory.LI)
    
    VOID = EvomorphType(kind=TypeKind.BOTTOM, size=0, alignment=1, category=TypeCategory.LI)
    
    @classmethod
    def get_pointer(cls, pointee: EvomorphType) -> EvomorphType:
        return EvomorphType(
            kind=TypeKind.POINTER,
            size=8,
            alignment=8,
            category=TypeCategory.YUAN,
            type_params=[pointee]
        )
    
    @classmethod
    def get_array(cls, element: EvomorphType, length: int) -> EvomorphType:
        return EvomorphType(
            kind=TypeKind.ARRAY,
            size=element.size * length,
            alignment=element.alignment,
            category=TypeCategory.LI,
            type_params=[element],
            array_length=length
        )
    
    @classmethod
    def get_function(cls, return_type: EvomorphType, param_types: List[EvomorphType]) -> EvomorphType:
        return EvomorphType(
            kind=TypeKind.FUNCTION,
            size=8,
            alignment=8,
            category=TypeCategory.YUAN,
            return_type=return_type,
            param_types=param_types
        )


class TypeInferenceEngine:
    def __init__(self):
        self.type_variables: Dict[str, EvomorphType] = {}
        self.constraints: List[Tuple[EvomorphType, EvomorphType, str]] = []
        self.unification_map: Dict[int, EvomorphType] = {}
        self.next_type_var_id = 0
    
    def fresh_type_var(self, hint: str = "") -> EvomorphType:
        var_id = f"T{self.next_type_var_id}"
        if hint:
            var_id = f"{hint}_{var_id}"
        self.next_type_var_id += 1
        return EvomorphType(kind=TypeKind.TYPE_VAR, type_var_id=var_id)
    
    def add_constraint(self, t1: EvomorphType, t2: EvomorphType, reason: str = ""):
        self.constraints.append((t1, t2, reason))
    
    def unify(self, t1: EvomorphType, t2: EvomorphType) -> Optional[EvomorphType]:
        if t1.kind == TypeKind.TYPE_VAR:
            if self.occurs_check(t1, t2):
                return None
            self.unification_map[id(t1)] = t2
            return t2
        
        if t2.kind == TypeKind.TYPE_VAR:
            if self.occurs_check(t2, t1):
                return None
            self.unification_map[id(t2)] = t1
            return t1
        
        if t1 == t2:
            return t1
        
        if t1.kind == TypeKind.INTEGER and t2.kind == TypeKind.INTEGER:
            if t1.size <= t2.size:
                return t2
            else:
                return t1
        
        if t1.kind == TypeKind.POINTER and t2.kind == TypeKind.POINTER:
            if t1.type_params and t2.type_params:
                unified = self.unify(t1.type_params[0], t2.type_params[0])
                if unified:
                    return PrimitiveTypes.get_pointer(unified)
        
        if t1.kind == TypeKind.ARRAY and t2.kind == TypeKind.ARRAY:
            if t1.array_length == t2.array_length and t1.type_params and t2.type_params:
                unified = self.unify(t1.type_params[0], t2.type_params[0])
                if unified:
                    return PrimitiveTypes.get_array(unified, t1.array_length or 0)
        
        if t1.kind == TypeKind.FUNCTION and t2.kind == TypeKind.FUNCTION:
            if t1.return_type and t2.return_type:
                unified_return = self.unify(t1.return_type, t2.return_type)
                if not unified_return:
                    return None
                
                if len(t1.param_types) == len(t2.param_types):
                    unified_params = []
                    for p1, p2 in zip(t1.param_types, t2.param_types):
                        unified = self.unify(p1, p2)
                        if not unified:
                            return None
                        unified_params.append(unified)
                    
                    return PrimitiveTypes.get_function(unified_return, unified_params)
        
        return None
    
    def occurs_check(self, var: EvomorphType, t: EvomorphType) -> bool:
        if var == t:
            return True
        
        if t.kind == TypeKind.POINTER:
            for param in t.type_params:
                if self.occurs_check(var, param):
                    return True
        
        if t.kind == TypeKind.ARRAY:
            for param in t.type_params:
                if self.occurs_check(var, param):
                    return True
        
        if t.kind == TypeKind.FUNCTION:
            if t.return_type and self.occurs_check(var, t.return_type):
                return True
            for param in t.param_types:
                if self.occurs_check(var, param):
                    return True
        
        if t.kind == TypeKind.STRUCT:
            for field_type in t.fields.values():
                if self.occurs_check(var, field_type):
                    return True
        
        return False
    
    def infer_expression_type(self, expression: Any, context: Dict[str, EvomorphType]) -> Optional[EvomorphType]:
        raise NotImplementedError("Subclasses should implement expression type inference")
    
    def resolve_all(self) -> Dict[str, EvomorphType]:
        resolved = {}
        
        for var_id, typ in self.type_variables.items():
            resolved[var_id] = self.apply_substitution(typ)
        
        return resolved
    
    def apply_substitution(self, typ: EvomorphType) -> EvomorphType:
        if typ.kind == TypeKind.TYPE_VAR:
            if id(typ) in self.unification_map:
                return self.apply_substitution(self.unification_map[id(typ)])
            return typ
        
        result = typ.clone()
        
        if result.type_params:
            result.type_params = [self.apply_substitution(t) for t in result.type_params]
        
        if result.kind == TypeKind.FUNCTION:
            if result.return_type:
                result.return_type = self.apply_substitution(result.return_type)
            result.param_types = [self.apply_substitution(t) for t in result.param_types]
        
        if result.kind == TypeKind.STRUCT:
            result.fields = {k: self.apply_substitution(v) for k, v in result.fields.items()}
        
        return result


class TypeChecker:
    def __init__(self):
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.inference_engine = TypeInferenceEngine()
    
    def reset(self):
        self.errors.clear()
        self.warnings.clear()
        self.inference_engine = TypeInferenceEngine()
    
    def add_error(self, message: str, location: Optional[Dict[str, Any]] = None, code: str = "E0001"):
        error = {
            "code": code,
            "message": message,
            "location": location or {},
            "level": "error"
        }
        self.errors.append(error)
    
    def add_warning(self, message: str, location: Optional[Dict[str, Any]] = None, code: str = "W0001"):
        warning = {
            "code": code,
            "message": message,
            "location": location or {},
            "level": "warning"
        }
        self.warnings.append(warning)
    
    def check_type_compatibility(self, 
                                    expected: EvomorphType, 
                                    actual: EvomorphType,
                                    location: Optional[Dict[str, Any]] = None) -> bool:
        if expected == actual:
            return True
        
        if expected.kind == TypeKind.INTEGER and actual.kind == TypeKind.INTEGER:
            if actual.size <= expected.size:
                self.add_warning(
                    f"隐式类型转换: {actual.size*8}位整数 到 {expected.size*8}位整数",
                    location,
                    "W0002"
                )
                return True
        
        if expected.kind == TypeKind.POINTER and actual.kind == TypeKind.POINTER:
            if not expected.type_params and not actual.type_params:
                return True
            
            if expected.type_params and actual.type_params:
                if expected.type_params[0].kind == TypeKind.BOTTOM:
                    return True
        
        self.add_error(
            f"类型不匹配: 期望 {expected.kind.value}, 实际 {actual.kind.value}",
            location,
            "E0002"
        )
        return False
    
    def check_operand_types(self, 
                              opcode: int,
                              operands: List[Tuple[EvomorphType, Dict[str, Any]]]) -> bool:
        from evomorph.hexagrams.instruction_set import HEXAGRAM_CATEGORIES
        
        category = TrigramTypeSystem.infer_type_category(opcode)
        
        if category == TypeCategory.YUAN:
            if len(operands) >= 1:
                dest_type, _ = operands[0]
                if dest_type.kind not in (TypeKind.INTEGER, TypeKind.POINTER):
                    self.add_error(
                        f"源指令需要整数或指针类型作为目标, 得到 {dest_type.kind.value}",
                        None,
                        "E0003"
                    )
                    return False
        
        elif category == TypeCategory.LI:
            if len(operands) >= 2:
                t1, _ = operands[0]
                t2, _ = operands[1]
                
                if t1.kind != t2.kind:
                    self.add_error(
                        f"转换指令操作数类型不匹配: {t1.kind.value} vs {t2.kind.value}",
                        None,
                        "E0004"
                    )
                    return False
        
        elif category == TypeCategory.HENG:
            pass
        
        elif category == TypeCategory.ZHEN:
            pass
        
        return True
    
    def get_diagnostics(self) -> Dict[str, Any]:
        return {
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "has_errors": len(self.errors) > 0,
        }


class TypeEnvironment:
    def __init__(self, parent: Optional['TypeEnvironment'] = None):
        self.parent = parent
        self.bindings: Dict[str, EvomorphType] = {}
        self.struct_definitions: Dict[str, EvomorphType] = {}
    
    def lookup(self, name: str) -> Optional[EvomorphType]:
        if name in self.bindings:
            return self.bindings[name]
        if self.parent:
            return self.parent.lookup(name)
        return None
    
    def bind(self, name: str, typ: EvomorphType):
        self.bindings[name] = typ
    
    def define_struct(self, name: str, struct_type: EvomorphType):
        self.struct_definitions[name] = struct_type
    
    def lookup_struct(self, name: str) -> Optional[EvomorphType]:
        if name in self.struct_definitions:
            return self.struct_definitions[name]
        if self.parent:
            return self.parent.lookup_struct(name)
        return None
    
    def get_all_bindings(self) -> Dict[str, EvomorphType]:
        result = {}
        if self.parent:
            result.update(self.parent.get_all_bindings())
        result.update(self.bindings)
        return result
