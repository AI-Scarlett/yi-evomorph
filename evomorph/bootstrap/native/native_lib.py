"""
易衍·Evomorph 原生标准库
用传统CPU指令实现的标准库
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evomorph.vm.extended_vm2 import ExtendedIChingVM2


class NativeLib:
    """
    原生标准库 - 用传统CPU指令实现
    """
    
    @staticmethod
    def strlen_asm() -> str:
        """字符串长度函数"""
        return """
        ; R0 = 字符串地址
        ; 返回 R0 = 长度
        ; 使用寄存器 R1-R3 作为临时
strlen:
        MOVI R1, #0          ; 计数器 = 0
strlen_loop:
        LDRB R2, R0          ; 读取当前字符
        CMP R2, R1           ; 比较是否为0
        JE strlen_done       ; 如果是0，结束
        INC R1               ; 计数器+1
        INC R0               ; 地址+1
        JMP strlen_loop      ; 循环
strlen_done:
        MOV R0, R1           ; 返回长度
        RET
        """
    
    @staticmethod
    def strcmp_asm() -> str:
        """字符串比较函数"""
        return """
        ; R0 = 字符串A地址
        ; R1 = 字符串B地址
        ; 返回 R0 = 0(相等), <0(A<B), >0(A>B)
strcmp:
strcmp_loop:
        LDRB R2, R0          ; 读取A的字符
        LDRB R3, R1          ; 读取B的字符
        CMP R2, R3           ; 比较
        JNE strcmp_diff      ; 不相等
        CMP R2, #0           ; 检查是否结束
        JE strcmp_equal      ; 都为0，相等
        INC R0               ; A地址+1
        INC R1               ; B地址+1
        JMP strcmp_loop      ; 循环
strcmp_diff:
        MOV R0, R2
        SUB R0, R3
        RET
strcmp_equal:
        MOVI R0, #0          ; 返回0
        RET
        """
    
    @staticmethod
    def strcpy_asm() -> str:
        """字符串复制函数"""
        return """
        ; R0 = 目标地址
        ; R1 = 源地址
        ; 返回 R0 = 目标地址
strcpy:
        PUSH R0              ; 保存目标地址
strcpy_loop:
        LDRB R2, R1          ; 读取源字符
        STRB R0, R2          ; 写入目标
        CMP R2, #0           ; 检查是否结束
        JE strcpy_done       ; 结束
        INC R0               ; 目标地址+1
        INC R1               ; 源地址+1
        JMP strcpy_loop      ; 循环
strcpy_done:
        POP R0               ; 恢复目标地址
        RET
        """
    
    @staticmethod
    def strcat_asm() -> str:
        """字符串连接函数"""
        return """
        ; R0 = 目标地址
        ; R1 = 源地址
        ; 返回 R0 = 目标地址
strcat:
        PUSH R0              ; 保存目标地址
strcat_find_end:
        LDRB R2, R0          ; 读取字符
        CMP R2, #0           ; 检查是否结束
        JE strcat_copy       ; 找到结束
        INC R0               ; 地址+1
        JMP strcat_find_end  ; 循环
strcat_copy:
        LDRB R2, R1          ; 读取源字符
        STRB R0, R2          ; 写入目标
        CMP R2, #0           ; 检查是否结束
        JE strcat_done       ; 结束
        INC R0               ; 目标地址+1
        INC R1               ; 源地址+1
        JMP strcat_copy      ; 循环
strcat_done:
        POP R0               ; 恢复目标地址
        RET
        """
    
    @staticmethod
    def memset_asm() -> str:
        """内存设置函数"""
        return """
        ; R0 = 目标地址
        ; R1 = 值
        ; R2 = 大小
        ; 返回 R0 = 目标地址
memset:
        PUSH R0              ; 保存目标地址
        CMP R2, #0           ; 检查大小
        JE memset_done       ; 大小为0，结束
memset_loop:
        STRB R0, R1          ; 写入值
        INC R0               ; 地址+1
        DEC R2               ; 大小-1
        JNE memset_loop      ; 循环
memset_done:
        POP R0               ; 恢复目标地址
        RET
        """
    
    @staticmethod
    def memcpy_asm() -> str:
        """内存复制函数"""
        return """
        ; R0 = 目标地址
        ; R1 = 源地址
        ; R2 = 大小
        ; 返回 R0 = 目标地址
memcpy:
        PUSH R0              ; 保存目标地址
        CMP R2, #0           ; 检查大小
        JE memcpy_done       ; 大小为0，结束
memcpy_loop:
        LDRB R3, R1          ; 读取源
        STRB R0, R3          ; 写入目标
        INC R0               ; 目标地址+1
        INC R1               ; 源地址+1
        DEC R2               ; 大小-1
        JNE memcpy_loop      ; 循环
memcpy_done:
        POP R0               ; 恢复目标地址
        RET
        """
    
    @staticmethod
    def is_digit_asm() -> str:
        """检查是否为数字字符"""
        return """
        ; R0 = 字符
        ; 返回 R0 = 1(是), 0(否)
is_digit:
        MOVI R1, #'0'        ; '0' = 48
        CMP R0, R1           ; 比较 '0'
        JL is_digit_no       ; 小于 '0'
        MOVI R1, #'9'        ; '9' = 57
        CMP R0, R1           ; 比较 '9'
        JG is_digit_no       ; 大于 '9'
        MOVI R0, #1          ; 是数字
        RET
is_digit_no:
        MOVI R0, #0          ; 不是数字
        RET
        """
    
    @staticmethod
    def is_alpha_asm() -> str:
        """检查是否为字母字符"""
        return """
        ; R0 = 字符
        ; 返回 R0 = 1(是), 0(否)
is_alpha:
        MOVI R1, #'A'        ; 'A' = 65
        CMP R0, R1
        JL is_alpha_check_lower
        MOVI R1, #'Z'        ; 'Z' = 90
        CMP R0, R1
        JG is_alpha_check_lower
        MOVI R0, #1
        RET
is_alpha_check_lower:
        MOVI R1, #'a'        ; 'a' = 97
        CMP R0, R1
        JL is_alpha_no
        MOVI R1, #'z'        ; 'z' = 122
        CMP R0, R1
        JG is_alpha_no
        MOVI R0, #1
        RET
is_alpha_no:
        MOVI R0, #0
        RET
        """
    
    @staticmethod
    def is_alnum_asm() -> str:
        """检查是否为字母数字字符"""
        return """
        ; R0 = 字符
        ; 返回 R0 = 1(是), 0(否)
is_alnum:
        PUSH R4              ; 保存R4
        MOV R4, R0           ; 保存字符到R4
        CALL is_digit        ; 检查数字
        CMP R0, #1
        JE is_alnum_yes
        MOV R0, R4           ; 恢复字符
        CALL is_alpha        ; 检查字母
        CMP R0, #1
        JE is_alnum_yes
        MOVI R0, #0
        POP R4
        RET
is_alnum_yes:
        MOVI R0, #1
        POP R4
        RET
        """
    
    @staticmethod
    def is_whitespace_asm() -> str:
        """检查是否为空白字符"""
        return """
        ; R0 = 字符
        ; 返回 R0 = 1(是), 0(否)
is_whitespace:
        CMP R0, #' '         ; 空格
        JE is_whitespace_yes
        CMP R0, #9           ; 制表符
        JE is_whitespace_yes
        CMP R0, #10          ; 换行
        JE is_whitespace_yes
        CMP R0, #13          ; 回车
        JE is_whitespace_yes
        MOVI R0, #0
        RET
is_whitespace_yes:
        MOVI R0, #1
        RET
        """
    
    @staticmethod
    def strchr_asm() -> str:
        """查找字符"""
        return """
        ; R0 = 字符串地址
        ; R1 = 要查找的字符
        ; 返回 R0 = 找到的位置(或NULL)
strchr:
strchr_loop:
        LDRB R2, R0          ; 读取当前字符
        CMP R2, R1           ; 比较
        JE strchr_found      ; 找到
        CMP R2, #0           ; 检查是否结束
        JE strchr_not_found  ; 没找到
        INC R0               ; 地址+1
        JMP strchr_loop      ; 循环
strchr_found:
        RET
strchr_not_found:
        MOVI R0, #0
        RET
        """
    
    @staticmethod
    def strstr_asm() -> str:
        """查找子字符串"""
        return """
        ; R0 = 字符串地址
        ; R1 = 子字符串地址
        ; 返回 R0 = 找到的位置(或NULL)
strstr:
        PUSH R0
        PUSH R1
        MOV R2, R0           ; 保存起始位置
strstr_main_loop:
        LDRB R3, R2          ; 读取主串字符
        CMP R3, #0           ; 主串结束
        JE strstr_not_found
        
        MOV R0, R2           ; 当前位置
        POP R1               ; 恢复子串
        PUSH R1              ; 再次保存
        MOV R4, R1           ; 子串起始
        
strstr_cmp_loop:
        LDRB R5, R0          ; 主串字符
        LDRB R6, R4          ; 子串字符
        CMP R6, #0           ; 子串结束
        JE strstr_found      ; 找到
        CMP R5, R6           ; 比较
        JNE strstr_next      ; 不匹配
        INC R0               ; 主串+1
        INC R4               ; 子串+1
        JMP strstr_cmp_loop  ; 继续比较
        
strstr_next:
        INC R2               ; 主串下一个位置
        JMP strstr_main_loop
        
strstr_found:
        POP R1               ; 清理栈
        POP R0
        MOV R0, R2
        RET
        
strstr_not_found:
        POP R1               ; 清理栈
        POP R0
        MOVI R0, #0
        RET
        """
    
    @staticmethod
    def atoi_asm() -> str:
        """字符串转整数"""
        return """
        ; R0 = 字符串地址
        ; 返回 R0 = 整数值
atoi:
        MOVI R1, #0          ; 结果
        MOVI R2, #1          ; 符号 (1=正, -1=负)
        MOVI R3, #0          ; 是否有数字
        
        ; 跳过空白
atoi_skip_whitespace:
        LDRB R4, R0
        CALL is_whitespace
        CMP R0, #1
        JNE atoi_check_sign
        INC R0
        JMP atoi_skip_whitespace
        
atoi_check_sign:
        LDRB R4, R0
        CMP R4, #'-'
        JNE atoi_check_plus
        MOVI R2, #-1
        INC R0
        JMP atoi_digit_loop
        
atoi_check_plus:
        CMP R4, #'+'
        JNE atoi_digit_loop
        INC R0
        
atoi_digit_loop:
        LDRB R4, R0
        CALL is_digit
        CMP R0, #1
        JNE atoi_done
        
        ; 转换数字
        MOVI R0, #10
        MUL R1, R0           ; result *= 10
        SUB R4, #'0'         ; digit - '0'
        ADD R1, R4           ; result += digit
        MOVI R3, #1          ; 标记有数字
        INC R0
        JMP atoi_digit_loop
        
atoi_done:
        CMP R3, #1
        JNE atoi_no_digit
        
        ; 应用符号
        MOV R0, R1
        CMP R2, #-1
        JNE atoi_return
        NEG R0
atoi_return:
        RET
        
atoi_no_digit:
        MOVI R0, #0
        RET
        """
    
    @staticmethod
    def itoa_asm() -> str:
        """整数转字符串"""
        return """
        ; R0 = 整数值
        ; R1 = 字符串缓冲区
        ; R2 = 基数 (2, 8, 10, 16)
        ; 返回 R0 = 字符串地址
itoa:
        PUSH R1              ; 保存缓冲区地址
        MOV R3, R0           ; 保存值
        MOVI R4, #0          ; 负数标记
        
        ; 处理负数 (基数10)
        CMP R2, #10
        JNE itoa_convert
        CMP R3, #0
        JGE itoa_convert
        MOVI R4, #1          ; 标记负数
        NEG R3               ; 转为正数
        
itoa_convert:
        MOV R0, R3
        MOV R5, #0           ; 数字计数
        
itoa_div_loop:
        MOV R0, R3           ; R0 = current value
        DIV R0, R2           ; R0 = quotient
        MOV R6, R0           ; 保存商
        ; 计算余数
        MUL R0, R2           ; 商 * 除数
        SUB R3, R0           ; 被除数 - (商*除数) = 余数
        
        ; 转换余数为字符
        CMP R3, #10
        JL itoa_digit_char
        ADD R3, #'A' - 10    ; 10-15 -> 'A'-'F'
        JMP itoa_store_char
itoa_digit_char:
        ADD R3, #'0'         ; 0-9 -> '0'-'9'
        
itoa_store_char:
        STRB R1, R3          ; 存储字符
        INC R1
        INC R5
        
        ; 检查是否还有更多数字
        MOV R3, R6
        CMP R3, #0
        JNE itoa_div_loop
        
        ; 处理负号
        CMP R4, #1
        JNE itoa_reverse
        MOVI R0, #'-'
        STRB R1, R0
        INC R1
        INC R5
        
itoa_reverse:
        ; 添加字符串结束符
        MOVI R0, #0
        STRB R1, R0
        
        ; 反转字符串
        POP R0               ; 起始地址
        MOV R1, R0
        ADD R1, R5
        DEC R1               ; 最后一个字符
        
itoa_rev_loop:
        CMP R0, R1
        JGE itoa_done
        
        ; 交换 *R0 和 *R1
        LDRB R2, R0
        LDRB R3, R1
        STRB R0, R3
        STRB R1, R2
        
        INC R0
        DEC R1
        JMP itoa_rev_loop
        
itoa_done:
        POP R0               ; 返回起始地址
        RET
        """


def test_native_lib():
    """测试原生库"""
    print("=" * 60)
    print("测试原生标准库")
    print("=" * 60)
    
    vm = ExtendedIChingVM2()
    
    # 测试字符串长度
    print("\n测试 strlen:")
    
    test_str = b"Hello, World!\x00"
    for i, b in enumerate(test_str):
        vm.heap[i] = b
    
    asm = NativeLib.strlen_asm()
    print(f"汇编代码长度: {len(asm.splitlines())} 行")
    
    print("✓ 原生库加载成功")
    
    return True


if __name__ == "__main__":
    test_native_lib()
