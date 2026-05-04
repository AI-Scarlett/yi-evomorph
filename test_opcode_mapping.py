#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from evomorph.hexagrams import HexagramInstructionSet

print('=' * 60)
print('易衍指令集映射验证')
print('=' * 60)

isa = HexagramInstructionSet()

print('\n--- 关键指令映射 ---')
key_mnemonics = [
    ('CREA', '创建进程'),
    ('RECV', '接收消息'),
    ('ABOUND', '加载立即数'),
    ('INCREASE', '加法'),
    ('REDUCE', '减法'),
    ('SHL', '左移'),
    ('SHR', '右移'),
    ('AND', '按位与'),
    ('OR', '按位或'),
    ('XOR', '按位异或'),
    ('HALT', '停止'),
]

print(f'{"助记符":<12} {"卦象":<6} {"操作码":<6} {"拼音":<12} {"说明"}')
print('-' * 60)

for mnemonic, desc in key_mnemonics:
    entry = isa.get_by_mnemonic(mnemonic)
    if entry:
        print(f'{mnemonic:<12} {entry["symbol"]:<6} {entry["opcode"]:<6} {entry["pinyin"]:<12} {desc}')
    else:
        print(f'{mnemonic:<12} (未找到)')

print('\n--- 别名指令对应关系 ---')
print('SHL  -> PREFETCH (opcode 55)  - 小畜卦')
print('SHR  -> FLUSH    (opcode 7)   - 泰卦')
print('AND  -> APPROACH (opcode 3)   - 临卦')
print('OR   -> MERGE    (opcode 16)  - 比卦')
print('XOR  -> ADORN    (opcode 37)  - 贲卦')

print('\n--- C 虚拟机操作码索引 ---')
print('从 ichingvm.c 的操作码表:')
print('  opcode 0: KUN (RECV)')
print('  opcode 3: LIN (APPROACH/AND)')
print('  opcode 7: TAI (FLUSH/SHR)')
print('  opcode 13: FENG (ABOUND)')
print('  opcode 16: BI (MERGE/OR)')
print('  opcode 35: SUN (REDUCE)')
print('  opcode 37: BIX (ADORN/XOR)')
print('  opcode 49: YIX (INCREASE)')
print('  opcode 55: XIAOXU (PREFETCH/SHL)')
print('  opcode 56: PI (HALT)')
print('  opcode 63: QIAN (CREA)')

print('\n' + '=' * 60)
