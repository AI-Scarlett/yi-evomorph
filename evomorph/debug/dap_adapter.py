#!/usr/bin/env python3
"""
易衍·Evomorph Debug Adapter Protocol (DAP) 适配器
连接 IChingVM 虚拟机，支持调试功能
"""

import json
import sys
import os
import subprocess
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from evomorph.compiler import EvocCompiler


@dataclass
class StackFrame:
    id: int
    name: str
    source: Dict[str, Any]
    line: int
    column: int


@dataclass
class Scope:
    name: str
    variablesReference: int
    expensive: bool = False


@dataclass
class Variable:
    name: str
    value: str
    type: str
    variablesReference: int = 0
    evaluateName: Optional[str] = None


@dataclass
class Breakpoint:
    id: int
    verified: bool
    line: int
    message: Optional[str] = None
    source: Optional[Dict[str, Any]] = None


class IChingVMDebugger:
    """IChingVM 调试器包装器"""
    
    def __init__(self):
        self.vm_path = None
        self.breakpoints: Dict[str, List[Breakpoint]] = {}
        self.current_pc = 0
        self.is_running = False
        self.is_stopped = False
        self.current_source: Optional[str] = None
        self.current_instructions: List[Dict] = []
        self.breakpoint_count = 0
        self.stack_frames: List[StackFrame] = []
        self.variables: Dict[int, List[Variable]] = {}
        self.next_variable_ref = 1
        self.compiler = EvocCompiler()
        self.registers = {f"R{i}": 0 for i in range(16)}
        self.registers["R_FP"] = 0
        self.registers["R_SP"] = 65536
        self.registers["R_LR"] = 0
        self.registers["R_A0"] = 0
        self.memory: Dict[int, int] = {}
        
    def set_vm_path(self, vm_path: str):
        self.vm_path = vm_path
        
    def compile_source(self, source_path: str):
        """编译源代码"""
        self.current_source = source_path
        
        if source_path.endswith('.evo'):
            result = self.compiler.compile_file(source_path, output_format='dict')
            self.current_instructions = []
            
            for locus in result.get('loci', []):
                for instr in locus.get('instructions', []):
                    self.current_instructions.append({
                        'mnemonic': instr.get('mnemonic', 'NOP'),
                        'operands': instr.get('operands', []),
                        'opcode': instr.get('opcode'),
                    })
            
            return True
        else:
            return True
        
    def set_breakpoints(self, source: str, lines: List[int]) -> List[Breakpoint]:
        """设置断点"""
        bps = []
        for line in lines:
            self.breakpoint_count += 1
            bp = Breakpoint(
                id=self.breakpoint_count,
                verified=True,
                line=line,
                source={"path": source, "name": os.path.basename(source)}
            )
            bps.append(bp)
        
        self.breakpoints[source] = bps
        return bps
    
    def launch(self, program: str, max_cycles: int = 10000, platform: str = "linux-6.x"):
        """启动调试会话"""
        self.current_pc = 0
        self.is_running = True
        self.is_stopped = False
        self.compile_source(program)
        return True
    
    def continue_execution(self):
        """继续执行"""
        if not self.current_instructions:
            self.is_running = False
            return False
        
        while self.current_pc < len(self.current_instructions):
            self._execute_instruction()
            self.current_pc += 1
            
            if self._check_breakpoint():
                self.is_stopped = True
                return "breakpoint"
        
        self.is_running = False
        return "exited"
    
    def next(self):
        """单步执行"""
        if self.current_pc < len(self.current_instructions):
            self._execute_instruction()
            self.current_pc += 1
            self.is_stopped = True
            return "step"
        
        self.is_running = False
        return "exited"
    
    def _execute_instruction(self):
        """模拟执行指令"""
        if self.current_pc >= len(self.current_instructions):
            return
        
        instr = self.current_instructions[self.current_pc]
        mnemonic = instr.get('mnemonic', 'NOP')
        operands = instr.get('operands', [])
        
        if mnemonic == "CREA":
            pass
        elif mnemonic == "ABOUND":
            if len(operands) >= 2:
                reg = self._parse_register(operands[0])
                val = self._parse_value(operands[1])
                if reg:
                    self.registers[reg] = val
        elif mnemonic == "INCREASE":
            if len(operands) >= 2:
                reg1 = self._parse_register(operands[0])
                reg2 = self._parse_register(operands[1])
                if reg1 and reg2:
                    self.registers[reg1] += self.registers.get(reg2, 0)
        elif mnemonic == "REDUCE":
            if len(operands) >= 2:
                reg1 = self._parse_register(operands[0])
                reg2 = self._parse_register(operands[1])
                if reg1 and reg2:
                    self.registers[reg1] -= self.registers.get(reg2, 0)
        elif mnemonic == "SYNC":
            pass
        elif mnemonic == "HALT":
            self.is_running = False
    
    def _parse_register(self, op):
        """解析寄存器"""
        if isinstance(op, dict):
            if op.get('kind') == 'register':
                val = op.get('value', 0)
                if isinstance(val, int):
                    return f"R{val}"
                elif isinstance(val, str):
                    return val.upper()
        elif isinstance(op, str):
            if op.startswith('R'):
                return op.upper()
        return None
    
    def _parse_value(self, op):
        """解析数值"""
        if isinstance(op, dict):
            if op.get('kind') in ('immediate', 'env_ref'):
                return int(op.get('value', 0))
        elif isinstance(op, int):
            return op
        elif isinstance(op, str):
            try:
                return int(op, 0)
            except ValueError:
                pass
        return 0
    
    def _check_breakpoint(self):
        """检查是否命中断点"""
        if not self.current_source:
            return False
        
        bps = self.breakpoints.get(self.current_source, [])
        
        line = self.current_pc + 1
        
        for bp in bps:
            if bp.line == line or abs(bp.line - line) <= 5:
                return True
        
        return False
    
    def get_stack_frames(self) -> List[StackFrame]:
        """获取栈帧"""
        frames = []
        
        for i in range(self.current_pc + 1):
            if i < len(self.current_instructions):
                instr = self.current_instructions[i]
                mnemonic = instr.get('mnemonic', 'NOP')
                
                frames.append(StackFrame(
                    id=i,
                    name=f"{mnemonic} (PC={i})",
                    source={"path": self.current_source or "unknown", "name": os.path.basename(self.current_source or "unknown")},
                    line=i + 1,
                    column=1
                ))
        
        return frames[-10:]
    
    def get_scopes(self, frame_id: int) -> List[Scope]:
        """获取作用域"""
        return [
            Scope(name="寄存器", variablesReference=1),
            Scope(name="内存", variablesReference=2),
        ]
    
    def get_variables(self, variables_reference: int) -> List[Variable]:
        """获取变量"""
        if variables_reference == 1:
            return [
                Variable(name=name, value=str(val), type="register")
                for name, val in self.registers.items()
            ]
        elif variables_reference == 2:
            return [
                Variable(name=f"0x{addr:04X}", value=str(val), type="memory")
                for addr, val in list(self.memory.items())[:20]
            ]
        return []


class DAPAdapter:
    """Debug Adapter Protocol 适配器"""
    
    def __init__(self):
        self.debugger = IChingVMDebugger()
        self.seq = 0
        self.request_seq = 0
        
    def send(self, msg: Dict[str, Any]):
        """发送 DAP 消息"""
        msg_str = json.dumps(msg, ensure_ascii=False)
        msg_bytes = msg_str.encode('utf-8')
        header = f"Content-Length: {len(msg_bytes)}\r\n\r\n".encode('utf-8')
        sys.stdout.buffer.write(header + msg_bytes)
        sys.stdout.buffer.flush()
        
    def send_response(self, request: Dict[str, Any], body: Any = None, success: bool = True, message: str = ""):
        """发送响应"""
        self.seq += 1
        response = {
            "type": "response",
            "seq": self.seq,
            "request_seq": request.get("seq", 0),
            "success": success,
            "command": request.get("command", ""),
        }
        if body is not None:
            response["body"] = body
        if not success and message:
            response["message"] = message
        
        self.send(response)
    
    def send_event(self, event: str, body: Any = None):
        """发送事件"""
        self.seq += 1
        evt = {
            "type": "event",
            "seq": self.seq,
            "event": event,
        }
        if body is not None:
            evt["body"] = body
        
        self.send(evt)
    
    def handle_request(self, request: Dict[str, Any]):
        """处理 DAP 请求"""
        command = request.get("command", "")
        self.request_seq = request.get("seq", 0)
        
        if command == "initialize":
            self._handle_initialize(request)
        elif command == "launch":
            self._handle_launch(request)
        elif command == "configurationDone":
            self._handle_configuration_done(request)
        elif command == "setBreakpoints":
            self._handle_set_breakpoints(request)
        elif command == "threads":
            self._handle_threads(request)
        elif command == "stackTrace":
            self._handle_stack_trace(request)
        elif command == "scopes":
            self._handle_scopes(request)
        elif command == "variables":
            self._handle_variables(request)
        elif command == "continue":
            self._handle_continue(request)
        elif command == "next":
            self._handle_next(request)
        elif command == "stepIn":
            self._handle_step_in(request)
        elif command == "stepOut":
            self._handle_step_out(request)
        elif command == "disconnect":
            self._handle_disconnect(request)
        elif command == "evaluate":
            self._handle_evaluate(request)
        elif command == "pause":
            self._handle_pause(request)
        else:
            self.send_response(request, None, False, f"未知命令: {command}")
    
    def _handle_initialize(self, request: Dict[str, Any]):
        """处理初始化"""
        self.send_response(request, {
            "supportsConfigurationDoneRequest": True,
            "supportsFunctionBreakpoints": False,
            "supportsConditionalBreakpoints": False,
            "supportsHitConditionalBreakpoints": False,
            "supportsEvaluateForHovers": True,
            "exceptionBreakpointFilters": [],
            "supportsStepBack": False,
            "supportsSetVariable": False,
            "supportsRestartFrame": False,
            "supportsGotoTargetsRequest": False,
            "supportsStepInTargetsRequest": False,
            "supportsCompletionsRequest": False,
            "supportsModulesRequest": False,
            "additionalModuleColumns": [],
            "supportedChecksumAlgorithms": [],
            "supportsRestartRequest": False,
            "supportsExceptionOptions": False,
            "supportsValueFormattingOptions": False,
            "supportsExceptionInfoRequest": False,
            "supportTerminateDebuggee": True,
            "supportsDelayedStackTraceLoading": True,
            "supportsLoadedSourcesRequest": False,
            "supportsLogPoints": False,
            "supportsBreakpointLocationsRequest": False,
        })
        self.send_event("initialized")
    
    def _handle_launch(self, request: Dict[str, Any]):
        """处理启动"""
        params = request.get("params", {})
        program = params.get("program", "")
        max_cycles = params.get("maxCycles", 10000)
        platform = params.get("platform", "linux-6.x")
        
        if not program:
            self.send_response(request, None, False, "未指定程序路径")
            return
        
        success = self.debugger.launch(program, max_cycles, platform)
        self.send_response(request, None, success, "启动失败" if not success else "")
    
    def _handle_configuration_done(self, request: Dict[str, Any]):
        """配置完成"""
        self.send_response(request, {})
        
        self.send_event("stopped", {
            "reason": "entry",
            "threadId": 1,
        })
    
    def _handle_set_breakpoints(self, request: Dict[str, Any]):
        """设置断点"""
        params = request.get("params", {})
        source = params.get("source", {}).get("path", "")
        lines = [bp.get("line", 0) for bp in params.get("breakpoints", [])]
        
        if not source:
            self.send_response(request, {"breakpoints": []})
            return
        
        bps = self.debugger.set_breakpoints(source, lines)
        self.send_response(request, {
            "breakpoints": [asdict(bp) for bp in bps]
        })
    
    def _handle_threads(self, request: Dict[str, Any]):
        """获取线程"""
        self.send_response(request, {
            "threads": [
                {"id": 1, "name": "主线程"},
            ]
        })
    
    def _handle_stack_trace(self, request: Dict[str, Any]):
        """获取栈跟踪"""
        frames = self.debugger.get_stack_frames()
        self.send_response(request, {
            "stackFrames": [asdict(f) for f in frames],
            "totalFrames": len(frames)
        })
    
    def _handle_scopes(self, request: Dict[str, Any]):
        """获取作用域"""
        frame_id = request.get("params", {}).get("frameId", 0)
        scopes = self.debugger.get_scopes(frame_id)
        self.send_response(request, {
            "scopes": [asdict(s) for s in scopes]
        })
    
    def _handle_variables(self, request: Dict[str, Any]):
        """获取变量"""
        variables_ref = request.get("params", {}).get("variablesReference", 0)
        variables = self.debugger.get_variables(variables_ref)
        self.send_response(request, {
            "variables": [asdict(v) for v in variables]
        })
    
    def _handle_continue(self, request: Dict[str, Any]):
        """继续执行"""
        reason = self.debugger.continue_execution()
        
        self.send_response(request, {
            "allThreadsContinued": True
        })
        
        if reason == "breakpoint":
            self.send_event("stopped", {
                "reason": "breakpoint",
                "threadId": 1,
            })
        elif reason == "exited":
            self.send_event("exited", {"exitCode": 0})
            self.send_event("terminated")
    
    def _handle_next(self, request: Dict[str, Any]):
        """单步执行"""
        reason = self.debugger.next()
        
        self.send_response(request, {})
        
        if reason == "step":
            self.send_event("stopped", {
                "reason": "step",
                "threadId": 1,
            })
        elif reason == "exited":
            self.send_event("exited", {"exitCode": 0})
            self.send_event("terminated")
    
    def _handle_step_in(self, request: Dict[str, Any]):
        """步入"""
        self._handle_next(request)
    
    def _handle_step_out(self, request: Dict[str, Any]):
        """步出"""
        self._handle_next(request)
    
    def _handle_disconnect(self, request: Dict[str, Any]):
        """断开连接"""
        self.debugger.is_running = False
        self.send_response(request, {})
        self.send_event("terminated")
    
    def _handle_evaluate(self, request: Dict[str, Any]):
        """求值"""
        expression = request.get("params", {}).get("expression", "")
        
        if expression.startswith("R"):
            val = self.debugger.registers.get(expression.upper(), 0)
            self.send_response(request, {
                "result": str(val),
                "type": "register",
                "variablesReference": 0,
            })
        else:
            self.send_response(request, {
                "result": "未找到",
                "type": "unknown",
                "variablesReference": 0,
            })
    
    def _handle_pause(self, request: Dict[str, Any]):
        """暂停"""
        self.debugger.is_stopped = True
        self.send_response(request, {})
        self.send_event("stopped", {
            "reason": "pause",
            "threadId": 1,
        })


def main():
    """DAP 适配器主函数"""
    adapter = DAPAdapter()
    
    import asyncio
    
    async def run():
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        transport, _ = await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
        
        while True:
            line = await reader.readline()
            if not line:
                break
            
            header = line.decode("utf-8").strip()
            content_length = 0
            
            if header.startswith("Content-Length:"):
                try:
                    content_length = int(header.split(":")[1].strip())
                except ValueError:
                    content_length = 0
                await reader.readline()
            
            if content_length > 0:
                body = await reader.read(content_length)
                try:
                    request = json.loads(body.decode("utf-8"))
                    adapter.handle_request(request)
                except Exception as e:
                    adapter.send({
                        "type": "response",
                        "seq": adapter.seq + 1,
                        "request_seq": adapter.request_seq,
                        "success": False,
                        "command": request.get("command", "") if 'request' in dir() else "",
                        "message": str(e)
                    })
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
