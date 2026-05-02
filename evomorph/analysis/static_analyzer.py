import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional, Set, Any, Callable, Union
from collections import defaultdict, deque


class AnalysisType(Enum):
    CONTROL_FLOW = "control_flow"
    DATA_FLOW = "data_flow"
    DEPENDENCE = "dependence"
    MEMORY = "memory"
    CONCURRENCY = "concurrency"
    TYPE = "type"
    UNINITIALIZED = "uninitialized"
    DEAD_CODE = "dead_code"
    LOOP = "loop"


@dataclass
class CFGNode:
    node_id: int
    block_name: str = ""
    instructions: List[Dict] = field(default_factory=list)
    predecessors: Set[int] = field(default_factory=set)
    successors: Set[int] = field(default_factory=set)
    is_entry: bool = False
    is_exit: bool = False
    is_conditional: bool = False
    is_loop_header: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "block_name": self.block_name,
            "instructions_count": len(self.instructions),
            "predecessors": list(self.predecessors),
            "successors": list(self.successors),
            "is_entry": self.is_entry,
            "is_exit": self.is_exit,
            "is_conditional": self.is_conditional,
            "is_loop_header": self.is_loop_header,
        }


@dataclass
class ControlFlowGraph:
    nodes: Dict[int, CFGNode] = field(default_factory=dict)
    entry_node: Optional[int] = None
    exit_nodes: List[int] = field(default_factory=list)
    edges: Set[Tuple[int, int]] = field(default_factory=set)
    
    def add_node(self, node: CFGNode):
        self.nodes[node.node_id] = node
        if node.is_entry:
            self.entry_node = node.node_id
        if node.is_exit:
            self.exit_nodes.append(node.node_id)
    
    def add_edge(self, from_id: int, to_id: int):
        self.edges.add((from_id, to_id))
        if from_id in self.nodes and to_id in self.nodes:
            self.nodes[from_id].successors.add(to_id)
            self.nodes[to_id].predecessors.add(from_id)
    
    def get_node(self, node_id: int) -> Optional[CFGNode]:
        return self.nodes.get(node_id)
    
    def reachable_nodes(self, start_id: int) -> Set[int]:
        if start_id not in self.nodes:
            return set()
        
        visited = set()
        queue = deque([start_id])
        
        while queue:
            node_id = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)
            
            node = self.nodes.get(node_id)
            if node:
                for succ_id in node.successors:
                    if succ_id not in visited:
                        queue.append(succ_id)
        
        return visited
    
    def unreachable_nodes(self) -> Set[int]:
        if self.entry_node is None:
            return set(self.nodes.keys())
        
        reachable = self.reachable_nodes(self.entry_node)
        all_nodes = set(self.nodes.keys())
        return all_nodes - reachable
    
    def compute_dominators(self) -> Dict[int, Set[int]]:
        dominators: Dict[int, Set[int]] = {}
        
        for node_id in self.nodes:
            if node_id == self.entry_node:
                dominators[node_id] = {node_id}
            else:
                dominators[node_id] = set(self.nodes.keys())
        
        changed = True
        while changed:
            changed = False
            
            for node_id in self.nodes:
                if node_id == self.entry_node:
                    continue
                
                node = self.nodes.get(node_id)
                if not node:
                    continue
                
                if not node.predecessors:
                    continue
                
                new_dom = set(self.nodes.keys())
                for pred_id in node.predecessors:
                    if pred_id in dominators:
                        new_dom &= dominators[pred_id]
                
                new_dom.add(node_id)
                
                if new_dom != dominators[node_id]:
                    dominators[node_id] = new_dom
                    changed = True
        
        return dominators
    
    def compute_post_dominators(self) -> Dict[int, Set[int]]:
        reversed_nodes = copy.deepcopy(self.nodes)
        for node_id, node in reversed_nodes.items():
            node.predecessors, node.successors = node.successors, node.predecessors
            node.is_entry, node.is_exit = node.is_exit, node.is_entry
        
        rev_cfg = ControlFlowGraph()
        rev_cfg.nodes = reversed_nodes
        if self.exit_nodes:
            rev_cfg.entry_node = self.exit_nodes[0]
        
        return rev_cfg.compute_dominators()
    
    def identify_loops(self) -> List[Dict[str, Any]]:
        dominators = self.compute_dominators()
        loops: List[Dict[str, Any]] = []
        
        for node_id, node in self.nodes.items():
            for succ_id in node.successors:
                if succ_id in dominators[node_id]:
                    loop_header = succ_id
                    loop_latch = node_id
                    
                    loop_body = self._compute_loop_body(loop_header, loop_latch)
                    
                    loops.append({
                        "header": loop_header,
                        "latch": loop_latch,
                        "body": list(loop_body),
                        "node_count": len(loop_body) + 2,
                    })
                    
                    if loop_header in self.nodes:
                        self.nodes[loop_header].is_loop_header = True
        
        return loops
    
    def _compute_loop_body(self, header: int, latch: int) -> Set[int]:
        body = set()
        stack = [latch]
        
        while stack:
            node_id = stack.pop()
            if node_id == header or node_id in body:
                continue
            
            body.add(node_id)
            node = self.nodes.get(node_id)
            if node:
                for pred_id in node.predecessors:
                    if pred_id != header:
                        stack.append(pred_id)
        
        return body
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes_count": len(self.nodes),
            "entry_node": self.entry_node,
            "exit_nodes": list(self.exit_nodes),
            "edges_count": len(self.edges),
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
        }


class CFGConstructor:
    def __init__(self):
        self.node_counter = 0
    
    def build_from_instructions(self, instructions: List[Dict]) -> ControlFlowGraph:
        cfg = ControlFlowGraph()
        
        if not instructions:
            return cfg
        
        basic_blocks = self._split_into_basic_blocks(instructions)
        
        nodes: Dict[int, CFGNode] = {}
        for bb in basic_blocks:
            node = CFGNode(
                node_id=self.node_counter,
                block_name=f"BB_{self.node_counter}",
                instructions=bb["instructions"],
                is_entry=bb["is_entry"],
                is_exit=bb["is_exit"],
            )
            nodes[self.node_counter] = node
            self.node_counter += 1
        
        for node_id, node in nodes.items():
            cfg.add_node(node)
        
        for i, bb in enumerate(basic_blocks):
            current_node_id = i
            
            if "successors" in bb:
                for succ_label in bb["successors"]:
                    for j, target_bb in enumerate(basic_blocks):
                        if target_bb.get("label") == succ_label:
                            cfg.add_edge(current_node_id, j)
                            break
            
            if bb.get("falls_through") and i + 1 < len(basic_blocks):
                cfg.add_edge(current_node_id, i + 1)
        
        return cfg
    
    def _split_into_basic_blocks(self, instructions: List[Dict]) -> List[Dict]:
        leaders: Set[int] = {0}
        
        for i, instr in enumerate(instructions):
            if self._is_branch_instruction(instr):
                if i + 1 < len(instructions):
                    leaders.add(i + 1)
                
                targets = self._get_branch_targets(instr)
                for target in targets:
                    if 0 <= target < len(instructions):
                        leaders.add(target)
        
        sorted_leaders = sorted(leaders)
        
        basic_blocks: List[Dict] = []
        
        for i, leader in enumerate(sorted_leaders):
            next_leader = sorted_leaders[i + 1] if i + 1 < len(sorted_leaders) else len(instructions)
            
            bb_instructions = instructions[leader:next_leader]
            
            is_entry = (leader == 0)
            is_exit = False
            falls_through = True
            successors: List[str] = []
            
            if bb_instructions:
                last_instr = bb_instructions[-1]
                if self._is_terminal_instruction(last_instr):
                    is_exit = True
                    falls_through = False
                
                if self._is_branch_instruction(last_instr):
                    successors = self._get_branch_target_labels(last_instr)
                    if not self._is_unconditional_branch(last_instr):
                        falls_through = True
                    else:
                        falls_through = False
            
            basic_blocks.append({
                "start_index": leader,
                "end_index": next_leader - 1,
                "instructions": bb_instructions,
                "is_entry": is_entry,
                "is_exit": is_exit,
                "falls_through": falls_through,
                "successors": successors,
            })
        
        return basic_blocks
    
    def _is_branch_instruction(self, instr: Dict) -> bool:
        opcode = instr.get("opcode", 0)
        branch_opcodes = {2, 1, 56, 31, 36}
        return opcode in branch_opcodes
    
    def _is_unconditional_branch(self, instr: Dict) -> bool:
        opcode = instr.get("opcode", 0)
        return opcode in {1, 56}
    
    def _is_terminal_instruction(self, instr: Dict) -> bool:
        opcode = instr.get("opcode", 0)
        return opcode == 1
    
    def _get_branch_targets(self, instr: Dict) -> List[int]:
        operands = instr.get("operands", [])
        targets = []
        for op in operands:
            if isinstance(op, int):
                targets.append(op)
        return targets
    
    def _get_branch_target_labels(self, instr: Dict) -> List[str]:
        targets = []
        operands = instr.get("operands", [])
        for op in operands:
            if isinstance(op, str):
                targets.append(op)
            elif isinstance(op, int):
                targets.append(f"label_{op}")
        return targets


@dataclass
class LatticeValue:
    value: Any
    is_top: bool = False
    is_bottom: bool = False
    
    @classmethod
    def top(cls) -> 'LatticeValue':
        return LatticeValue(None, is_top=True)
    
    @classmethod
    def bottom(cls) -> 'LatticeValue':
        return LatticeValue(None, is_bottom=True)
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, LatticeValue):
            return False
        if self.is_top and other.is_top:
            return True
        if self.is_bottom and other.is_bottom:
            return True
        return self.value == other.value
    
    def __repr__(self) -> str:
        if self.is_top:
            return "TOP"
        if self.is_bottom:
            return "BOT"
        return str(self.value)


class DataFlowAnalysis:
    def __init__(self, cfg: ControlFlowGraph):
        self.cfg = cfg
        self.IN: Dict[int, Dict] = {}
        self.OUT: Dict[int, Dict] = {}
    
    def run_forward_analysis(self,
                               initial_IN: Dict[int, Dict],
                               transfer: Callable[[int, Dict], Dict],
                               meet: Callable[[List[Dict]], Dict]) -> Tuple[Dict[int, Dict], Dict[int, Dict]]:
        IN = copy.deepcopy(initial_IN)
        OUT: Dict[int, Dict] = {node_id: {} for node_id in self.cfg.nodes}
        
        changed = True
        while changed:
            changed = False
            
            for node_id in self.cfg.nodes:
                node = self.cfg.nodes.get(node_id)
                if not node:
                    continue
                
                if node.predecessors:
                    pred_outputs = [OUT.get(pred_id, {}) for pred_id in node.predecessors]
                    IN[node_id] = meet(pred_outputs)
                else:
                    IN[node_id] = initial_IN.get(node_id, {})
                
                old_out = OUT.get(node_id, {})
                new_out = transfer(node_id, IN[node_id])
                
                if new_out != old_out:
                    OUT[node_id] = new_out
                    changed = True
        
        return IN, OUT
    
    def run_backward_analysis(self,
                                initial_OUT: Dict[int, Dict],
                                transfer: Callable[[int, Dict], Dict],
                                meet: Callable[[List[Dict]], Dict]) -> Tuple[Dict[int, Dict], Dict[int, Dict]]:
        OUT = copy.deepcopy(initial_OUT)
        IN: Dict[int, Dict] = {node_id: {} for node_id in self.cfg.nodes}
        
        changed = True
        while changed:
            changed = False
            
            for node_id in reversed(self.cfg.nodes):
                node = self.cfg.nodes.get(node_id)
                if not node:
                    continue
                
                if node.successors:
                    succ_inputs = [IN.get(succ_id, {}) for succ_id in node.successors]
                    OUT[node_id] = meet(succ_inputs)
                else:
                    OUT[node_id] = initial_OUT.get(node_id, {})
                
                old_in = IN.get(node_id, {})
                new_in = transfer(node_id, OUT[node_id])
                
                if new_in != old_in:
                    IN[node_id] = new_in
                    changed = True
        
        return IN, OUT


class ReachingDefinitions(DataFlowAnalysis):
    def __init__(self, cfg: ControlFlowGraph, instructions: List[Dict]):
        super().__init__(cfg)
        self.instructions = instructions
        self.definitions: Dict[str, List[int]] = defaultdict(list)
        self._collect_definitions()
    
    def _collect_definitions(self):
        for i, instr in enumerate(self.instructions):
            defined = self._get_defined_vars(instr)
            for var in defined:
                self.definitions[var].append(i)
    
    def _get_defined_vars(self, instr: Dict) -> List[str]:
        opcode = instr.get("opcode", 0)
        operands = instr.get("operands", [])
        
        if operands and isinstance(operands[0], int):
            return [f"R{operands[0]}"]
        
        return []
    
    def _get_used_vars(self, instr: Dict) -> List[str]:
        operands = instr.get("operands", [])
        used = []
        
        for i, op in enumerate(operands):
            if i == 0:
                continue
            if isinstance(op, int):
                used.append(f"R{op}")
        
        return used
    
    def analyze(self) -> Tuple[Dict[int, Set], Dict[int, Set]]:
        initial_IN: Dict[int, Set] = {node_id: set() for node_id in self.cfg.nodes}
        
        def transfer(node_id: int, in_set: Set) -> Set:
            node = self.cfg.nodes.get(node_id)
            if not node:
                return in_set
            
            out_set = set(in_set)
            
            for instr in node.instructions:
                defined = self._get_defined_vars(instr)
                for var in defined:
                    for def_idx in self.definitions.get(var, []):
                        out_set.discard(def_idx)
                    
                    instr_idx = self._find_instruction_index(instr)
                    if instr_idx is not None:
                        out_set.add(instr_idx)
            
            return out_set
        
        def meet(sets_list: List[Set]) -> Set:
            if not sets_list:
                return set()
            result = set()
            for s in sets_list:
                result.update(s)
            return result
        
        return self.run_forward_analysis(initial_IN, transfer, meet)
    
    def _find_instruction_index(self, instr: Dict) -> Optional[int]:
        for i, existing in enumerate(self.instructions):
            if existing.get("opcode") == instr.get("opcode"):
                if existing.get("operands") == instr.get("operands"):
                    return i
        return None


class LiveVariables(DataFlowAnalysis):
    def __init__(self, cfg: ControlFlowGraph, instructions: List[Dict]):
        super().__init__(cfg)
        self.instructions = instructions
    
    def _get_defined_vars(self, instr: Dict) -> Set[str]:
        opcode = instr.get("opcode", 0)
        operands = instr.get("operands", [])
        
        defined = set()
        if operands and isinstance(operands[0], int):
            defined.add(f"R{operands[0]}")
        
        return defined
    
    def _get_used_vars(self, instr: Dict) -> Set[str]:
        operands = instr.get("operands", [])
        used = set()
        
        for i, op in enumerate(operands):
            if i == 0:
                continue
            if isinstance(op, int):
                used.add(f"R{op}")
        
        return used
    
    def analyze(self) -> Tuple[Dict[int, Set], Dict[int, Set]]:
        initial_OUT: Dict[int, Set] = {node_id: set() for node_id in self.cfg.nodes}
        
        def transfer(node_id: int, out_set: Set) -> Set:
            node = self.cfg.nodes.get(node_id)
            if not node:
                return out_set
            
            in_set = set(out_set)
            
            for instr in reversed(node.instructions):
                defined = self._get_defined_vars(instr)
                used = self._get_used_vars(instr)
                
                in_set -= defined
                in_set.update(used)
            
            return in_set
        
        def meet(sets_list: List[Set]) -> Set:
            if not sets_list:
                return set()
            result = set()
            for s in sets_list:
                result.update(s)
            return result
        
        return self.run_backward_analysis(initial_OUT, transfer, meet)


class UninitializedVariableAnalysis:
    def __init__(self, cfg: ControlFlowGraph, instructions: List[Dict]):
        self.cfg = cfg
        self.instructions = instructions
        self.all_variables: Set[str] = self._collect_all_variables()
    
    def _collect_all_variables(self) -> Set[str]:
        variables = set()
        for instr in self.instructions:
            operands = instr.get("operands", [])
            for op in operands:
                if isinstance(op, int) and 0 <= op <= 15:
                    variables.add(f"R{op}")
        return variables
    
    def analyze(self) -> List[Dict[str, Any]]:
        issues = []
        
        reaching = ReachingDefinitions(self.cfg, self.instructions)
        IN, OUT = reaching.analyze()
        
        variable_definitions: Dict[str, Set[int]] = defaultdict(set)
        for i, instr in enumerate(self.instructions):
            operands = instr.get("operands", [])
            if operands and isinstance(operands[0], int):
                var = f"R{operands[0]}"
                variable_definitions[var].add(i)
        
        for node_id, node in self.cfg.nodes.items():
            for i, instr in enumerate(node.instructions):
                operands = instr.get("operands", [])
                
                for j, op in enumerate(operands):
                    if j == 0:
                        continue
                    if isinstance(op, int):
                        var = f"R{op}"
                        
                        defs = variable_definitions.get(var, set())
                        
                        if not defs:
                            issues.append({
                                "type": "uninitialized_variable",
                                "variable": var,
                                "instruction_index": self._find_instruction_index(instr),
                                "instruction": instr,
                                "message": f"变量 {var} 在使用前从未被定义",
                                "severity": "warning",
                            })
        
        return issues
    
    def _find_instruction_index(self, instr: Dict) -> Optional[int]:
        for i, existing in enumerate(self.instructions):
            if existing.get("opcode") == instr.get("opcode"):
                if existing.get("operands") == instr.get("operands"):
                    return i
        return None


class DeadCodeAnalysis:
    def __init__(self, cfg: ControlFlowGraph, instructions: List[Dict]):
        self.cfg = cfg
        self.instructions = instructions
    
    def analyze(self) -> List[Dict[str, Any]]:
        issues = []
        
        unreachable = self.cfg.unreachable_nodes()
        for node_id in unreachable:
            node = self.cfg.nodes.get(node_id)
            if node:
                issues.append({
                    "type": "unreachable_code",
                    "node_id": node_id,
                    "block_name": node.block_name,
                    "instructions_count": len(node.instructions),
                    "message": f"基本块 {node.block_name} 不可达",
                    "severity": "warning",
                })
        
        live_analysis = LiveVariables(self.cfg, self.instructions)
        IN, OUT = live_analysis.analyze()
        
        for node_id, node in self.cfg.nodes.items():
            live = IN.get(node_id, set()).copy()
            
            for instr in reversed(node.instructions):
                defined = live_analysis._get_defined_vars(instr)
                used = live_analysis._get_used_vars(instr)
                
                for var in defined:
                    if var not in live:
                        issues.append({
                            "type": "dead_store",
                            "variable": var,
                            "instruction": instr,
                            "message": f"对变量 {var} 的赋值从未被使用",
                            "severity": "warning",
                        })
                
                live -= defined
                live.update(used)
        
        return issues


class MemoryAccessAnalysis:
    def __init__(self, cfg: ControlFlowGraph, instructions: List[Dict]):
        self.cfg = cfg
        self.instructions = instructions
        self.memory_instructions = {0, 17, 34, 47, 6, 22, 54, 50}
    
    def analyze(self) -> List[Dict[str, Any]]:
        issues = []
        
        memory_accesses: List[Dict] = []
        
        for i, instr in enumerate(self.instructions):
            opcode = instr.get("opcode", 0)
            if opcode in self.memory_instructions:
                operands = instr.get("operands", [])
                
                access_info = {
                    "index": i,
                    "opcode": opcode,
                    "operands": operands,
                    "is_write": opcode in {47, 6, 50},
                    "is_read": opcode in {0, 22, 54},
                }
                memory_accesses.append(access_info)
        
        for access in memory_accesses:
            operands = access.get("operands", [])
            
            if operands and isinstance(operands[1], int):
                addr = operands[1]
                
                if addr < 0 or addr > 0xFFFFF:
                    issues.append({
                        "type": "suspicious_memory_address",
                        "instruction_index": access["index"],
                        "address": addr,
                        "message": f"可疑的内存地址 0x{addr:X}",
                        "severity": "warning",
                    })
        
        for i in range(len(memory_accesses) - 1):
            access1 = memory_accesses[i]
            access2 = memory_accesses[i + 1]
            
            if access1["is_write"] and access2["is_read"]:
                if self._same_address(access1, access2):
                    issues.append({
                        "type": "write_after_read",
                        "instruction_indices": [access1["index"], access2["index"]],
                        "message": "写入后立即读取，可能需要优化",
                        "severity": "info",
                    })
        
        return issues
    
    def _same_address(self, access1: Dict, access2: Dict) -> bool:
        ops1 = access1.get("operands", [])
        ops2 = access2.get("operands", [])
        
        if len(ops1) >= 2 and len(ops2) >= 2:
            if ops1[1] == ops2[1]:
                return True
        
        return False


class ConcurrencyAnalysis:
    def __init__(self, cfg: ControlFlowGraph, instructions: List[Dict]):
        self.cfg = cfg
        self.instructions = instructions
        
        self.thread_ops = {63, 34}
        self.sync_ops = {58, 61, 21, 39, 10}
        self.lock_ops = {58, 10}
        self.unlock_ops = {39}
    
    def analyze(self) -> List[Dict[str, Any]]:
        issues = []
        
        lock_stack: List[Dict] = []
        thread_count = 0
        
        for i, instr in enumerate(self.instructions):
            opcode = instr.get("opcode", 0)
            
            if opcode in self.thread_ops:
                thread_count += 1
            
            if opcode in self.lock_ops:
                lock_stack.append({
                    "index": i,
                    "instruction": instr,
                })
            
            if opcode in self.unlock_ops:
                if lock_stack:
                    lock_stack.pop()
                else:
                    issues.append({
                        "type": "unmatched_unlock",
                        "instruction_index": i,
                        "message": "解锁操作没有对应的加锁",
                        "severity": "warning",
                    })
        
        for lock in lock_stack:
            issues.append({
                "type": "unreleased_lock",
                "instruction_index": lock["index"],
                "message": "锁可能未被释放，存在死锁风险",
                "severity": "warning",
            })
        
        if thread_count > 1:
            memory_analysis = MemoryAccessAnalysis(self.cfg, self.instructions)
            mem_issues = memory_analysis.analyze()
            
            sync_count = sum(1 for instr in self.instructions 
                           if instr.get("opcode", 0) in self.sync_ops)
            
            if sync_count == 0:
                issues.append({
                    "type": "missing_synchronization",
                    "thread_count": thread_count,
                    "message": f"检测到 {thread_count} 个线程操作，但没有同步指令",
                    "severity": "warning",
                })
        
        return issues


class StaticAnalyzer:
    def __init__(self):
        self.analyses: Dict[str, Any] = {}
        self.results: Dict[str, List] = {}
    
    def analyze_instructions(self, instructions: List[Dict]) -> Dict[str, Any]:
        self.results.clear()
        
        constructor = CFGConstructor()
        cfg = constructor.build_from_instructions(instructions)
        
        self.results["cfg"] = cfg.to_dict()
        
        loops = cfg.identify_loops()
        self.results["loops"] = loops
        
        self._run_data_flow_analyses(cfg, instructions)
        
        self._run_safety_analyses(cfg, instructions)
        
        return self._compile_results()
    
    def _run_data_flow_analyses(self, cfg: ControlFlowGraph, instructions: List[Dict]):
        reaching = ReachingDefinitions(cfg, instructions)
        IN, OUT = reaching.analyze()
        self.results["reaching_definitions"] = {
            "IN": {k: list(v) for k, v in IN.items()},
            "OUT": {k: list(v) for k, v in OUT.items()},
        }
        
        live = LiveVariables(cfg, instructions)
        LIVE_IN, LIVE_OUT = live.analyze()
        self.results["live_variables"] = {
            "IN": {k: list(v) for k, v in LIVE_IN.items()},
            "OUT": {k: list(v) for k, v in LIVE_OUT.items()},
        }
    
    def _run_safety_analyses(self, cfg: ControlFlowGraph, instructions: List[Dict]):
        uninit = UninitializedVariableAnalysis(cfg, instructions)
        self.results["uninitialized_variables"] = uninit.analyze()
        
        dead = DeadCodeAnalysis(cfg, instructions)
        self.results["dead_code"] = dead.analyze()
        
        memory = MemoryAccessAnalysis(cfg, instructions)
        self.results["memory_issues"] = memory.analyze()
        
        concurrency = ConcurrencyAnalysis(cfg, instructions)
        self.results["concurrency_issues"] = concurrency.analyze()
    
    def _compile_results(self) -> Dict[str, Any]:
        all_issues = []
        
        for category in ["uninitialized_variables", "dead_code", 
                         "memory_issues", "concurrency_issues"]:
            if category in self.results:
                for issue in self.results[category]:
                    issue["category"] = category
                    all_issues.append(issue)
        
        errors = [i for i in all_issues if i.get("severity") == "error"]
        warnings = [i for i in all_issues if i.get("severity") == "warning"]
        infos = [i for i in all_issues if i.get("severity") == "info"]
        
        return {
            "summary": {
                "total_issues": len(all_issues),
                "errors": len(errors),
                "warnings": len(warnings),
                "infos": len(infos),
                "has_critical": len(errors) > 0,
            },
            "issues": all_issues,
            "cfg": self.results.get("cfg"),
            "loops": self.results.get("loops", []),
            "data_flow": {
                "reaching_definitions": self.results.get("reaching_definitions"),
                "live_variables": self.results.get("live_variables"),
            },
        }
    
    def get_issues_by_severity(self, severity: str) -> List[Dict]:
        all_issues = []
        for category in ["uninitialized_variables", "dead_code", 
                         "memory_issues", "concurrency_issues"]:
            if category in self.results:
                all_issues.extend([
                    i for i in self.results[category] 
                    if i.get("severity") == severity
                ])
        return all_issues
