/*
 * IChingVM - 易衍虚拟机 C 语言实现
 * 种子虚拟机 - 用于自举
 * 
 * 六十四卦指令集:
 * - 操作码 = 爻位二进制 (6位)
 * - 每条指令 = 4字节: [opcode<<2|mod>>4, mod&0xF, operand1, operand2]
 * 
 * 操作码映射 (来自 instruction_set.py):
 *  0: KUN     - RECV
 *  1: FU      - RETURN
 *  2: SHI     - BRANCH
 *  3: LIN     - APPROACH / AND
 *  4: QIANX   - YIELD
 *  5: MINGYI  - OBSCURE
 *  6: SHENG   - PUSH_UP
 *  7: TAI     - FLUSH / SHR
 *  8: YU      - SPECULATE
 *  9: ZHEN    - SHOCK
 * 10: JIE     - UNLOCK
 * 11: GUIMEI  - MISMATCH
 * 12: XIAOGUO - MICRO
 * 13: FENG    - ABOUND
 * 14: HENG    - PERSIST
 * 15: DAZHUANG- THRUST
 * 16: BI      - MERGE / OR
 * 17: ZHUN    - ALLOC
 * 18: KAN     - TRAP
 * 19: JIEX    - THROTTLE
 * 20: JIANX   - LAME
 * 21: JIJI    - SYNC
 * 22: JING    - WELL
 * 23: XU      - WAIT
 * 24: CUI     - GATHER
 * 25: SUI     - FOLLOWING
 * 26: KUNX    - TRAPPED
 * 27: DUI     - JOY
 * 28: XIAN    - SENSE
 * 29: GE      - REPLACE
 * 30: DAGUO   - OVERLOAD
 * 31: GUAI    - BREAK
 * 32: BO      - STRIP
 * 33: YI      - NOURISH
 * 34: MENG    - SPRT
 * 35: SUN     - REDUCE
 * 36: GEN     - STILL
 * 37: BIX     - ADORN / XOR
 * 38: GU      - MUT
 * 39: DAXU    - BARRIER
 * 40: JIN     - ADVANCE
 * 41: SHIHE   - BITE
 * 42: WEIJI   - FUTU
 * 43: KUI     - CONVERT
 * 44: LVX     - TRAVEL
 * 45: LI      - ILLUMINATE
 * 46: DING    - CAST
 * 47: DAYOU   - ABUNDANCE
 * 48: GUAN    - CONTEMPLATE
 * 49: YIX     - INCREASE
 * 50: HUAN    - DISPERSE
 * 51: ZHONGFU - TRUST
 * 52: JIANJ   - GRADUAL
 * 53: JIAREN  - BIND
 * 54: XUN     - PENETRATE
 * 55: XIAOXU  - PREFETCH / SHL
 * 56: PI      - HALT
 * 57: WUWANG  - INTRINSIC
 * 58: SONG    - LOCK
 * 59: LV      - STEP
 * 60: DUN     - RETREAT
 * 61: TONGREN - FELLOWSHIP
 * 62: GOU     - MATE
 * 63: QIAN    - CREA
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <ctype.h>

#define NUM_REGISTERS 16
#define STACK_SIZE 65536
#define HEAP_SIZE 1048576
#define MAX_LOCKS 256
#define MAX_BARRIERS 256

#define R_FP 12
#define R_SP 13
#define R_LR 14
#define R_A0 15

typedef enum {
    VM_INIT = 0,
    VM_RUNNING = 1,
    VM_PAUSED = 2,
    VM_HALTED = 3,
    VM_ERROR = 4,
    VM_TRAPPED = 5
} VMState;

typedef struct {
    uint32_t registers[NUM_REGISTERS];
    uint8_t stack[STACK_SIZE];
    uint8_t heap[HEAP_SIZE];
    uint32_t heap_ptr;
    uint32_t pc;
    VMState state;
    uint8_t *program;
    uint32_t program_len;
    
    uint8_t flag_zero;
    uint8_t flag_carry;
    uint8_t flag_negative;
    uint8_t flag_overflow;
    
    uint32_t future_id_counter;
    uint8_t locks[MAX_LOCKS];
    uint32_t barriers[MAX_BARRIERS];
    
    uint64_t cycle_count;
    double energy_cost;
} IChingVM;

void vm_init(IChingVM *vm) {
    memset(vm, 0, sizeof(IChingVM));
    vm->state = VM_INIT;
    vm->registers[R_SP] = STACK_SIZE;
    vm->registers[R_FP] = STACK_SIZE;
}

void vm_load_program(IChingVM *vm, uint8_t *program, uint32_t len) {
    vm->program = program;
    vm->program_len = len;
    vm->pc = 0;
    vm->state = VM_INIT;
}

static inline uint8_t decode_opcode(uint8_t byte1) {
    return (byte1 >> 2) & 0x3F;
}

static inline uint8_t decode_modifier(uint8_t byte1, uint8_t byte2) {
    return ((byte1 & 0x03) << 4) | (byte2 & 0x0F);
}

typedef void (*OpHandler)(IChingVM*, uint8_t, uint8_t*);

/* 0: KUN - RECV */
static void op_recv(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    vm->registers[dst] = 0;
}

/* 1: FU - RETURN */
static void op_return(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    if (vm->registers[R_SP] < STACK_SIZE) {
        vm->pc = vm->stack[vm->registers[R_SP]];
        vm->registers[R_SP]++;
    } else {
        vm->state = VM_HALTED;
    }
}

/* 2: SHI - BRANCH */
static void op_branch(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    uint8_t cond = operands[0] & 0x0F;
    if (vm->registers[cond] != 0) {
        if (modifier & 0x10) {
            uint8_t target_reg = operands[1] & 0x0F;
            uint32_t target = vm->registers[target_reg];
            if (target < vm->program_len) {
                vm->pc = target;
            }
        } else {
            uint8_t target = operands[1];
            if (target < vm->program_len) {
                vm->pc = target;
            }
        }
    }
}

/* 3: LIN - APPROACH / AND */
static void op_approach(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t result = (vm->registers[dst] & vm->registers[src]) & 0xFFFFFFFF;
    vm->registers[dst] = result;
    vm->flag_zero = (result == 0);
    vm->flag_negative = (result & 0x80000000) != 0;
}

/* 4: QIANX - YIELD */
static void op_yield(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    vm->state = VM_PAUSED;
}

/* 5: MINGYI - OBSCURE */
static void op_obscure(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t val = vm->registers[src];
    val = ~val;
    vm->registers[dst] = val;
}

/* 6: SHENG - PUSH_UP */
static void op_push_up(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t reg = operands[0] & 0x0F;
    if (vm->registers[R_SP] > 0) {
        vm->registers[R_SP]--;
        vm->stack[vm->registers[R_SP]] = vm->registers[reg] & 0xFF;
    }
}

/* 7: TAI - FLUSH / SHR */
static void op_flush(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint8_t shift = vm->registers[src] & 0x1F;
    uint32_t result = (vm->registers[dst] >> shift) & 0xFFFFFFFF;
    vm->registers[dst] = result;
    vm->flag_zero = (result == 0);
    vm->flag_negative = (result & 0x80000000) != 0;
}

/* 8: YU - SPECULATE */
static void op_speculate(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

/* 9: ZHEN - SHOCK */
static void op_shock(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

/* 10: JIE - UNLOCK */
static void op_unlock(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint16_t lock_id = operands[0] & 0xFFFF;
    if (lock_id < MAX_LOCKS) {
        vm->locks[lock_id] = 0;
    }
}

/* 11: GUIMEI - MISMATCH */
static void op_mismatch(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    vm->state = VM_ERROR;
}

/* 12: XIAOGUO - MICRO */
static void op_micro(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t val = operands[1];
    vm->registers[dst] = (vm->registers[dst] + val) & 0xFFFFFFFF;
}

/* 13: FENG - ABOUND */
static void op_abound(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t count = operands[1];
    vm->registers[dst] = count;
}

/* 14: HENG - PERSIST */
static void op_persist(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

/* 15: DAZHUANG - THRUST */
static void op_thrust(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

/* 16: BI - MERGE / OR */
static void op_merge(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t result = (vm->registers[dst] | vm->registers[src]) & 0xFFFFFFFF;
    vm->registers[dst] = result;
    vm->flag_zero = (result == 0);
    vm->flag_negative = (result & 0x80000000) != 0;
}

/* 17: ZHUN - ALLOC */
static void op_alloc(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint32_t size = operands[1] > 0 ? operands[1] : 256;
    if (vm->heap_ptr + size <= HEAP_SIZE) {
        uint32_t addr = vm->heap_ptr + 1;
        vm->heap_ptr += size;
        vm->registers[dst] = addr;
    } else {
        vm->registers[dst] = 0;
        vm->flag_overflow = 1;
    }
}

/* 18: KAN - TRAP */
static void op_trap(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    vm->state = VM_TRAPPED;
}

/* 19: JIEX - THROTTLE */
static void op_throttle(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

/* 20: JIANX - LAME */
static void op_lame(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

/* 21: JIJI - SYNC */
static void op_sync(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t barrier_id = operands[0];
    if (barrier_id < MAX_BARRIERS) {
        vm->barriers[barrier_id]++;
    }
}

/* 22: JING - WELL */
static void op_well(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    if (vm->registers[R_SP] < STACK_SIZE) {
        vm->registers[dst] = vm->stack[vm->registers[R_SP]];
        vm->registers[R_SP]++;
    }
}

/* 23: XU - WAIT */
static void op_wait(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t cond = operands[0] & 0x0F;
    if (vm->registers[cond] == 0) {
        vm->pc -= 4;
    }
}

/* 24: CUI - GATHER */
static void op_gather(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t result = (vm->registers[dst] + vm->registers[src]) & 0xFFFFFFFF;
    vm->registers[dst] = result;
}

/* 25: SUI - FOLLOWING */
static void op_following(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

/* 26: KUNX - TRAPPED */
static void op_trapped(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    vm->state = VM_ERROR;
}

/* 27: DUI - JOY */
static void op_joy(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

/* 28: XIAN - SENSE */
static void op_sense(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

/* 29: GE - REPLACE */
static void op_replace(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

/* 30: DAGUO - OVERLOAD */
static void op_overload(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    vm->state = VM_ERROR;
}

/* 31: GUAI - BREAK */
static void op_break(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    vm->state = VM_HALTED;
}

/* 32: BO - STRIP */
static void op_strip(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src] & 0xFF;
}

/* 33: YI - NOURISH */
static void op_nourish(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    vm->heap_ptr = 0;
    memset(vm->heap, 0, HEAP_SIZE);
}

/* 34: MENG - SPRT */
static void op_sprt(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    vm->registers[dst] = 1;
}

/* 35: SUN - REDUCE */
static void op_reduce(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t result = (vm->registers[dst] - vm->registers[src]) & 0xFFFFFFFF;
    vm->registers[dst] = result;
    vm->flag_zero = (result == 0);
    vm->flag_negative = (result & 0x80000000) != 0;
}

/* 36: GEN - STILL */
static void op_still(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    vm->state = VM_PAUSED;
}

/* 37: BIX - ADORN / XOR */
static void op_adorn(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t result = (vm->registers[dst] ^ vm->registers[src]) & 0xFFFFFFFF;
    vm->registers[dst] = result;
    vm->flag_zero = (result == 0);
    vm->flag_negative = (result & 0x80000000) != 0;
}

/* 38: GU - MUT */
static void op_mut(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t target = operands[0] & 0x0F;
    uint8_t bit = operands[1] & 0x1F;
    uint32_t mask = 1 << bit;
    vm->registers[target] ^= mask;
}

/* 39: DAXU - BARRIER */
static void op_barrier(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

/* 40: JIN - ADVANCE */
static void op_advance(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t reg = operands[0] & 0x0F;
    vm->registers[reg] = (vm->registers[reg] + 1) & 0xFFFFFFFF;
}

/* 41: SHIHE - BITE */
static void op_bite(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t expected = operands[0];
    uint8_t actual_reg = operands[1] & 0x0F;
    if (vm->registers[actual_reg] != expected) {
        vm->state = VM_TRAPPED;
    }
}

/* 42: WEIJI - FUTU */
static void op_futu(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    vm->registers[dst] = vm->future_id_counter++;
}

/* 43: KUI - CONVERT */
static void op_convert(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

/* 44: LVX - TRAVEL */
static void op_travel(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

/* 45: LI - ILLUMINATE */
static void op_illuminate(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t reg = operands[0] & 0x0F;
    uint32_t val = vm->registers[reg];
    printf("%u", val);
}

/* 46: DING - CAST */
static void op_cast(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

/* 47: DAYOU - ABUNDANCE */
static void op_abundance(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t src_val = vm->registers[src];
    uint32_t addr = vm->registers[dst];
    if (addr < HEAP_SIZE) {
        vm->heap[addr] = src_val & 0xFF;
    }
}

/* 48: GUAN - CONTEMPLATE */
static void op_contemplate(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t reg = operands[0] & 0x0F;
    vm->registers[reg] = vm->cycle_count;
}

/* 49: YIX - INCREASE */
static void op_increase(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t result = (vm->registers[dst] + vm->registers[src]) & 0xFFFFFFFF;
    vm->registers[dst] = result;
    vm->flag_zero = (result == 0);
    vm->flag_negative = (result & 0x80000000) != 0;
}

/* 50: HUAN - DISPERSE */
static void op_disperse(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t addr_reg = operands[0] & 0x0F;
    uint8_t val_reg = operands[1] & 0x0F;
    uint32_t addr = vm->registers[addr_reg];
    uint32_t val = vm->registers[val_reg];
    if (addr < HEAP_SIZE) {
        vm->heap[addr] = val & 0xFF;
    }
}

/* 51: ZHONGFU - TRUST */
static void op_trust(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

/* 52: JIANJ - GRADUAL */
static void op_gradual(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t reg = operands[0] & 0x0F;
    vm->registers[reg] = (vm->registers[reg] + 1) & 0xFFFFFFFF;
}

/* 53: JIAREN - BIND */
static void op_bind(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

/* 54: XUN - PENETRATE */
static void op_penetrate(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t addr_reg = operands[0] & 0x0F;
    uint8_t dst = operands[1] & 0x0F;
    uint32_t addr = vm->registers[addr_reg];
    if (addr < HEAP_SIZE) {
        vm->registers[dst] = vm->heap[addr];
    }
}

/* 55: XIAOXU - PREFETCH / SHL */
static void op_prefetch(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint8_t shift = vm->registers[src] & 0x1F;
    uint32_t result = (vm->registers[dst] << shift) & 0xFFFFFFFF;
    vm->registers[dst] = result;
    vm->flag_zero = (result == 0);
    vm->flag_negative = (result & 0x80000000) != 0;
}

/* 56: PI - HALT */
static void op_halt(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    vm->state = VM_HALTED;
}

/* 57: WUWANG - INTRINSIC */
static void op_intrinsic(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

/* 58: SONG - LOCK */
static void op_lock(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint16_t lock_id = operands[0] & 0xFFFF;
    if (lock_id < MAX_LOCKS && vm->locks[lock_id]) {
        vm->pc -= 4;
    } else if (lock_id < MAX_LOCKS) {
        vm->locks[lock_id] = 1;
    }
}

/* 59: LV - STEP */
static void op_step(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t reg = operands[0] & 0x0F;
    vm->registers[reg] = (vm->registers[reg] + 1) & 0xFFFFFFFF;
}

/* 60: DUN - RETREAT */
static void op_retreat(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    vm->state = VM_HALTED;
}

/* 61: TONGREN - FELLOWSHIP */
static void op_fellowship(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

/* 62: GOU - MATE */
static void op_mate(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t result = ((vm->registers[dst] + vm->registers[src]) / 2) & 0xFFFFFFFF;
    vm->registers[dst] = result;
}

/* 63: QIAN - CREA */
static void op_crea(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    static uint32_t thread_id = 1;
    vm->registers[dst] = thread_id++;
    vm->energy_cost += 10.0;
}

/* 指令表 - 按操作码 0-63 顺序 */
static OpHandler opcode_handlers[64] = {
    op_recv,        /* 00: KUN - RECV */
    op_return,      /* 01: FU - RETURN */
    op_branch,      /* 02: SHI - BRANCH */
    op_approach,    /* 03: LIN - APPROACH (AND) */
    op_yield,       /* 04: QIANX - YIELD */
    op_obscure,     /* 05: MINGYI - OBSCURE */
    op_push_up,     /* 06: SHENG - PUSH_UP */
    op_flush,       /* 07: TAI - FLUSH (SHR) */
    op_speculate,   /* 08: YU - SPECULATE */
    op_shock,       /* 09: ZHEN - SHOCK */
    op_unlock,      /* 10: JIE - UNLOCK */
    op_mismatch,    /* 11: GUIMEI - MISMATCH */
    op_micro,       /* 12: XIAOGUO - MICRO */
    op_abound,      /* 13: FENG - ABOUND */
    op_persist,     /* 14: HENG - PERSIST */
    op_thrust,      /* 15: DAZHUANG - THRUST */
    op_merge,       /* 16: BI - MERGE (OR) */
    op_alloc,       /* 17: ZHUN - ALLOC */
    op_trap,        /* 18: KAN - TRAP */
    op_throttle,    /* 19: JIEX - THROTTLE */
    op_lame,        /* 20: JIANX - LAME */
    op_sync,        /* 21: JIJI - SYNC */
    op_well,        /* 22: JING - WELL */
    op_wait,        /* 23: XU - WAIT */
    op_gather,      /* 24: CUI - GATHER */
    op_following,   /* 25: SUI - FOLLOWING */
    op_trapped,     /* 26: KUNX - TRAPPED */
    op_joy,         /* 27: DUI - JOY */
    op_sense,       /* 28: XIAN - SENSE */
    op_replace,     /* 29: GE - REPLACE */
    op_overload,    /* 30: DAGUO - OVERLOAD */
    op_break,       /* 31: GUAI - BREAK */
    op_strip,       /* 32: BO - STRIP */
    op_nourish,     /* 33: YI - NOURISH */
    op_sprt,        /* 34: MENG - SPRT */
    op_reduce,      /* 35: SUN - REDUCE */
    op_still,       /* 36: GEN - STILL */
    op_adorn,       /* 37: BIX - ADORN (XOR) */
    op_mut,         /* 38: GU - MUT */
    op_barrier,     /* 39: DAXU - BARRIER */
    op_advance,     /* 40: JIN - ADVANCE */
    op_bite,        /* 41: SHIHE - BITE */
    op_futu,        /* 42: WEIJI - FUTU */
    op_convert,     /* 43: KUI - CONVERT */
    op_travel,      /* 44: LVX - TRAVEL */
    op_illuminate,  /* 45: LI - ILLUMINATE */
    op_cast,        /* 46: DING - CAST */
    op_abundance,   /* 47: DAYOU - ABUNDANCE */
    op_contemplate, /* 48: GUAN - CONTEMPLATE */
    op_increase,    /* 49: YIX - INCREASE */
    op_disperse,    /* 50: HUAN - DISPERSE */
    op_trust,       /* 51: ZHONGFU - TRUST */
    op_gradual,     /* 52: JIANJ - GRADUAL */
    op_bind,        /* 53: JIAREN - BIND */
    op_penetrate,   /* 54: XUN - PENETRATE */
    op_prefetch,    /* 55: XIAOXU - PREFETCH (SHL) */
    op_halt,        /* 56: PI - HALT */
    op_intrinsic,   /* 57: WUWANG - INTRINSIC */
    op_lock,        /* 58: SONG - LOCK */
    op_step,        /* 59: LV - STEP */
    op_retreat,     /* 60: DUN - RETREAT */
    op_fellowship,  /* 61: TONGREN - FELLOWSHIP */
    op_mate,        /* 62: GOU - MATE */
    op_crea,        /* 63: QIAN - CREA */
};

VMState vm_run(IChingVM *vm, uint32_t max_cycles) {
    vm->state = VM_RUNNING;
    
    if (max_cycles == 0) {
        max_cycles = 1000000;
    }
    
    uint32_t cycles_remaining = max_cycles;
    
    while (vm->state == VM_RUNNING && cycles_remaining > 0) {
        if (vm->pc + 3 >= vm->program_len) {
            vm->state = VM_HALTED;
            break;
        }
        
        uint8_t byte1 = vm->program[vm->pc];
        uint8_t byte2 = vm->program[vm->pc + 1];
        uint8_t operand1 = vm->program[vm->pc + 2];
        uint8_t operand2 = vm->program[vm->pc + 3];
        
        uint8_t opcode = decode_opcode(byte1);
        uint8_t modifier = decode_modifier(byte1, byte2);
        uint8_t operands[2] = {operand1, operand2};
        
        vm->pc += 4;
        
        if (opcode < 64 && opcode_handlers[opcode]) {
            opcode_handlers[opcode](vm, modifier, operands);
        } else {
            vm->state = VM_ERROR;
            break;
        }
        
        vm->cycle_count++;
        cycles_remaining--;
    }
    
    return vm->state;
}

uint8_t* vm_read_raw_file(const char *filename, uint32_t *out_size) {
    FILE *f = fopen(filename, "rb");
    if (!f) {
        return NULL;
    }
    
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    
    uint8_t *code = (uint8_t*)malloc(size);
    if (!code) {
        fclose(f);
        return NULL;
    }
    
    if (fread(code, 1, size, f) != (size_t)size) {
        free(code);
        fclose(f);
        return NULL;
    }
    
    fclose(f);
    *out_size = (uint32_t)size;
    return code;
}

void vm_dump_state(IChingVM *vm) {
    printf("\n=== VM State ===\n");
    printf("PC: 0x%08X\n", vm->pc);
    printf("State: %d\n", vm->state);
    printf("Cycles: %llu\n", vm->cycle_count);
    printf("Energy: %.2f\n", vm->energy_cost);
    printf("\nRegisters:\n");
    for (int i = 0; i < NUM_REGISTERS; i++) {
        printf("  R%d: 0x%08X (%u)", i, vm->registers[i], vm->registers[i]);
        if (i == R_FP) printf(" [FP]");
        if (i == R_SP) printf(" [SP]");
        if (i == R_LR) printf(" [LR]");
        if (i == R_A0) printf(" [A0]");
        printf("\n");
    }
    printf("\nFlags:\n");
    printf("  Zero: %d, Carry: %d, Negative: %d, Overflow: %d\n",
           vm->flag_zero, vm->flag_carry, vm->flag_negative, vm->flag_overflow);
    printf("================\n\n");
}

typedef struct {
    const char *mnemonic;
    uint8_t opcode;
} MnemonicMap;

static MnemonicMap mnemonic_map[] = {
    {"CREA", 63}, {"RECV", 0}, {"ALLOC", 17}, {"SPRT", 34},
    {"WAIT", 23}, {"LOCK", 58}, {"BRANCH", 2}, {"MERGE", 16},
    {"SHL", 55}, {"PREFETCH", 55}, {"STEP", 59}, {"SHR", 7},
    {"FLUSH", 7}, {"HALT", 56}, {"FELLOWSHIP", 61}, {"ABUNDANCE", 47},
    {"YIELD", 4}, {"SPECULATE", 8}, {"FOLLOWING", 25}, {"MUT", 38},
    {"AND", 3}, {"APPROACH", 3}, {"CONTEMPLATE", 48}, {"BITE", 41},
    {"XOR", 37}, {"ADORN", 37}, {"STRIP", 32}, {"RETURN", 1},
    {"INTRINSIC", 57}, {"BARRIER", 39}, {"NOURISH", 33}, {"OVERLOAD", 30},
    {"TRAP", 18}, {"ILLUMINATE", 45}, {"SENSE", 28}, {"PERSIST", 14},
    {"RETREAT", 60}, {"THRUST", 15}, {"ADVANCE", 40}, {"OBSCURE", 5},
    {"BIND", 53}, {"CONVERT", 43}, {"LAME", 20}, {"UNLOCK", 10},
    {"REDUCE", 35}, {"INCREASE", 49}, {"BREAK", 31}, {"MATE", 62},
    {"GATHER", 24}, {"PUSH_UP", 6}, {"TRAPPED", 26}, {"WELL", 22},
    {"REPLACE", 29}, {"CAST", 46}, {"SHOCK", 9}, {"STILL", 36},
    {"GRADUAL", 52}, {"MISMATCH", 11}, {"ABOUND", 13}, {"TRAVEL", 44},
    {"PENETRATE", 54}, {"JOY", 27}, {"DISPERSE", 50}, {"THROTTLE", 19},
    {"TRUST", 51}, {"MICRO", 12}, {"SYNC", 21}, {"FUTU", 42},
    {"OR", 16},
    {NULL, 0}
};

static uint8_t find_opcode(const char *mnemonic) {
    for (int i = 0; mnemonic_map[i].mnemonic != NULL; i++) {
        if (strcasecmp(mnemonic_map[i].mnemonic, mnemonic) == 0) {
            return mnemonic_map[i].opcode;
        }
    }
    return 0xFF;
}

static char* skip_whitespace(char *p) {
    while (*p && isspace(*p)) p++;
    return p;
}

static char* read_token(char *p, char *buf, int bufsize) {
    int i = 0;
    p = skip_whitespace(p);
    while (*p && !isspace(*p) && *p != ',' && *p != ';' && *p != '#' && i < bufsize - 1) {
        buf[i++] = *p++;
    }
    buf[i] = '\0';
    return p;
}

static int is_register(const char *token) {
    if (token[0] == 'R' || token[0] == 'r') {
        int r = atoi(token + 1);
        if (r >= 0 && r <= 15) return 1;
    }
    return 0;
}

static int parse_register(const char *token) {
    if (token[0] == 'R' || token[0] == 'r') {
        return atoi(token + 1);
    }
    return 0;
}

static uint32_t parse_number(const char *token) {
    if (strncmp(token, "0x", 2) == 0 || strncmp(token, "0X", 2) == 0) {
        return (uint32_t)strtoul(token, NULL, 16);
    } else if (token[0] == '0') {
        return (uint32_t)strtoul(token, NULL, 8);
    } else {
        return (uint32_t)atoi(token);
    }
}

int assemble_file(const char *input_file, const char *output_file) {
    FILE *fin = fopen(input_file, "r");
    if (!fin) {
        fprintf(stderr, "Error: Cannot open input file %s\n", input_file);
        return -1;
    }
    
    uint8_t *code = (uint8_t*)malloc(65536);
    int code_len = 0;
    char line[1024];
    
    while (fgets(line, sizeof(line), fin)) {
        char *p = line;
        char token[256];
        
        p = skip_whitespace(p);
        if (*p == '\0' || *p == ';' || *p == '#') continue;
        
        p = read_token(p, token, sizeof(token));
        if (token[0] == '\0') continue;
        
        uint8_t opcode = find_opcode(token);
        if (opcode == 0xFF) {
            fprintf(stderr, "Warning: Unknown mnemonic '%s'\n", token);
            continue;
        }
        
        uint8_t modifier = 0;
        uint8_t operands[2] = {0, 0};
        int op_count = 0;
        
        while (1) {
            p = skip_whitespace(p);
            if (*p == '\0' || *p == ';' || *p == '#') break;
            
            if (*p == ',') {
                p++;
                continue;
            }
            
            p = read_token(p, token, sizeof(token));
            if (token[0] == '\0') break;
            
            if (is_register(token)) {
                operands[op_count] = parse_register(token) & 0x0F;
            } else {
                operands[op_count] = parse_number(token) & 0xFF;
            }
            op_count++;
            if (op_count >= 2) break;
        }
        
        uint8_t byte1 = (opcode << 2) | ((modifier >> 4) & 0x03);
        uint8_t byte2 = modifier & 0x0F;
        
        code[code_len++] = byte1;
        code[code_len++] = byte2;
        code[code_len++] = operands[0];
        code[code_len++] = operands[1];
        
        if (code_len >= 65536) {
            fprintf(stderr, "Error: Code too large\n");
            fclose(fin);
            free(code);
            return -1;
        }
    }
    
    fclose(fin);
    
    FILE *fout = fopen(output_file, "wb");
    if (!fout) {
        fprintf(stderr, "Error: Cannot open output file %s\n", output_file);
        free(code);
        return -1;
    }
    
    fwrite(code, 1, code_len, fout);
    fclose(fout);
    free(code);
    
    printf("Assembled: %d bytes\n", code_len);
    return 0;
}

void print_usage(const char *prog) {
    printf("Usage: %s <command> [options]\n", prog);
    printf("\nCommands:\n");
    printf("  run <program.raw> [max_cycles]  - Run raw bytecode\n");
    printf("  asm <input.asm> <output.raw>     - Assemble text to bytecode\n");
    printf("  help                              - Show this help\n");
    printf("\nIChingVM - 易衍虚拟机 C 语言实现\n");
    printf("六十四卦指令集解释器 - 用于自举\n");
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        print_usage(argv[0]);
        return 1;
    }
    
    const char *cmd = argv[1];
    
    if (strcmp(cmd, "help") == 0 || strcmp(cmd, "-h") == 0 || strcmp(cmd, "--help") == 0) {
        print_usage(argv[0]);
        return 0;
    }
    
    if (strcmp(cmd, "asm") == 0) {
        if (argc < 4) {
            fprintf(stderr, "Usage: %s asm <input.asm> <output.raw>\n", argv[0]);
            return 1;
        }
        return assemble_file(argv[2], argv[3]) == 0 ? 0 : 1;
    }
    
    if (strcmp(cmd, "run") == 0) {
        if (argc < 3) {
            fprintf(stderr, "Usage: %s run <program.raw> [max_cycles]\n", argv[0]);
            return 1;
        }
        
        const char *filename = argv[2];
        uint32_t max_cycles = 1000000;
        
        if (argc >= 4) {
            max_cycles = (uint32_t)atoi(argv[3]);
        }
        
        uint32_t program_size;
        uint8_t *program = vm_read_raw_file(filename, &program_size);
        
        if (!program) {
            fprintf(stderr, "Error: Cannot load program %s\n", filename);
            return 1;
        }
        printf("Loaded raw bytecode: %u bytes\n", program_size);
        
        IChingVM vm;
        vm_init(&vm);
        vm_load_program(&vm, program, program_size);
        
        printf("\nRunning program...\n");
        VMState state = vm_run(&vm, max_cycles);
        
        printf("\nProgram finished with state: ");
        switch (state) {
            case VM_INIT: printf("INIT"); break;
            case VM_RUNNING: printf("RUNNING"); break;
            case VM_PAUSED: printf("PAUSED"); break;
            case VM_HALTED: printf("HALTED"); break;
            case VM_ERROR: printf("ERROR"); break;
            case VM_TRAPPED: printf("TRAPPED"); break;
        }
        printf("\n");
        
        vm_dump_state(&vm);
        
        free(program);
        return 0;
    }
    
    /* 旧版兼容：直接运行文件 */
    const char *filename = argv[1];
    uint32_t max_cycles = 1000000;
    
    if (argc >= 3) {
        max_cycles = (uint32_t)atoi(argv[2]);
    }
    
    uint32_t program_size;
    uint8_t *program = vm_read_raw_file(filename, &program_size);
    
    if (!program) {
        fprintf(stderr, "Error: Cannot load program %s\n", filename);
        return 1;
    }
    printf("Loaded raw bytecode: %u bytes\n", program_size);
    
    IChingVM vm;
    vm_init(&vm);
    vm_load_program(&vm, program, program_size);
    
    printf("\nRunning program...\n");
    VMState state = vm_run(&vm, max_cycles);
    
    printf("\nProgram finished with state: ");
    switch (state) {
        case VM_INIT: printf("INIT"); break;
        case VM_RUNNING: printf("RUNNING"); break;
        case VM_PAUSED: printf("PAUSED"); break;
        case VM_HALTED: printf("HALTED"); break;
        case VM_ERROR: printf("ERROR"); break;
        case VM_TRAPPED: printf("TRAPPED"); break;
    }
    printf("\n");
    
    vm_dump_state(&vm);
    
    free(program);
    return 0;
}
