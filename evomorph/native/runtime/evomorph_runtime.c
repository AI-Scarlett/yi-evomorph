/*
 * Evomorph 原生运行时实现
 * 基于六十四卦指令集的进化编程运行时
 */

#include "evomorph_runtime.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <math.h>
#include <limits.h>
#include <time.h>

#if defined(EVO_POSIX)
#include <sys/stat.h>
#endif

/* 操作码解码器 */
#define DECODE_OPCODE(byte1) (((byte1) >> 2) & 0x3F)
#define DECODE_MODIFIER(byte1, byte2) (((byte1 & 0x03) << 4) | (byte2 & 0x0F))

/* 版本字符串 */
static const char* g_version_string = "Evomorph Runtime 3.0.0";

/* 操作码处理器函数声明 */
static void op_recv(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_return(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_branch(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_approach(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_yield(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_obscure(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_push_up(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_flush(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_speculate(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_shock(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_unlock(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_mismatch(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_micro(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_abound(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_persist(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_thrust(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_merge(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_alloc(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_trap(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_throttle(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_lame(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_sync(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_well(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_wait(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_gather(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_following(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_trapped(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_joy(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_sense(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_replace(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_overload(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_break(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_strip(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_nourish(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_sprt(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_reduce(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_still(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_adorn(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_mut(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_barrier(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_advance(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_bite(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_futu(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_convert(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_travel(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_illuminate(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_cast(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_abundance(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_contemplate(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_increase(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_disperse(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_trust(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_gradual(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_bind(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_penetrate(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_prefetch(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_halt(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_intrinsic(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_lock(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_step(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_retreat(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_fellowship(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_mate(EvoVM* vm, uint8_t modifier, uint8_t* operands);
static void op_crea(EvoVM* vm, uint8_t modifier, uint8_t* operands);

/* 操作码处理器表 */
static EvoOpHandler g_opcode_handlers[64] = {
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

/* 辅助函数：设置标志位 */
static void set_flags(EvoVM* vm, uint32_t result) {
    vm->flag_zero = (result == 0);
    vm->flag_negative = (result & 0x80000000) != 0;
}

/* 操作码实现 */
static void op_recv(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    vm->registers[dst] = 0;
}

static void op_return(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    (void)operands;
    if (vm->registers[EVO_R_SP] < EVO_STACK_SIZE) {
        vm->pc = vm->stack[vm->registers[EVO_R_SP]];
        vm->registers[EVO_R_SP]++;
    } else {
        vm->state = EVO_VM_HALTED;
    }
}

static void op_branch(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
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

static void op_approach(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t result = (vm->registers[dst] & vm->registers[src]) & 0xFFFFFFFF;
    vm->registers[dst] = result;
    set_flags(vm, result);
}

static void op_yield(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    (void)operands;
    vm->state = EVO_VM_PAUSED;
}

static void op_obscure(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t val = vm->registers[src];
    val = ~val;
    vm->registers[dst] = val;
}

static void op_push_up(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t reg = operands[0] & 0x0F;
    if (vm->registers[EVO_R_SP] > 0) {
        vm->registers[EVO_R_SP]--;
        vm->stack[vm->registers[EVO_R_SP]] = vm->registers[reg] & 0xFF;
    }
}

static void op_flush(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint8_t shift = vm->registers[src] & 0x1F;
    uint32_t result = (vm->registers[dst] >> shift) & 0xFFFFFFFF;
    vm->registers[dst] = result;
    set_flags(vm, result);
}

static void op_speculate(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

static void op_shock(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

static void op_unlock(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint16_t lock_id = operands[0] & 0xFFFF;
    if (lock_id < EVO_MAX_LOCKS) {
        vm->locks[lock_id] = 0;
    }
}

static void op_mismatch(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    (void)operands;
    vm->state = EVO_VM_ERROR;
}

static void op_micro(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t val = operands[1];
    vm->registers[dst] = (vm->registers[dst] + val) & 0xFFFFFFFF;
}

static void op_abound(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t count = operands[1];
    vm->registers[dst] = count;
}

static void op_persist(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

static void op_thrust(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

static void op_merge(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t result = (vm->registers[dst] | vm->registers[src]) & 0xFFFFFFFF;
    vm->registers[dst] = result;
    set_flags(vm, result);
}

static void op_alloc(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint32_t size = operands[1] > 0 ? operands[1] : 256;
    if (vm->heap_ptr + size <= EVO_HEAP_SIZE) {
        uint32_t addr = vm->heap_ptr + 1;
        vm->heap_ptr += size;
        vm->registers[dst] = addr;
    } else {
        vm->registers[dst] = 0;
        vm->flag_overflow = 1;
    }
}

static void op_trap(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    (void)operands;
    vm->state = EVO_VM_TRAPPED;
}

static void op_throttle(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

static void op_lame(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

static void op_sync(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t barrier_id = operands[0];
    if ((size_t)barrier_id < EVO_MAX_BARRIERS) {
        vm->barriers[barrier_id]++;
    }
}

static void op_well(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    if (vm->registers[EVO_R_SP] < EVO_STACK_SIZE) {
        vm->registers[dst] = vm->stack[vm->registers[EVO_R_SP]];
        vm->registers[EVO_R_SP]++;
    }
}

static void op_wait(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t cond = operands[0] & 0x0F;
    if (vm->registers[cond] == 0) {
        vm->pc -= 4;
    }
}

static void op_gather(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t result = (vm->registers[dst] + vm->registers[src]) & 0xFFFFFFFF;
    vm->registers[dst] = result;
}

static void op_following(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

static void op_trapped(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    (void)operands;
    vm->state = EVO_VM_ERROR;
}

static void op_joy(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

static void op_sense(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

static void op_replace(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

static void op_overload(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    (void)operands;
    vm->state = EVO_VM_ERROR;
}

static void op_break(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    (void)operands;
    vm->state = EVO_VM_HALTED;
}

static void op_strip(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src] & 0xFF;
}

static void op_nourish(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    (void)operands;
    vm->heap_ptr = 0;
    memset(vm->heap, 0, EVO_HEAP_SIZE);
}

static void op_sprt(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    vm->registers[dst] = 1;
}

static void op_reduce(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t result = (vm->registers[dst] - vm->registers[src]) & 0xFFFFFFFF;
    vm->registers[dst] = result;
    set_flags(vm, result);
}

static void op_still(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    (void)operands;
    vm->state = EVO_VM_PAUSED;
}

static void op_adorn(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t result = (vm->registers[dst] ^ vm->registers[src]) & 0xFFFFFFFF;
    vm->registers[dst] = result;
    set_flags(vm, result);
}

static void op_mut(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t target = operands[0] & 0x0F;
    uint8_t bit = operands[1] & 0x1F;
    uint32_t mask = 1 << bit;
    vm->registers[target] ^= mask;
}

static void op_barrier(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

static void op_advance(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t reg = operands[0] & 0x0F;
    vm->registers[reg] = (vm->registers[reg] + 1) & 0xFFFFFFFF;
}

static void op_bite(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t expected = operands[0];
    uint8_t actual_reg = operands[1] & 0x0F;
    if (vm->registers[actual_reg] != expected) {
        vm->state = EVO_VM_TRAPPED;
    }
}

static void op_futu(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    vm->registers[dst] = vm->future_id_counter++;
}

static void op_convert(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

static void op_travel(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

static void op_illuminate(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t reg = operands[0] & 0x0F;
    uint32_t val = vm->registers[reg];
    printf("%u", val);
}

static void op_cast(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

static void op_abundance(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t src_val = vm->registers[src];
    uint32_t addr = vm->registers[dst];
    if (addr < EVO_HEAP_SIZE) {
        vm->heap[addr] = src_val & 0xFF;
    }
}

static void op_contemplate(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t reg = operands[0] & 0x0F;
    vm->registers[reg] = (uint32_t)vm->cycle_count;
}

static void op_increase(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t result = (vm->registers[dst] + vm->registers[src]) & 0xFFFFFFFF;
    vm->registers[dst] = result;
    set_flags(vm, result);
}

static void op_disperse(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t addr_reg = operands[0] & 0x0F;
    uint8_t val_reg = operands[1] & 0x0F;
    uint32_t addr = vm->registers[addr_reg];
    uint32_t val = vm->registers[val_reg];
    if (addr < EVO_HEAP_SIZE) {
        vm->heap[addr] = val & 0xFF;
    }
}

static void op_trust(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

static void op_gradual(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t reg = operands[0] & 0x0F;
    vm->registers[reg] = (vm->registers[reg] + 1) & 0xFFFFFFFF;
}

static void op_bind(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

static void op_penetrate(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t addr_reg = operands[0] & 0x0F;
    uint8_t dst = operands[1] & 0x0F;
    uint32_t addr = vm->registers[addr_reg];
    if (addr < EVO_HEAP_SIZE) {
        vm->registers[dst] = vm->heap[addr];
    }
}

static void op_prefetch(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint8_t shift = vm->registers[src] & 0x1F;
    uint32_t result = (vm->registers[dst] << shift) & 0xFFFFFFFF;
    vm->registers[dst] = result;
    set_flags(vm, result);
}

static void op_halt(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    (void)operands;
    vm->state = EVO_VM_HALTED;
}

static void op_intrinsic(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

static void op_lock(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint16_t lock_id = operands[0] & 0xFFFF;
    if (lock_id < EVO_MAX_LOCKS && vm->locks[lock_id]) {
        vm->pc -= 4;
    } else if (lock_id < EVO_MAX_LOCKS) {
        vm->locks[lock_id] = 1;
    }
}

static void op_step(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t reg = operands[0] & 0x0F;
    vm->registers[reg] = (vm->registers[reg] + 1) & 0xFFFFFFFF;
}

static void op_retreat(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    (void)operands;
    vm->state = EVO_VM_HALTED;
}

static void op_fellowship(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

static void op_mate(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t result = ((vm->registers[dst] + vm->registers[src]) / 2) & 0xFFFFFFFF;
    vm->registers[dst] = result;
}

static void op_crea(EvoVM* vm, uint8_t modifier, uint8_t* operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    static uint32_t thread_id = 1;
    vm->registers[dst] = thread_id++;
    vm->energy_cost += 10.0;
}

/* 虚拟机API实现 */
EVO_API EvoVM* evo_vm_create(void) {
    EvoVM* vm = (EvoVM*)malloc(sizeof(EvoVM));
    if (!vm) return NULL;
    
    vm->stack = (uint8_t*)malloc(EVO_STACK_SIZE);
    vm->heap = (uint8_t*)malloc(EVO_HEAP_SIZE);
    vm->program = NULL;
    
    if (!vm->stack || !vm->heap) {
        free(vm->stack);
        free(vm->heap);
        free(vm);
        return NULL;
    }
    
    evo_vm_init(vm);
    return vm;
}

EVO_API void evo_vm_destroy(EvoVM* vm) {
    if (!vm) return;
    
    free(vm->stack);
    free(vm->heap);
    if (vm->program) {
        free(vm->program);
    }
    if (vm->population) {
        evo_population_destroy(vm->population);
    }
    if (vm->evo_config) {
        evo_config_destroy(vm->evo_config);
    }
    if (vm->best_ever) {
        evo_individual_destroy(vm->best_ever);
    }
    
    free(vm);
}

EVO_API void evo_vm_init(EvoVM* vm) {
    if (!vm) return;
    
    memset(vm->registers, 0, sizeof(vm->registers));
    memset(vm->stack, 0, EVO_STACK_SIZE);
    memset(vm->heap, 0, EVO_HEAP_SIZE);
    
    vm->heap_ptr = 0;
    vm->pc = 0;
    vm->state = EVO_VM_INIT;
    vm->program_len = 0;
    
    vm->flag_zero = 0;
    vm->flag_carry = 0;
    vm->flag_negative = 0;
    vm->flag_overflow = 0;
    
    vm->future_id_counter = 0;
    memset(vm->locks, 0, sizeof(vm->locks));
    memset(vm->barriers, 0, sizeof(vm->barriers));
    memset(vm->futures, 0, sizeof(vm->futures));
    
    vm->cycle_count = 0;
    vm->energy_cost = 0.0;
    
    vm->population = NULL;
    vm->evo_config = NULL;
    vm->current_generation = 0;
    vm->best_ever = NULL;
    
    /* 初始化RNG */
    vm->rng_state[0] = (uint64_t)time(NULL);
    vm->rng_state[1] = (uint64_t)clock();
    
    /* 设置特殊寄存器 */
    vm->registers[EVO_R_SP] = EVO_STACK_SIZE;
    vm->registers[EVO_R_FP] = EVO_STACK_SIZE;
}

EVO_API void evo_vm_reset(EvoVM* vm) {
    evo_vm_init(vm);
}

EVO_API EvoError evo_vm_load_program(EvoVM* vm, const uint8_t* program, uint32_t len) {
    if (!vm || !program) return EVO_ERROR_INVALID_ARG;
    
    if (vm->program) {
        free(vm->program);
    }
    
    vm->program = (uint8_t*)malloc(len);
    if (!vm->program) return EVO_ERROR_OUT_OF_MEMORY;
    
    memcpy(vm->program, program, len);
    vm->program_len = len;
    vm->pc = 0;
    vm->state = EVO_VM_INIT;
    
    return EVO_OK;
}

EVO_API EvoVMState evo_vm_run(EvoVM* vm, uint64_t max_cycles) {
    if (!vm) return EVO_VM_ERROR;
    
    vm->state = EVO_VM_RUNNING;
    
    if (max_cycles == 0) {
        max_cycles = 1000000;
    }
    
    uint64_t cycles_remaining = max_cycles;
    
    while (vm->state == EVO_VM_RUNNING && cycles_remaining > 0) {
        if (vm->pc + 3 >= vm->program_len) {
            vm->state = EVO_VM_HALTED;
            break;
        }
        
        uint8_t byte1 = vm->program[vm->pc];
        uint8_t byte2 = vm->program[vm->pc + 1];
        uint8_t operand1 = vm->program[vm->pc + 2];
        uint8_t operand2 = vm->program[vm->pc + 3];
        
        uint8_t opcode = DECODE_OPCODE(byte1);
        uint8_t modifier = DECODE_MODIFIER(byte1, byte2);
        uint8_t operands[2] = {operand1, operand2};
        
        vm->pc += 4;
        
        if (opcode < 64 && g_opcode_handlers[opcode]) {
            g_opcode_handlers[opcode](vm, modifier, operands);
        } else {
            vm->state = EVO_VM_ERROR;
            break;
        }
        
        vm->cycle_count++;
        cycles_remaining--;
    }
    
    return vm->state;
}

EVO_API void evo_vm_step(EvoVM* vm) {
    if (!vm || vm->state == EVO_VM_HALTED || vm->state == EVO_VM_ERROR) {
        return;
    }
    
    if (vm->pc + 3 >= vm->program_len) {
        vm->state = EVO_VM_HALTED;
        return;
    }
    
    uint8_t byte1 = vm->program[vm->pc];
    uint8_t byte2 = vm->program[vm->pc + 1];
    uint8_t operand1 = vm->program[vm->pc + 2];
    uint8_t operand2 = vm->program[vm->pc + 3];
    
    uint8_t opcode = DECODE_OPCODE(byte1);
    uint8_t modifier = DECODE_MODIFIER(byte1, byte2);
    uint8_t operands[2] = {operand1, operand2};
    
    vm->pc += 4;
    vm->state = EVO_VM_RUNNING;
    
    if (opcode < 64 && g_opcode_handlers[opcode]) {
        g_opcode_handlers[opcode](vm, modifier, operands);
    } else {
        vm->state = EVO_VM_ERROR;
    }
    
    vm->cycle_count++;
}

EVO_API void evo_vm_dump_state(const EvoVM* vm) {
    if (!vm) return;
    
    printf("\n=== EvoVM State ===\n");
    printf("PC: 0x%08X\n", vm->pc);
    printf("State: %d\n", vm->state);
    printf("Cycles: %llu\n", (unsigned long long)vm->cycle_count);
    printf("Energy: %.2f\n", vm->energy_cost);
    
    printf("\nRegisters:\n");
    for (int i = 0; i < EVO_NUM_REGISTERS; i++) {
        printf("  R%d: 0x%08X (%u)", i, vm->registers[i], vm->registers[i]);
        if (i == EVO_R_FP) printf(" [FP]");
        if (i == EVO_R_SP) printf(" [SP]");
        if (i == EVO_R_LR) printf(" [LR]");
        if (i == EVO_R_A0) printf(" [A0]");
        printf("\n");
    }
    
    printf("\nFlags:\n");
    printf("  Zero: %d, Carry: %d, Negative: %d, Overflow: %d\n",
           vm->flag_zero, vm->flag_carry, vm->flag_negative, vm->flag_overflow);
    
    printf("================\n\n");
}

/* 进化引擎API实现 */
EVO_API EvoEvolutionConfig* evo_config_create(void) {
    EvoEvolutionConfig* config = (EvoEvolutionConfig*)malloc(sizeof(EvoEvolutionConfig));
    if (!config) return NULL;
    
    config->population_size = 64;
    config->max_generations = 100;
    config->mut_rate = 0.02;
    config->crossover_rate = 0.7;
    config->elite_count = 2;
    config->selection_method = EVO_SELECT_TOURNAMENT;
    config->crossover_method = EVO_CROSS_SINGLE_POINT;
    config->tournament_size = 5;
    
    /* 默认适应度权重 */
    config->fitness_weights[0] = 1.0;  /* min_latency */
    config->fitness_weights[1] = 2.0;  /* max_throughput */
    config->fitness_weights[2] = 0.5;  /* min_energy */
    config->fitness_weights[3] = 0.3;  /* min_size */
    
    config->env_targets = NULL;
    config->num_env_targets = 0;
    config->cross_pool = NULL;
    
    return config;
}

EVO_API void evo_config_destroy(EvoEvolutionConfig* config) {
    if (!config) return;
    
    if (config->env_targets) {
        for (size_t i = 0; i < config->num_env_targets; i++) {
            free(config->env_targets[i]);
        }
        free(config->env_targets);
    }
    free(config->cross_pool);
    free(config);
}

EVO_API EvoPopulation* evo_population_create(size_t capacity) {
    if (capacity == 0) capacity = 64;
    
    EvoPopulation* pop = (EvoPopulation*)malloc(sizeof(EvoPopulation));
    if (!pop) return NULL;
    
    pop->individuals = (EvoIndividual*)malloc(capacity * sizeof(EvoIndividual));
    if (!pop->individuals) {
        free(pop);
        return NULL;
    }
    
    memset(pop->individuals, 0, capacity * sizeof(EvoIndividual));
    pop->size = 0;
    pop->capacity = capacity;
    
    return pop;
}

EVO_API void evo_population_destroy(EvoPopulation* pop) {
    if (!pop) return;
    
    for (size_t i = 0; i < pop->size; i++) {
        evo_individual_destroy(&pop->individuals[i]);
    }
    free(pop->individuals);
    free(pop);
}

EVO_API EvoIndividual* evo_individual_create(size_t num_genes) {
    EvoIndividual* ind = (EvoIndividual*)malloc(sizeof(EvoIndividual));
    if (!ind) return NULL;
    
    ind->genes = NULL;
    ind->num_genes = 0;
    ind->fitness = 0.0;
    ind->age = 0;
    ind->origin = 0;
    ind->platform_scores = NULL;
    ind->num_platforms = 0;
    
    if (num_genes > 0) {
        ind->genes = (EvoGeneInstruction*)malloc(num_genes * sizeof(EvoGeneInstruction));
        if (!ind->genes) {
            free(ind);
            return NULL;
        }
        memset(ind->genes, 0, num_genes * sizeof(EvoGeneInstruction));
        ind->num_genes = num_genes;
    }
    
    return ind;
}

EVO_API void evo_individual_destroy(EvoIndividual* ind) {
    if (!ind) return;
    free(ind->genes);
    free(ind->platform_scores);
    free(ind);
}

EVO_API EvoIndividual* evo_individual_clone(const EvoIndividual* ind) {
    if (!ind) return NULL;
    
    EvoIndividual* clone = evo_individual_create(ind->num_genes);
    if (!clone) return NULL;
    
    if (ind->genes && ind->num_genes > 0) {
        memcpy(clone->genes, ind->genes, ind->num_genes * sizeof(EvoGeneInstruction));
    }
    
    clone->fitness = ind->fitness;
    clone->age = ind->age;
    clone->origin = ind->origin;
    
    if (ind->platform_scores && ind->num_platforms > 0) {
        clone->platform_scores = (double*)malloc(ind->num_platforms * sizeof(double));
        if (clone->platform_scores) {
            memcpy(clone->platform_scores, ind->platform_scores, ind->num_platforms * sizeof(double));
            clone->num_platforms = ind->num_platforms;
        }
    }
    
    return clone;
}

/* 进化算子实现 */
EVO_API void evo_mutation_flip_yao(EvoGeneInstruction* gene, uint8_t position) {
    if (!gene) return;
    if (position <= 5) {
        gene->opcode ^= (1 << position);
    }
}

EVO_API void evo_mutation_modifier(EvoGeneInstruction* gene) {
    if (!gene) return;
    uint8_t bit = (uint8_t)(rand() % 6);
    gene->modifier ^= (1 << bit);
}

EVO_API void evo_crossover_single_point(const EvoIndividual* p1, const EvoIndividual* p2,
                                         EvoIndividual* c1, EvoIndividual* c2) {
    if (!p1 || !p2 || !c1 || !c2) return;
    
    size_t min_len = (p1->num_genes < p2->num_genes) ? p1->num_genes : p2->num_genes;
    if (min_len <= 1) return;
    
    size_t point = (size_t)(rand() % (min_len - 1)) + 1;
    
    /* 子个体1：p1前半 + p2后半 */
    for (size_t i = 0; i < point && i < c1->num_genes; i++) {
        if (i < p1->num_genes) {
            c1->genes[i] = p1->genes[i];
        }
    }
    for (size_t i = point; i < c1->num_genes; i++) {
        if (i < p2->num_genes) {
            c1->genes[i] = p2->genes[i];
        }
    }
    
    /* 子个体2：p2前半 + p1后半 */
    for (size_t i = 0; i < point && i < c2->num_genes; i++) {
        if (i < p2->num_genes) {
            c2->genes[i] = p2->genes[i];
        }
    }
    for (size_t i = point; i < c2->num_genes; i++) {
        if (i < p1->num_genes) {
            c2->genes[i] = p1->genes[i];
        }
    }
}

EVO_API void evo_crossover_two_point(const EvoIndividual* p1, const EvoIndividual* p2,
                                      EvoIndividual* c1, EvoIndividual* c2) {
    if (!p1 || !p2 || !c1 || !c2) return;
    
    size_t min_len = (p1->num_genes < p2->num_genes) ? p1->num_genes : p2->num_genes;
    if (min_len <= 2) {
        evo_crossover_single_point(p1, p2, c1, c2);
        return;
    }
    
    size_t pts[2];
    pts[0] = (size_t)(rand() % (min_len - 1)) + 1;
    pts[1] = (size_t)(rand() % (min_len - 1)) + 1;
    if (pts[0] > pts[1]) {
        size_t temp = pts[0];
        pts[0] = pts[1];
        pts[1] = temp;
    }
    
    /* 子个体1 */
    for (size_t i = 0; i < c1->num_genes; i++) {
        if (i < pts[0] || i >= pts[1]) {
            if (i < p1->num_genes) c1->genes[i] = p1->genes[i];
        } else {
            if (i < p2->num_genes) c1->genes[i] = p2->genes[i];
        }
    }
    
    /* 子个体2 */
    for (size_t i = 0; i < c2->num_genes; i++) {
        if (i < pts[0] || i >= pts[1]) {
            if (i < p2->num_genes) c2->genes[i] = p2->genes[i];
        } else {
            if (i < p1->num_genes) c2->genes[i] = p1->genes[i];
        }
    }
}

EVO_API void evo_crossover_uniform(const EvoIndividual* p1, const EvoIndividual* p2,
                                    EvoIndividual* c1, EvoIndividual* c2) {
    if (!p1 || !p2 || !c1 || !c2) return;
    
    size_t max_len = (p1->num_genes > p2->num_genes) ? p1->num_genes : p2->num_genes;
    
    for (size_t i = 0; i < max_len; i++) {
        int choose_p1 = (rand() % 2) == 0;
        
        if (i < c1->num_genes) {
            if (choose_p1 && i < p1->num_genes) {
                c1->genes[i] = p1->genes[i];
            } else if (i < p2->num_genes) {
                c1->genes[i] = p2->genes[i];
            }
        }
        
        if (i < c2->num_genes) {
            if (!choose_p1 && i < p1->num_genes) {
                c2->genes[i] = p1->genes[i];
            } else if (i < p2->num_genes) {
                c2->genes[i] = p2->genes[i];
            }
        }
    }
}

/* 选择算法实现 */
EVO_API size_t evo_select_roulette(const EvoPopulation* pop, uint64_t* rng_state) {
    if (!pop || pop->size == 0) return 0;
    
    double total = 0.0;
    for (size_t i = 0; i < pop->size; i++) {
        total += (pop->individuals[i].fitness > 0.0) ? pop->individuals[i].fitness : 0.001;
    }
    
    if (total == 0) {
        return (size_t)(evo_rng_next_uint32(rng_state, (uint32_t)pop->size));
    }
    
    double r = evo_rng_next_double(rng_state) * total;
    double cumulative = 0.0;
    
    for (size_t i = 0; i < pop->size; i++) {
        cumulative += (pop->individuals[i].fitness > 0.0) ? pop->individuals[i].fitness : 0.001;
        if (cumulative >= r) {
            return i;
        }
    }
    
    return pop->size - 1;
}

EVO_API size_t evo_select_tournament(const EvoPopulation* pop, size_t tournament_size,
                                      uint64_t* rng_state) {
    if (!pop || pop->size == 0) return 0;
    
    size_t actual_size = (tournament_size < pop->size) ? tournament_size : pop->size;
    size_t best_idx = 0;
    double best_fitness = -1e10;
    
    for (size_t i = 0; i < actual_size; i++) {
        size_t idx = (size_t)(evo_rng_next_uint32(rng_state, (uint32_t)pop->size));
        if (pop->individuals[idx].fitness > best_fitness) {
            best_fitness = pop->individuals[idx].fitness;
            best_idx = idx;
        }
    }
    
    return best_idx;
}

EVO_API size_t evo_select_rank(const EvoPopulation* pop, uint64_t* rng_state) {
    if (!pop || pop->size == 0) return 0;
    
    /* 创建索引数组并按适应度排序 */
    size_t* indices = (size_t*)malloc(pop->size * sizeof(size_t));
    if (!indices) return 0;
    
    for (size_t i = 0; i < pop->size; i++) {
        indices[i] = i;
    }
    
    /* 简单的冒泡排序 */
    for (size_t i = 0; i < pop->size - 1; i++) {
        for (size_t j = 0; j < pop->size - i - 1; j++) {
            if (pop->individuals[indices[j]].fitness < pop->individuals[indices[j+1]].fitness) {
                size_t temp = indices[j];
                indices[j] = indices[j+1];
                indices[j+1] = temp;
            }
        }
    }
    
    /* 计算排名权重 */
    uint64_t total_rank = 0;
    for (size_t i = 0; i < pop->size; i++) {
        total_rank += (pop->size - i);
    }
    
    /* 轮盘赌选择 */
    uint64_t r = evo_rng_next(rng_state) % total_rank;
    uint64_t cumulative = 0;
    size_t selected = 0;
    
    for (size_t i = 0; i < pop->size; i++) {
        cumulative += (pop->size - i);
        if (cumulative >= r) {
            selected = indices[i];
            break;
        }
    }
    
    free(indices);
    return selected;
}

/* 主进化循环实现 */
static int individual_compare(const void* a, const void* b) {
    const EvoIndividual* ind_a = (const EvoIndividual*)a;
    const EvoIndividual* ind_b = (const EvoIndividual*)b;
    if (ind_a->fitness > ind_b->fitness) return -1;
    if (ind_a->fitness < ind_b->fitness) return 1;
    return 0;
}

EVO_API EvoError evo_initialize_population(EvoVM* vm, const EvoGeneInstruction* seed_genes,
                                            size_t num_seed_genes) {
    if (!vm || !seed_genes || num_seed_genes == 0) {
        return EVO_ERROR_INVALID_ARG;
    }
    
    if (!vm->evo_config) {
        vm->evo_config = evo_config_create();
        if (!vm->evo_config) return EVO_ERROR_OUT_OF_MEMORY;
    }
    
    if (vm->population) {
        evo_population_destroy(vm->population);
    }
    
    vm->population = evo_population_create(vm->evo_config->population_size);
    if (!vm->population) return EVO_ERROR_OUT_OF_MEMORY;
    
    /* 创建种子个体 */
    EvoIndividual* seed = evo_individual_create(num_seed_genes);
    if (!seed) {
        evo_population_destroy(vm->population);
        vm->population = NULL;
        return EVO_ERROR_OUT_OF_MEMORY;
    }
    
    memcpy(seed->genes, seed_genes, num_seed_genes * sizeof(EvoGeneInstruction));
    seed->origin = 0; /* initial */
    
    /* 添加种子个体 */
    vm->population->individuals[0] = *seed;
    free(seed);
    vm->population->size = 1;
    
    /* 创建变异体 */
    for (size_t i = 1; i < vm->evo_config->population_size; i++) {
        EvoIndividual* variant = evo_individual_create(num_seed_genes);
        if (!variant) continue;
        
        /* 从种子复制并变异 */
        memcpy(variant->genes, seed_genes, num_seed_genes * sizeof(EvoGeneInstruction));
        
        /* 应用变异 */
        double mut_rate = vm->evo_config->mut_rate * 5;
        for (size_t g = 0; g < variant->num_genes; g++) {
            if (evo_rng_next_double(vm->rng_state) < mut_rate) {
                uint8_t bit = (uint8_t)(evo_rng_next_uint32(vm->rng_state, 6));
                evo_mutation_flip_yao(&variant->genes[g], bit);
            }
            if (evo_rng_next_double(vm->rng_state) < mut_rate * 0.5) {
                evo_mutation_modifier(&variant->genes[g]);
            }
            if (evo_rng_next_double(vm->rng_state) < mut_rate * 0.3) {
                if (variant->genes[g].operands[0] > 0) {
                    variant->genes[g].operands[0] = (uint8_t)evo_rng_next_uint32(vm->rng_state, 16);
                }
            }
        }
        
        variant->origin = (uint32_t)i;
        vm->population->individuals[i] = *variant;
        free(variant);
        vm->population->size++;
    }
    
    vm->current_generation = 0;
    
    return EVO_OK;
}

EVO_API double evo_evaluate_fitness(const EvoVM* vm, EvoIndividual* ind) {
    if (!vm || !ind) return -1000.0;
    
    if (ind->num_genes == 0) {
        ind->fitness = -1000.0;
        return ind->fitness;
    }
    
    const double* weights = vm->evo_config->fitness_weights;
    size_t n_genes = ind->num_genes;
    
    /* 计算各项指标 */
    double latency_score = -(double)n_genes * 1.0;
    double throughput_score = (10.0 - (double)n_genes * 0.5);
    if (throughput_score < 0) throughput_score = 0;
    
    double energy_score = 0.0;
    for (size_t i = 0; i < n_genes; i++) {
        energy_score -= (double)ind->genes[i].opcode * 0.01;
    }
    
    double size_score = -(double)n_genes * 0.1;
    
    /* 加权组合 */
    ind->fitness = weights[0] * latency_score +
                    weights[1] * throughput_score +
                    weights[2] * energy_score +
                    weights[3] * size_score;
    
    return ind->fitness;
}

EVO_API EvoError evo_evolve_one_generation(EvoVM* vm) {
    if (!vm || !vm->population || !vm->evo_config) {
        return EVO_ERROR_INVALID_ARG;
    }
    
    EvoPopulation* pop = vm->population;
    EvoEvolutionConfig* config = vm->evo_config;
    
    /* 评估所有个体适应度 */
    for (size_t i = 0; i < pop->size; i++) {
        evo_evaluate_fitness(vm, &pop->individuals[i]);
    }
    
    /* 按适应度排序 */
    qsort(pop->individuals, pop->size, sizeof(EvoIndividual), individual_compare);
    
    /* 更新最佳个体 */
    if (!vm->best_ever || pop->individuals[0].fitness > vm->best_ever->fitness) {
        if (vm->best_ever) {
            evo_individual_destroy(vm->best_ever);
        }
        vm->best_ever = evo_individual_clone(&pop->individuals[0]);
    }
    
    /* 精英保留 */
    size_t elite_count = (config->elite_count < pop->size) ? config->elite_count : pop->size;
    EvoIndividual* elites = (EvoIndividual*)malloc(elite_count * sizeof(EvoIndividual));
    if (!elites) return EVO_ERROR_OUT_OF_MEMORY;
    
    for (size_t i = 0; i < elite_count; i++) {
        elites[i] = *evo_individual_clone(&pop->individuals[i]);
    }
    
    /* 创建新种群 */
    EvoPopulation* new_pop = evo_population_create(config->population_size);
    if (!new_pop) {
        free(elites);
        return EVO_ERROR_OUT_OF_MEMORY;
    }
    
    /* 添加精英 */
    for (size_t i = 0; i < elite_count; i++) {
        new_pop->individuals[i] = elites[i];
        new_pop->size++;
    }
    free(elites);
    
    /* 生成其余个体 */
    while (new_pop->size < config->population_size) {
        /* 选择父母 */
        size_t p1_idx, p2_idx;
        
        if (config->selection_method == EVO_SELECT_ROULETTE) {
            p1_idx = evo_select_roulette(pop, vm->rng_state);
            p2_idx = evo_select_roulette(pop, vm->rng_state);
        } else if (config->selection_method == EVO_SELECT_RANK) {
            p1_idx = evo_select_rank(pop, vm->rng_state);
            p2_idx = evo_select_rank(pop, vm->rng_state);
        } else {
            p1_idx = evo_select_tournament(pop, config->tournament_size, vm->rng_state);
            p2_idx = evo_select_tournament(pop, config->tournament_size, vm->rng_state);
        }
        
        EvoIndividual* p1 = &pop->individuals[p1_idx];
        EvoIndividual* p2 = &pop->individuals[p2_idx];
        
        /* 创建子个体 */
        size_t max_genes = (p1->num_genes > p2->num_genes) ? p1->num_genes : p2->num_genes;
        EvoIndividual* c1 = evo_individual_create(max_genes);
        EvoIndividual* c2 = evo_individual_create(max_genes);
        
        if (!c1 || !c2) {
            evo_individual_destroy(c1);
            evo_individual_destroy(c2);
            continue;
        }
        
        /* 复制父代基因到子个体 */
        for (size_t g = 0; g < c1->num_genes && g < p1->num_genes; g++) {
            c1->genes[g] = p1->genes[g];
        }
        for (size_t g = 0; g < c2->num_genes && g < p2->num_genes; g++) {
            c2->genes[g] = p2->genes[g];
        }
        
        /* 执行交叉 */
        if (evo_rng_next_double(vm->rng_state) < config->crossover_rate) {
            if (config->crossover_method == EVO_CROSS_TWO_POINT) {
                evo_crossover_two_point(p1, p2, c1, c2);
            } else if (config->crossover_method == EVO_CROSS_UNIFORM) {
                evo_crossover_uniform(p1, p2, c1, c2);
            } else {
                evo_crossover_single_point(p1, p2, c1, c2);
            }
        }
        
        /* 执行变异 */
        for (size_t g = 0; g < c1->num_genes; g++) {
            if (evo_rng_next_double(vm->rng_state) < config->mut_rate) {
                uint8_t bit = (uint8_t)evo_rng_next_uint32(vm->rng_state, 6);
                evo_mutation_flip_yao(&c1->genes[g], bit);
            }
            if (evo_rng_next_double(vm->rng_state) < config->mut_rate * 0.3) {
                evo_mutation_modifier(&c1->genes[g]);
            }
        }
        
        for (size_t g = 0; g < c2->num_genes; g++) {
            if (evo_rng_next_double(vm->rng_state) < config->mut_rate) {
                uint8_t bit = (uint8_t)evo_rng_next_uint32(vm->rng_state, 6);
                evo_mutation_flip_yao(&c2->genes[g], bit);
            }
            if (evo_rng_next_double(vm->rng_state) < config->mut_rate * 0.3) {
                evo_mutation_modifier(&c2->genes[g]);
            }
        }
        
        /* 添加到新种群 */
        c1->origin = (uint32_t)new_pop->size;
        if (new_pop->size < new_pop->capacity) {
            new_pop->individuals[new_pop->size] = *c1;
            new_pop->size++;
        } else {
            evo_individual_destroy(c1);
        }
        
        c2->origin = (uint32_t)new_pop->size;
        if (new_pop->size < new_pop->capacity) {
            new_pop->individuals[new_pop->size] = *c2;
            new_pop->size++;
        } else {
            evo_individual_destroy(c2);
        }
    }
    
    /* 替换旧种群 */
    evo_population_destroy(vm->population);
    vm->population = new_pop;
    vm->current_generation++;
    
    return EVO_OK;
}

EVO_API const EvoIndividual* evo_evolve(EvoVM* vm, uint32_t max_generations) {
    if (!vm || !vm->population || !vm->evo_config) {
        return NULL;
    }
    
    if (max_generations == 0) {
        max_generations = vm->evo_config->max_generations;
    }
    
    uint32_t gen;
    double last_best = -1e10;
    uint32_t stagnant = 0;
    
    for (gen = 0; gen < max_generations; gen++) {
        EvoError err = evo_evolve_one_generation(vm);
        if (err != EVO_OK) {
            break;
        }
        
        /* 检查收敛 */
        if (vm->best_ever) {
            if (vm->best_ever->fitness <= last_best) {
                stagnant++;
            } else {
                stagnant = 0;
                last_best = vm->best_ever->fitness;
            }
            
            /* 如果连续多代没有改进，可以提前终止 */
            if (stagnant >= 20) {
                break;
            }
        }
    }
    
    return vm->best_ever;
}

/* 文件工具函数 */
EVO_API uint8_t* evo_read_raw_file(const char* filename, uint32_t* out_size) {
    if (!filename || !out_size) return NULL;
    
    *out_size = 0;
    
    FILE* f = fopen(filename, "rb");
    if (!f) return NULL;
    
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    
    if (size <= 0) {
        fclose(f);
        return NULL;
    }
    
    uint8_t* buffer = (uint8_t*)malloc((size_t)size);
    if (!buffer) {
        fclose(f);
        return NULL;
    }
    
    size_t read_size = fread(buffer, 1, (size_t)size, f);
    fclose(f);
    
    if (read_size != (size_t)size) {
        free(buffer);
        return NULL;
    }
    
    *out_size = (uint32_t)size;
    return buffer;
}

EVO_API int evo_assemble_file(const char* input_file, const char* output_file) {
    (void)input_file;
    (void)output_file;
    return -1;
}

/* 版本信息 */
EVO_API const char* evo_version_string(void) {
    return g_version_string;
}

EVO_API void evo_get_version(int* major, int* minor, int* patch) {
    if (major) *major = EVO_VERSION_MAJOR;
    if (minor) *minor = EVO_VERSION_MINOR;
    if (patch) *patch = EVO_VERSION_PATCH;
}