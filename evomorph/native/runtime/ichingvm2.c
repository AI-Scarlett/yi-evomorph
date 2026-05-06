#include "ichingvm2.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <time.h>

#define MASK32(x) ((x) & 0xFFFFFFFFU)
#define MAX_SYSCALLS 256

static IChingVM2_SyscallHandler g_syscalls[MAX_SYSCALLS];

static void sys_print_char(IChingVM2 *vm) {
    char ch = (char)(vm->regs[1] & 0xFF);
    if (vm->output_len < sizeof(vm->output_buffer) - 1) {
        vm->output_buffer[vm->output_len++] = ch;
        vm->output_buffer[vm->output_len] = 0;
    }
}

static void sys_print_string(IChingVM2 *vm) {
    uint32_t addr = vm->regs[1];
    while (addr < ICHINGVM2_HEAP_SIZE && vm->heap[addr] != 0) {
        if (vm->output_len < sizeof(vm->output_buffer) - 1) {
            vm->output_buffer[vm->output_len++] = (char)vm->heap[addr];
        }
        addr++;
    }
    vm->output_buffer[vm->output_len] = 0;
}

static void sys_exit(IChingVM2 *vm) {
    vm->state = ICHINGVM2_HALTED;
}

static void sys_get_time(IChingVM2 *vm) {
    vm->regs[1] = (uint32_t)time(NULL);
}

static void sys_heap_alloc(IChingVM2 *vm) {
    uint32_t size = vm->regs[1];
    if (vm->heap_ptr + size <= ICHINGVM2_HEAP_SIZE) {
        vm->regs[1] = vm->heap_ptr;
        vm->heap_ptr += size;
    } else {
        vm->regs[1] = 0;
    }
}

static void sys_read_file(IChingVM2 *vm) { vm->regs[1] = 0; }
static void sys_write_file(IChingVM2 *vm) { vm->regs[1] = 0; }
static void sys_open_file(IChingVM2 *vm) { vm->regs[1] = 0xFFFFFFFF; }
static void sys_close_file(IChingVM2 *vm) { vm->regs[1] = 0; }
static void sys_read_char(IChingVM2 *vm) { vm->regs[1] = 0; }

static void init_default_syscalls(void) {
    static int initialized = 0;
    if (initialized) return;
    memset(g_syscalls, 0, sizeof(g_syscalls));
    g_syscalls[0] = sys_print_char;
    g_syscalls[1] = sys_print_string;
    g_syscalls[2] = sys_read_char;
    g_syscalls[3] = sys_open_file;
    g_syscalls[4] = sys_read_file;
    g_syscalls[5] = sys_write_file;
    g_syscalls[6] = sys_close_file;
    g_syscalls[7] = sys_exit;
    g_syscalls[8] = sys_get_time;
    g_syscalls[9] = sys_heap_alloc;
    initialized = 1;
}

typedef struct {
    char name[64];
    uint32_t addr;
} Label;

typedef struct {
    char name[64];
    uint32_t addr;
    int resolved;
} LabelRef;

static const char *ICHING_MNEMONICS[64] = {
    "RECV","RETURN","BRANCH","APPROACH","YIELD","OBSCURE","PUSH_UP","FLUSH",
    "SPECULATE","SHOCK","UNLOCK","MISMATCH","MICRO","ABOUND","PERSIST","THRUST",
    "MERGE","ALLOC","TRAP","THROTTLE","LAME","SYNC","WELL","WAIT",
    "GATHER","FOLLOWING","TRAPPED","JOY","SENSE","REPLACE","OVERLOAD","BREAK",
    "STRIP","NOURISH","SPRT","REDUCE","STILL","ADORN","MUT","BARRIER",
    "ADVANCE","BITE","FUTU","CONVERT","TRAVEL","ILLUMINATE","CAST","ABUNDANCE",
    "CONTEMPLATE","INCREASE","DISPERSE","TRUST","GRADUAL","BIND","PENETRATE","PREFETCH",
    "HALT","INTRINSIC","LOCK","STEP","RETREAT","FELLOWSHIP","MATE","CREA"
};

static int iching_mnemonic_to_opcode(const char *name) {
    for (int i = 0; i < 64; i++) {
        if (strcmp(name, ICHING_MNEMONICS[i]) == 0) return i;
    }
    return -1;
}

typedef enum {
    NAT_NOP=0x00, NAT_HLT=0x01,
    NAT_ADD=0x08, NAT_SUB=0x09, NAT_MUL=0x0A, NAT_DIV=0x0B, NAT_MOD=0x0C,
    NAT_INC=0x0D, NAT_DEC=0x0E, NAT_NEG=0x0F,
    NAT_AND=0x10, NAT_OR=0x11, NAT_XOR=0x12, NAT_NOT=0x13,
    NAT_SHL=0x14, NAT_SHR=0x15, NAT_SAR=0x16,
    NAT_CMP=0x18, NAT_CMPI=0x19, NAT_TEST=0x1A,
    NAT_JMP=0x20, NAT_JE=0x21, NAT_JNE=0x22, NAT_JL=0x23, NAT_JLE=0x24,
    NAT_JG=0x25, NAT_JGE=0x26, NAT_JC=0x27, NAT_JNC=0x28,
    NAT_MOV=0x30, NAT_LEA=0x31, NAT_XCHG=0x32, NAT_MOVI=0x33,
    NAT_LDR=0x34, NAT_STR=0x35, NAT_LDRB=0x36, NAT_STRB=0x37,
    NAT_PUSH=0x38, NAT_POP=0x39, NAT_PUSHA=0x3A, NAT_POPA=0x3B,
    NAT_CALL=0x3C, NAT_RET=0x3D, NAT_INT=0x3E, NAT_IRET=0x3F
} NativeOpcode;

static struct { const char *name; int opcode; } NATIVE_MNEM_TAB[] = {
    {"NOP",NAT_NOP},{"HLT",NAT_HLT},
    {"ADD",NAT_ADD},{"SUB",NAT_SUB},{"MUL",NAT_MUL},{"DIV",NAT_DIV},{"MOD",NAT_MOD},
    {"INC",NAT_INC},{"DEC",NAT_DEC},{"NEG",NAT_NEG},
    {"AND",NAT_AND},{"OR",NAT_OR},{"XOR",NAT_XOR},{"NOT",NAT_NOT},
    {"SHL",NAT_SHL},{"SHR",NAT_SHR},{"SAR",NAT_SAR},
    {"CMP",NAT_CMP},{"CMPI",NAT_CMPI},{"TEST",NAT_TEST},
    {"JMP",NAT_JMP},{"JE",NAT_JE},{"JNE",NAT_JNE},{"JL",NAT_JL},{"JLE",NAT_JLE},
    {"JG",NAT_JG},{"JGE",NAT_JGE},{"JC",NAT_JC},{"JNC",NAT_JNC},
    {"MOV",NAT_MOV},{"LEA",NAT_LEA},{"XCHG",NAT_XCHG},{"MOVI",NAT_MOVI},
    {"LDR",NAT_LDR},{"STR",NAT_STR},{"LDRB",NAT_LDRB},{"STRB",NAT_STRB},
    {"PUSH",NAT_PUSH},{"POP",NAT_POP},{"PUSHA",NAT_PUSHA},{"POPA",NAT_POPA},
    {"CALL",NAT_CALL},{"RET",NAT_RET},{"INT",NAT_INT},
    {NULL,-1}
};

static int native_mnemonic_to_opcode(const char *name) {
    for (int i = 0; NATIVE_MNEM_TAB[i].name; i++) {
        if (strcmp(name, NATIVE_MNEM_TAB[i].name) == 0) return NATIVE_MNEM_TAB[i].opcode;
    }
    return -1;
}

static int is_imm_native(int opc) {
    return opc==NAT_MOVI || opc==NAT_CMPI || opc==NAT_JMP || opc==NAT_CALL ||
           opc==NAT_JE || opc==NAT_JNE || opc==NAT_JL || opc==NAT_JLE ||
           opc==NAT_JG || opc==NAT_JGE || opc==NAT_JC || opc==NAT_JNC;
}

static int is_two_reg_imm_compat(int opc) {
    return opc==NAT_ADD || opc==NAT_SUB || opc==NAT_MUL || opc==NAT_DIV ||
           opc==NAT_MOD || opc==NAT_AND || opc==NAT_OR || opc==NAT_XOR ||
           opc==NAT_SHL || opc==NAT_SHR || opc==NAT_SAR ||
           opc==NAT_CMP || opc==NAT_TEST;
}

static int is_no_operand(int opc) {
    return opc==NAT_NOP || opc==NAT_HLT || opc==NAT_RET || opc==NAT_PUSHA || opc==NAT_POPA;
}

static int is_one_reg(int opc) {
    return opc==NAT_INC || opc==NAT_DEC || opc==NAT_NEG || opc==NAT_NOT ||
           opc==NAT_PUSH || opc==NAT_POP || opc==NAT_INT;
}

static int is_two_reg(int opc) {
    return opc==NAT_ADD || opc==NAT_SUB || opc==NAT_MUL || opc==NAT_DIV ||
           opc==NAT_MOD || opc==NAT_AND || opc==NAT_OR || opc==NAT_XOR ||
           opc==NAT_SHL || opc==NAT_SHR || opc==NAT_SAR ||
           opc==NAT_CMP || opc==NAT_TEST ||
           opc==NAT_MOV || opc==NAT_LEA || opc==NAT_XCHG ||
           opc==NAT_LDR || opc==NAT_STR || opc==NAT_LDRB || opc==NAT_STRB;
}

IChingVM2 *ichingvm2_create(void) {
    IChingVM2 *vm = (IChingVM2 *)calloc(1, sizeof(IChingVM2));
    if (!vm) return NULL;
    vm->heap = (uint8_t *)calloc(ICHINGVM2_HEAP_SIZE, 1);
    vm->stack = (uint8_t *)calloc(ICHINGVM2_STACK_SIZE, 1);
    vm->program = (uint8_t *)calloc(ICHINGVM2_MAX_PROGRAM, 1);
    if (!vm->heap || !vm->stack || !vm->program) {
        ichingvm2_destroy(vm);
        return NULL;
    }
    vm->program_size = 0;
    vm->state = ICHINGVM2_INIT;
    vm->flag_interrupt = 1;
    vm->regs[ICHINGVM2_SP_REG] = ICHINGVM2_STACK_SIZE;
    vm->regs[ICHINGVM2_FP_REG] = ICHINGVM2_STACK_SIZE;
    vm->output_len = 0;
    vm->output_buffer[0] = 0;
    init_default_syscalls();
    return vm;
}

void ichingvm2_destroy(IChingVM2 *vm) {
    if (!vm) return;
    free(vm->heap);
    free(vm->stack);
    free(vm->program);
    free(vm);
}

void ichingvm2_reset(IChingVM2 *vm) {
    memset(vm->regs, 0, sizeof(vm->regs));
    memset(vm->heap, 0, ICHINGVM2_HEAP_SIZE);
    memset(vm->stack, 0, ICHINGVM2_STACK_SIZE);
    vm->program_size = 0;
    vm->pc = 0;
    vm->heap_ptr = 0;
    vm->state = ICHINGVM2_INIT;
    vm->cycle_count = 0;
    vm->energy_cost = 0;
    vm->flag_zero = vm->flag_carry = vm->flag_negative = vm->flag_overflow = 0;
    vm->flag_direction = 0;
    vm->flag_interrupt = 1;
    vm->call_stack_top = 0;
    vm->regs[ICHINGVM2_SP_REG] = ICHINGVM2_STACK_SIZE;
    vm->regs[ICHINGVM2_FP_REG] = ICHINGVM2_STACK_SIZE;
}

uint32_t ichingvm2_load_word(IChingVM2 *vm, uint32_t addr) {
    if (addr + 3 >= ICHINGVM2_HEAP_SIZE) return 0;
    return (uint32_t)vm->heap[addr] |
           ((uint32_t)vm->heap[addr+1] << 8) |
           ((uint32_t)vm->heap[addr+2] << 16) |
           ((uint32_t)vm->heap[addr+3] << 24);
}

void ichingvm2_store_word(IChingVM2 *vm, uint32_t addr, uint32_t val) {
    if (addr + 3 >= ICHINGVM2_HEAP_SIZE) return;
    vm->heap[addr]   = val & 0xFF;
    vm->heap[addr+1] = (val >> 8) & 0xFF;
    vm->heap[addr+2] = (val >> 16) & 0xFF;
    vm->heap[addr+3] = (val >> 24) & 0xFF;
}

static uint32_t load_word_stack(IChingVM2 *vm, uint32_t addr) {
    if (addr + 3 >= ICHINGVM2_STACK_SIZE) return 0;
    return (uint32_t)vm->stack[addr] |
           ((uint32_t)vm->stack[addr+1] << 8) |
           ((uint32_t)vm->stack[addr+2] << 16) |
           ((uint32_t)vm->stack[addr+3] << 24);
}

static void store_word_stack(IChingVM2 *vm, uint32_t addr, uint32_t val) {
    if (addr + 3 >= ICHINGVM2_STACK_SIZE) return;
    vm->stack[addr]   = val & 0xFF;
    vm->stack[addr+1] = (val >> 8) & 0xFF;
    vm->stack[addr+2] = (val >> 16) & 0xFF;
    vm->stack[addr+3] = (val >> 24) & 0xFF;
}

static void set_flags_arith(IChingVM2 *vm, int64_t result, int carry) {
    uint32_t r = (uint32_t)MASK32(result);
    vm->flag_zero = (r == 0);
    vm->flag_negative = (r & 0x80000000U) != 0;
    vm->flag_carry = carry;
}

static uint32_t read_imm(IChingVM2 *vm) {
    if (vm->pc + 3 >= vm->program_size) return 0;
    uint32_t val = (uint32_t)vm->program[vm->pc] |
                   ((uint32_t)vm->program[vm->pc+1] << 8) |
                   ((uint32_t)vm->program[vm->pc+2] << 16) |
                   ((uint32_t)vm->program[vm->pc+3] << 24);
    vm->pc += 4;
    return val;
}

static void step_iching(IChingVM2 *vm, uint8_t byte1) {
    if (vm->pc + 3 >= vm->program_size) { vm->state = ICHINGVM2_HALTED; return; }
    uint8_t opcode = byte1 & 0x3F;
    uint8_t modifier = vm->program[vm->pc++];
    uint8_t op1 = vm->program[vm->pc++];
    uint8_t op2 = vm->program[vm->pc++];
    uint8_t sub_op = modifier & 0x3F;
    uint8_t ext_mode = (modifier >> 6) & 0x03;
    uint32_t dst, src;
    uint32_t imm = 0;
    int has_imm = 0;

    if (ext_mode == 0) {
        dst = op1 & 0x0F; src = op2 & 0x0F;
    } else if (ext_mode == 1) {
        dst = op1 & 0x1F; src = op2 & 0x1F;
    } else if (ext_mode == 2) {
        dst = op1 & 0x1F; src = op2 & 0x1F;
        imm = read_imm(vm); has_imm = 1;
    } else {
        dst = op1 & 0x1F; src = op2 & 0x1F;
    }

    if (dst >= ICHINGVM2_NUM_REGS) dst = 0;
    if (src >= ICHINGVM2_NUM_REGS) src = 0;

    uint32_t a, b, result;
    int64_t sresult;

    switch (opcode) {
    case 63:
        if (sub_op == 1) { vm->regs[dst] = has_imm ? imm : 0; }
        else if (sub_op == 2) { /* NOP */ }
        else { vm->regs[dst] = has_imm ? imm : 0; }
        break;
    case 0:
        if (sub_op == 1) {
            uint32_t addr = vm->regs[src];
            vm->regs[dst] = (addr + 3 < ICHINGVM2_HEAP_SIZE) ? ichingvm2_load_word(vm, addr) : 0;
        } else if (sub_op == 2) {
            uint32_t addr = vm->regs[src];
            vm->regs[dst] = (addr < ICHINGVM2_HEAP_SIZE) ? vm->heap[addr] : 0;
        } else {
            vm->regs[dst] = 0;
        }
        break;
    case 61:
        if (sub_op == 1 || sub_op == 2) {
            a = vm->regs[dst]; b = has_imm ? imm : vm->regs[src];
            sresult = (int64_t)a - (int64_t)b;
            vm->flag_zero = (a == b);
            vm->flag_negative = (MASK32(sresult) & 0x80000000U) != 0;
            vm->flag_carry = (a < b);
        } else {
            vm->regs[dst] = vm->regs[src];
        }
        break;
    case 17:
        if (sub_op == 1) {
            uint32_t addr = vm->regs[dst];
            if (addr + 3 < ICHINGVM2_HEAP_SIZE) ichingvm2_store_word(vm, addr, vm->regs[src]);
        } else if (sub_op == 2) {
            uint32_t addr = vm->regs[dst];
            if (addr < ICHINGVM2_HEAP_SIZE) vm->heap[addr] = vm->regs[src] & 0xFF;
        } else {
            uint32_t size = src > 0 ? src : 256;
            if (vm->heap_ptr + size <= ICHINGVM2_HEAP_SIZE) {
                vm->heap_ptr++;
                vm->regs[dst] = vm->heap_ptr;
                vm->heap_ptr += size - 1;
            } else {
                vm->regs[dst] = 0;
            }
        }
        break;
    case 2:
        if (sub_op == 1) { vm->pc = has_imm ? imm : vm->regs[src]; }
        else if (sub_op == 2) { if (vm->flag_zero) vm->pc = has_imm ? imm : vm->regs[src]; }
        else if (sub_op == 3) { if (!vm->flag_zero) vm->pc = has_imm ? imm : vm->regs[src]; }
        else if (sub_op == 4) { if (vm->flag_carry) vm->pc = has_imm ? imm : vm->regs[src]; }
        else if (sub_op == 5) { if (vm->flag_carry || vm->flag_zero) vm->pc = has_imm ? imm : vm->regs[src]; }
        else if (sub_op == 6) { if (!vm->flag_carry && !vm->flag_zero) vm->pc = has_imm ? imm : vm->regs[src]; }
        else if (sub_op == 7) { if (!vm->flag_carry) vm->pc = has_imm ? imm : vm->regs[src]; }
        else { if (vm->regs[dst] != 0) vm->pc = has_imm ? imm : vm->regs[src]; }
        break;
    case 47:
        if (sub_op == 1) {
            if (vm->call_stack_top < ICHINGVM2_MAX_CALLS) {
                vm->call_stack[vm->call_stack_top++] = vm->pc;
            }
            vm->regs[ICHINGVM2_LR_REG] = vm->pc;
            vm->pc = has_imm ? imm : vm->regs[src];
        } else {
            uint32_t addr = vm->regs[dst];
            if (addr < ICHINGVM2_HEAP_SIZE) vm->heap[addr] = vm->regs[src] & 0xFF;
        }
        break;
    case 1:
        if (sub_op == 1) { vm->state = ICHINGVM2_HALTED; }
        else {
            if (vm->call_stack_top > 0) {
                vm->pc = vm->call_stack[--vm->call_stack_top];
            } else if (vm->regs[ICHINGVM2_LR_REG] > 0) {
                vm->pc = vm->regs[ICHINGVM2_LR_REG];
                vm->regs[ICHINGVM2_LR_REG] = 0;
            } else {
                vm->state = ICHINGVM2_HALTED;
            }
        }
        break;
    case 62:
        a = vm->regs[dst]; b = has_imm ? imm : vm->regs[src];
        if (sub_op == 1) { vm->regs[dst] = MASK32(a & b); }
        else if (sub_op == 2) { vm->regs[dst] = MASK32(a ^ b); }
        else if (sub_op == 3) { vm->regs[dst] = MASK32(a | b); }
        else { vm->regs[dst] = MASK32((a + b) / 2); }
        break;
    case 24:
        a = vm->regs[dst]; b = has_imm ? imm : vm->regs[src];
        if (sub_op == 1) {
            sresult = (int64_t)a - (int64_t)b;
            vm->regs[dst] = MASK32(sresult);
            set_flags_arith(vm, sresult, a < b);
        } else if (sub_op == 2) { vm->regs[dst] = MASK32(a * b); }
        else if (sub_op == 3) { if (b == 0) { vm->state = ICHINGVM2_ERROR; return; } vm->regs[dst] = MASK32(a / b); }
        else if (sub_op == 4) { if (b == 0) { vm->state = ICHINGVM2_ERROR; return; } vm->regs[dst] = MASK32(a % b); }
        else {
            sresult = (int64_t)a + (int64_t)b;
            vm->regs[dst] = MASK32(sresult);
            set_flags_arith(vm, sresult, sresult > 0xFFFFFFFFLL);
        }
        break;
    case 38:
        a = vm->regs[dst]; b = has_imm ? imm : vm->regs[src];
        if (sub_op == 1) { vm->regs[dst] = MASK32(a << (b & 0x1F)); }
        else if (sub_op == 2) { vm->regs[dst] = MASK32(a >> (b & 0x1F)); }
        else if (sub_op == 3) {
            int32_t sa = (a & 0x80000000U) ? (int32_t)(a | 0xFFFFFFFF00000000ULL) : (int32_t)a;
            vm->regs[dst] = MASK32((uint32_t)(sa >> (b & 0x1F)));
        }
        else { vm->regs[dst] = MASK32(a ^ (1U << b)); }
        break;
    case 6:
        if (sub_op == 1) {
            vm->regs[ICHINGVM2_SP_REG] -= 4;
            ichingvm2_store_word(vm, vm->regs[ICHINGVM2_SP_REG], vm->regs[dst]);
        } else {
            vm->regs[ICHINGVM2_SP_REG] -= 1;
            if (vm->regs[ICHINGVM2_SP_REG] < ICHINGVM2_HEAP_SIZE)
                vm->heap[vm->regs[ICHINGVM2_SP_REG]] = vm->regs[dst] & 0xFF;
        }
        break;
    case 22:
        if (sub_op == 1) {
            vm->regs[dst] = ichingvm2_load_word(vm, vm->regs[ICHINGVM2_SP_REG]);
            vm->regs[ICHINGVM2_SP_REG] += 4;
        } else {
            if (vm->regs[ICHINGVM2_SP_REG] < ICHINGVM2_HEAP_SIZE)
                vm->regs[dst] = vm->heap[vm->regs[ICHINGVM2_SP_REG]];
            vm->regs[ICHINGVM2_SP_REG] += 1;
        }
        break;
    case 48:
        if (sub_op == 1) { vm->regs[dst] = has_imm ? imm : vm->regs[src]; }
        else { vm->regs[dst] = (uint32_t)vm->cycle_count; }
        break;
    case 46:
        if (sub_op == 1) { vm->regs[dst] = MASK32(~vm->regs[dst]); }
        else if (sub_op == 2) { vm->regs[dst] = MASK32((uint32_t)(-(int32_t)vm->regs[dst])); }
        else { vm->regs[dst] = vm->regs[src]; }
        break;
    case 13:
        if (sub_op == 1) {
            for (int i = 0; i < ICHINGVM2_NUM_REGS; i++) {
                vm->regs[ICHINGVM2_SP_REG] -= 4;
                ichingvm2_store_word(vm, vm->regs[ICHINGVM2_SP_REG], vm->regs[i]);
            }
        } else if (sub_op == 2) {
            for (int i = ICHINGVM2_NUM_REGS - 1; i >= 0; i--) {
                vm->regs[i] = ichingvm2_load_word(vm, vm->regs[ICHINGVM2_SP_REG]);
                vm->regs[ICHINGVM2_SP_REG] += 4;
            }
        }
        break;
    case 27:
        if (sub_op == 1) {
            a = vm->regs[dst]; b = has_imm ? imm : vm->regs[src];
            result = a & b;
            vm->flag_zero = (result == 0);
            vm->flag_negative = (result & 0x80000000U) != 0;
            vm->flag_carry = 0;
        }
        break;
    case 50:
        if (sub_op == 1) {
            uint32_t tmp = vm->regs[dst]; vm->regs[dst] = vm->regs[src]; vm->regs[src] = tmp;
        }
        break;
    case 52:
        if (sub_op == 1) { vm->regs[dst] = MASK32(vm->regs[dst] - 1); }
        else { vm->regs[dst] = MASK32(vm->regs[dst] + 1); }
        break;
    case 12:
        if (sub_op == 1) { vm->regs[dst] = MASK32(vm->regs[dst] + 1); }
        else { vm->regs[dst] = MASK32(vm->regs[dst] + (has_imm ? imm : 1)); }
        break;
    case 32:
        vm->regs[dst] = has_imm ? MASK32(vm->regs[src] & imm) : MASK32(vm->regs[src] & 0xFF);
        break;
    case 36: vm->state = ICHINGVM2_PAUSED; break;
    case 56: vm->state = ICHINGVM2_HALTED; break;
    case 21:
        if (sub_op == 1) {
            vm->pc = ichingvm2_load_word(vm, vm->regs[ICHINGVM2_SP_REG]);
            vm->regs[ICHINGVM2_SP_REG] += 4;
            ichingvm2_load_word(vm, vm->regs[ICHINGVM2_SP_REG]);
            vm->regs[ICHINGVM2_SP_REG] += 4;
        }
        break;
    case 9:
        if (sub_op == 1) {
            uint32_t int_num = has_imm ? imm : vm->regs[src];
            if (int_num == 0x80) {
                uint32_t sys_num = vm->regs[0];
                if (sys_num < MAX_SYSCALLS && g_syscalls[sys_num]) {
                    g_syscalls[sys_num](vm);
                }
            }
        }
        break;
    default:
        break;
    }
}

static void step_native(IChingVM2 *vm, uint8_t byte1) {
    if (vm->pc + 2 >= vm->program_size) { vm->state = ICHINGVM2_HALTED; return; }
    uint8_t opc = byte1 & 0x3F;
    uint8_t byte2 = vm->program[vm->pc++];
    uint8_t byte3 = vm->program[vm->pc++];
    uint32_t dst = byte2 & 0x1F;
    uint32_t src = byte3 & 0x1F;
    if (dst >= ICHINGVM2_NUM_REGS) dst = 0;
    if (src >= ICHINGVM2_NUM_REGS) src = 0;

    uint32_t imm = 0; int has_imm = 0;
    if (is_imm_native(opc)) {
        imm = read_imm(vm); has_imm = 1;
    } else if (is_two_reg_imm_compat(opc) && (byte2 & 0x20)) {
        imm = read_imm(vm); has_imm = 1;
    }

    uint32_t a, b, result;
    int64_t sresult;

    switch (opc) {
    case NAT_NOP: break;
    case NAT_HLT: vm->state = ICHINGVM2_HALTED; break;
    case NAT_ADD:
        a = vm->regs[dst]; b = has_imm ? imm : vm->regs[src];
        sresult = (int64_t)a + (int64_t)b;
        vm->regs[dst] = MASK32(sresult);
        set_flags_arith(vm, sresult, sresult > 0xFFFFFFFFLL);
        break;
    case NAT_SUB:
        a = vm->regs[dst]; b = has_imm ? imm : vm->regs[src];
        sresult = (int64_t)a - (int64_t)b;
        vm->regs[dst] = MASK32(sresult);
        set_flags_arith(vm, sresult, a < b);
        break;
    case NAT_MUL:
        a = vm->regs[dst]; b = has_imm ? imm : vm->regs[src];
        vm->regs[dst] = MASK32((int64_t)a * (int64_t)b);
        break;
    case NAT_DIV:
        b = has_imm ? imm : vm->regs[src];
        if (b == 0) { vm->state = ICHINGVM2_ERROR; return; }
        vm->regs[dst] = MASK32(vm->regs[dst] / b);
        break;
    case NAT_MOD:
        b = has_imm ? imm : vm->regs[src];
        if (b == 0) { vm->state = ICHINGVM2_ERROR; return; }
        vm->regs[dst] = MASK32(vm->regs[dst] % b);
        break;
    case NAT_INC: vm->regs[dst] = MASK32(vm->regs[dst] + 1); break;
    case NAT_DEC: vm->regs[dst] = MASK32(vm->regs[dst] - 1); break;
    case NAT_NEG: vm->regs[dst] = MASK32((uint32_t)(-(int32_t)vm->regs[dst])); break;
    case NAT_AND:
        a = vm->regs[dst]; b = has_imm ? imm : vm->regs[src];
        vm->regs[dst] = a & b; break;
    case NAT_OR:
        a = vm->regs[dst]; b = has_imm ? imm : vm->regs[src];
        vm->regs[dst] = a | b; break;
    case NAT_XOR:
        a = vm->regs[dst]; b = has_imm ? imm : vm->regs[src];
        vm->regs[dst] = a ^ b; break;
    case NAT_NOT: vm->regs[dst] = MASK32(~vm->regs[dst]); break;
    case NAT_SHL:
        a = vm->regs[dst]; b = (has_imm ? imm : vm->regs[src]) & 0x1F;
        vm->regs[dst] = MASK32(a << b); break;
    case NAT_SHR:
        a = vm->regs[dst]; b = (has_imm ? imm : vm->regs[src]) & 0x1F;
        vm->regs[dst] = MASK32(a >> b); break;
    case NAT_SAR: {
        a = vm->regs[dst]; b = (has_imm ? imm : vm->regs[src]) & 0x1F;
        int32_t sa = (a & 0x80000000U) ? (int32_t)(a | 0xFFFFFFFF00000000ULL) : (int32_t)a;
        vm->regs[dst] = MASK32((uint32_t)(sa >> b));
        break;
    }
    case NAT_CMP: case NAT_CMPI: {
        a = vm->regs[dst]; b = has_imm ? imm : vm->regs[src];
        sresult = (int64_t)a - (int64_t)b;
        vm->flag_zero = (a == b);
        vm->flag_negative = (MASK32(sresult) & 0x80000000U) != 0;
        vm->flag_carry = (a < b);
        break;
    }
    case NAT_TEST: {
        a = vm->regs[dst]; b = has_imm ? imm : vm->regs[src];
        result = a & b;
        vm->flag_zero = (result == 0);
        vm->flag_negative = (result & 0x80000000U) != 0;
        vm->flag_carry = 0;
        break;
    }
    case NAT_JMP:  if (has_imm) vm->pc = imm; break;
    case NAT_JE:   if (vm->flag_zero && has_imm) vm->pc = imm; break;
    case NAT_JNE:  if (!vm->flag_zero && has_imm) vm->pc = imm; break;
    case NAT_JL:   if (vm->flag_carry && has_imm) vm->pc = imm; break;
    case NAT_JLE:  if ((vm->flag_zero || vm->flag_carry) && has_imm) vm->pc = imm; break;
    case NAT_JG:   if (!vm->flag_zero && !vm->flag_carry && has_imm) vm->pc = imm; break;
    case NAT_JGE:  if (!vm->flag_carry && has_imm) vm->pc = imm; break;
    case NAT_JC:   if (vm->flag_carry && has_imm) vm->pc = imm; break;
    case NAT_JNC:  if (!vm->flag_carry && has_imm) vm->pc = imm; break;
    case NAT_MOV:  vm->regs[dst] = vm->regs[src]; break;
    case NAT_MOVI: if (has_imm) vm->regs[dst] = imm; break;
    case NAT_LEA:  vm->regs[dst] = MASK32(vm->regs[src] + (has_imm ? imm : 0)); break;
    case NAT_XCHG: { uint32_t t = vm->regs[dst]; vm->regs[dst] = vm->regs[src]; vm->regs[src] = t; break; }
    case NAT_PUSH:
        vm->regs[ICHINGVM2_SP_REG] -= 4;
        ichingvm2_store_word(vm, vm->regs[ICHINGVM2_SP_REG], vm->regs[dst]);
        break;
    case NAT_POP:
        vm->regs[dst] = ichingvm2_load_word(vm, vm->regs[ICHINGVM2_SP_REG]);
        vm->regs[ICHINGVM2_SP_REG] += 4;
        break;
    case NAT_PUSHA:
        for (int i = 0; i < ICHINGVM2_NUM_REGS; i++) {
            vm->regs[ICHINGVM2_SP_REG] -= 4;
            ichingvm2_store_word(vm, vm->regs[ICHINGVM2_SP_REG], vm->regs[i]);
        }
        break;
    case NAT_POPA:
        for (int i = ICHINGVM2_NUM_REGS - 1; i >= 0; i--) {
            vm->regs[i] = ichingvm2_load_word(vm, vm->regs[ICHINGVM2_SP_REG]);
            vm->regs[ICHINGVM2_SP_REG] += 4;
        }
        break;
    case NAT_CALL:
        vm->regs[ICHINGVM2_SP_REG] -= 4;
        ichingvm2_store_word(vm, vm->regs[ICHINGVM2_SP_REG], vm->pc);
        if (has_imm) vm->pc = imm;
        break;
    case NAT_RET: {
        uint32_t ra = ichingvm2_load_word(vm, vm->regs[ICHINGVM2_SP_REG]);
        vm->regs[ICHINGVM2_SP_REG] += 4;
        vm->pc = ra;
        break;
    }
    case NAT_LDR:
        vm->regs[dst] = ichingvm2_load_word(vm, vm->regs[src]);
        break;
    case NAT_STR:
        ichingvm2_store_word(vm, vm->regs[dst], vm->regs[src]);
        break;
    case NAT_LDRB:
        if (vm->regs[src] < ICHINGVM2_HEAP_SIZE) vm->regs[dst] = vm->heap[vm->regs[src]];
        break;
    case NAT_STRB:
        if (vm->regs[dst] < ICHINGVM2_HEAP_SIZE) vm->heap[vm->regs[dst]] = vm->regs[src] & 0xFF;
        break;
    case NAT_INT: break;
    case NAT_IRET: {
        uint32_t ra = ichingvm2_load_word(vm, vm->regs[ICHINGVM2_SP_REG]);
        vm->regs[ICHINGVM2_SP_REG] += 4;
        vm->pc = ra;
        vm->flag_interrupt = 1;
        break;
    }
    default: vm->state = ICHINGVM2_ERROR; break;
    }
}

int ichingvm2_step(IChingVM2 *vm) {
    if (vm->state != ICHINGVM2_RUNNING) return -1;
    if (vm->pc >= vm->program_size) { vm->state = ICHINGVM2_HALTED; return -1; }
    uint8_t byte1 = vm->program[vm->pc++];
    uint8_t itype = (byte1 >> 6) & 0x03;
    if (itype == 0x02) step_iching(vm, byte1);
    else if (itype == 0x01) step_native(vm, byte1);
    else { vm->state = ICHINGVM2_ERROR; return -1; }
    vm->cycle_count++;
    return 0;
}

int ichingvm2_run(IChingVM2 *vm, uint64_t max_cycles) {
    vm->state = ICHINGVM2_RUNNING;
    while (vm->state == ICHINGVM2_RUNNING && vm->cycle_count < max_cycles) {
        if (ichingvm2_step(vm) < 0) break;
    }
    return (vm->state == ICHINGVM2_HALTED) ? 0 : -1;
}

int ichingvm2_load_program(IChingVM2 *vm, const uint8_t *data, uint32_t size) {
    if (size > ICHINGVM2_MAX_PROGRAM) return -1;
    memcpy(vm->program, data, size);
    vm->program_size = size;
    vm->pc = 0;
    vm->state = ICHINGVM2_INIT;
    return 0;
}

int ichingvm2_load_evob(IChingVM2 *vm, const uint8_t *data, uint32_t size) {
    if (size < 10) return -1;
    if (memcmp(data, "EVOB", 4) != 0) return -1;
    uint16_t header_size = (data[6] << 8) | data[7];
    if (header_size < 10 || header_size > size) return -1;
    uint32_t bc_size = size - header_size;
    if (bc_size > ICHINGVM2_MAX_PROGRAM) return -1;
    memcpy(vm->program, data + header_size, bc_size);
    vm->program_size = bc_size;
    vm->pc = 0;
    vm->state = ICHINGVM2_INIT;
    return 0;
}

int ichingvm2_load_string(IChingVM2 *vm, uint32_t addr, const char *s) {
    uint32_t len = (uint32_t)strlen(s);
    if (addr + len >= ICHINGVM2_HEAP_SIZE) return -1;
    memcpy(vm->heap + addr, s, len);
    vm->heap[addr + len] = 0;
    return (int)len;
}

void ichingvm2_read_string(IChingVM2 *vm, uint32_t addr, char *buf, uint32_t buf_size) {
    uint32_t i = 0;
    while (i < buf_size - 1 && addr + i < ICHINGVM2_HEAP_SIZE && vm->heap[addr + i] != 0) {
        buf[i] = vm->heap[addr + i];
        i++;
    }
    buf[i] = '\0';
}

static int parse_register(const char *s) {
    while (*s && isspace(*s)) s++;
    if (toupper(*s) == 'R') { s++; return atoi(s); }
    if (strcmp(s, "SP") == 0) return ICHINGVM2_SP_REG;
    if (strcmp(s, "FP") == 0) return ICHINGVM2_FP_REG;
    if (strcmp(s, "LR") == 0) return ICHINGVM2_LR_REG;
    return -1;
}

static int parse_imm_or_label(const char *s, Label *labels, int nlabels, uint32_t *val) {
    while (*s && isspace(*s)) s++;
    if (*s == '#') {
        s++;
        *val = (uint32_t)strtoul(s, NULL, 0);
        return 1;
    }
    if (strncmp(s, "0x", 2) == 0 || strncmp(s, "0X", 2) == 0) {
        *val = (uint32_t)strtoul(s, NULL, 16);
        return 1;
    }
    char *end;
    unsigned long v = strtoul(s, &end, 10);
    if (end != s) { *val = (uint32_t)v; return 1; }
    if (*s == '@') s++;
    for (int i = 0; i < nlabels; i++) {
        if (strcmp(labels[i].name, s) == 0) { *val = labels[i].addr; return 1; }
    }
    return 0;
}

static int emit_byte(uint8_t *prog, uint32_t *pos, uint8_t b) {
    if (*pos >= ICHINGVM2_MAX_PROGRAM) return -1;
    prog[(*pos)++] = b;
    return 0;
}

static int emit_word_le(uint8_t *prog, uint32_t *pos, uint32_t val) {
    if (*pos + 3 >= ICHINGVM2_MAX_PROGRAM) return -1;
    prog[(*pos)++] = val & 0xFF;
    prog[(*pos)++] = (val >> 8) & 0xFF;
    prog[(*pos)++] = (val >> 16) & 0xFF;
    prog[(*pos)++] = (val >> 24) & 0xFF;
    return 0;
}

uint32_t ichingvm2_assemble(IChingVM2 *vm, const char *asm_source) {
    char *src = strdup(asm_source);
    Label labels[ICHINGVM2_MAX_LABELS];
    int nlabels = 0;
    LabelRef refs[ICHINGVM2_MAX_LABELS];
    int nrefs = 0;

    typedef struct { int type; char mnem[64]; char ops[256]; } ParsedLine;
    ParsedLine *lines_arr = NULL;
    int nlines = 0;

    char *line = strtok(src, "\n");
    while (line) {
        while (*line && isspace(*line)) line++;
        if (!*line || *line == ';' || *line == '#') { line = strtok(NULL, "\n"); continue; }
        lines_arr = (ParsedLine *)realloc(lines_arr, (nlines + 1) * sizeof(ParsedLine));
        ParsedLine *pl = &lines_arr[nlines];
        memset(pl, 0, sizeof(*pl));
        char *colon = strchr(line, ':');
        if (colon && !strchr(line, ',')) {
            char *p = line; while (*p && isspace(*p)) p++;
            char *e = colon; while (e > p && isspace(*(e-1))) e--;
            int len = (int)(e - p);
            if (len > 0 && len < 64) {
                memcpy(pl->mnem, p, len); pl->mnem[len] = 0;
                pl->type = 0; /* label */
                nlines++;
                line = strtok(NULL, "\n");
                continue;
            }
        }
        pl->type = 1; /* instruction */
        char *sp = strchr(line, ' ');
        char *tab = strchr(line, '\t');
        char *sep = NULL;
        if (sp && tab) sep = (sp < tab) ? sp : tab;
        else if (sp) sep = sp;
        else if (tab) sep = tab;
        if (sep) {
            int mlen = (int)(sep - line);
            if (mlen >= 64) mlen = 63;
            memcpy(pl->mnem, line, mlen); pl->mnem[mlen] = 0;
            char *o = sep; while (*o && isspace(*o)) o++;
            strncpy(pl->ops, o, 255); pl->ops[255] = 0;
            char *cmt = strchr(pl->ops, ';');
            if (cmt) *cmt = 0;
        } else {
            strncpy(pl->mnem, line, 63); pl->mnem[63] = 0;
        }
        for (char *p = pl->mnem; *p; p++) *p = toupper(*p);
        nlines++;
        line = strtok(NULL, "\n");
    }

    /* First pass: calculate label addresses */
    uint32_t pc = 0;
    for (int i = 0; i < nlines; i++) {
        ParsedLine *pl = &lines_arr[i];
        if (pl->type == 0) {
            if (nlabels < ICHINGVM2_MAX_LABELS) {
                strcpy(labels[nlabels].name, pl->mnem);
                labels[nlabels].addr = pc;
                nlabels++;
            }
            continue;
        }
        char base_mnem[64] = {0};
        int iching_ext = -1;
        char *dot = strchr(pl->mnem, '.');
        if (dot) {
            int len = (int)(dot - pl->mnem);
            memcpy(base_mnem, pl->mnem, len);
            iching_ext = atoi(dot + 1);
        } else {
            strcpy(base_mnem, pl->mnem);
        }
        int iching_opc = iching_mnemonic_to_opcode(base_mnem);
        if (iching_opc >= 0) {
            if (iching_ext >= 0) {
                int has_imm_op = 0;
                if (pl->ops[0]) {
                    char ops_copy[256]; strcpy(ops_copy, pl->ops);
                    char *tok = strtok(ops_copy, ",");
                    while (tok) {
                        while (*tok && isspace(*tok)) tok++;
                        if (*tok == '#' || *tok == '@') { has_imm_op = 1; break; }
                        if (strncmp(tok, "0x", 2) == 0 || strncmp(tok, "0X", 2) == 0) { has_imm_op = 1; break; }
                        tok = strtok(NULL, ",");
                    }
                }
                pc += has_imm_op ? 8 : 4;
            } else {
                pc += 4;
            }
            continue;
        }
        int nat_opc = native_mnemonic_to_opcode(pl->mnem);
        if (nat_opc >= 0) {
            if (is_imm_native(nat_opc)) { pc += 7; }
            else if (is_two_reg_imm_compat(nat_opc)) {
                int has_imm_op = 0;
                if (pl->ops[0]) {
                    char ops_copy[256]; strcpy(ops_copy, pl->ops);
                    char *tok1 = strtok(ops_copy, ",");
                    char *tok2 = strtok(NULL, ",");
                    if (tok2) {
                        while (*tok2 && isspace(*tok2)) tok2++;
                        if (*tok2 == '#' || strncmp(tok2, "0x", 2) == 0 || strncmp(tok2, "0X", 2) == 0)
                            has_imm_op = 1;
                        else {
                            char *end;
                            strtoul(tok2, &end, 10);
                            if (end != tok2) has_imm_op = 1;
                        }
                    }
                }
                pc += has_imm_op ? 7 : 3;
            } else { pc += 3; }
            continue;
        }
    }

    /* Second pass: generate bytecode */
    uint8_t *prog = vm->program;
    pc = 0;
    for (int i = 0; i < nlines; i++) {
        ParsedLine *pl = &lines_arr[i];
        if (pl->type == 0) {
            for (int j = 0; j < nlabels; j++) {
                if (strcmp(labels[j].name, pl->mnem) == 0) labels[j].addr = pc;
            }
            continue;
        }
        char base_mnem[64] = {0};
        int iching_ext = -1;
        char *dot = strchr(pl->mnem, '.');
        if (dot) {
            int len = (int)(dot - pl->mnem);
            memcpy(base_mnem, pl->mnem, len);
            iching_ext = atoi(dot + 1);
        } else {
            strcpy(base_mnem, pl->mnem);
        }
        int iching_opc = iching_mnemonic_to_opcode(base_mnem);
        if (iching_opc >= 0) {
            uint8_t b1 = 0x80 | (iching_opc & 0x3F);
            if (iching_ext >= 0) {
                uint8_t sub_op = iching_ext & 0x3F;
                uint32_t dst_reg = 0, src_reg = 0, imm_val = 0;
                int has_imm_op = 0;
                char ops_copy[256]; strcpy(ops_copy, pl->ops);
                char *toks[8] = {0}; int ntok = 0;
                char *t = strtok(ops_copy, ",");
                while (t && ntok < 8) { while(*t&&isspace(*t))t++; toks[ntok++] = t; t = strtok(NULL, ","); }

                for (int k = 0; k < ntok; k++) {
                    char *r = toks[k]; while(*r&&isspace(*r))r++;
                    if (toupper(*r) == 'R') {
                        if (k == 0) dst_reg = atoi(r+1);
                        else if (k == 1) src_reg = atoi(r+1);
                    } else if (*r == '#') {
                        imm_val = (uint32_t)strtoul(r+1, NULL, 0);
                        has_imm_op = 1;
                    } else if (*r == '@') {
                        for (int j = 0; j < nlabels; j++) {
                            if (strcmp(labels[j].name, r+1) == 0) { imm_val = labels[j].addr; has_imm_op = 1; break; }
                        }
                    } else if (strncmp(r, "0x", 2) == 0 || strncmp(r, "0X", 2) == 0) {
                        imm_val = (uint32_t)strtoul(r, NULL, 16); has_imm_op = 1;
                    } else {
                        for (int j = 0; j < nlabels; j++) {
                            if (strcmp(labels[j].name, r) == 0) { imm_val = labels[j].addr; has_imm_op = 1; break; }
                        }
                        if (!has_imm_op) { char *end; unsigned long v = strtoul(r, &end, 0); if (end != r) { imm_val = (uint32_t)v; has_imm_op = 1; } }
                    }
                }

                uint8_t ext_mode = has_imm_op ? 2 : 1;
                uint8_t b2 = (ext_mode << 6) | sub_op;
                emit_byte(prog, &pc, b1);
                emit_byte(prog, &pc, b2);
                emit_byte(prog, &pc, dst_reg & 0x1F);
                emit_byte(prog, &pc, src_reg & 0x1F);
                if (has_imm_op) emit_word_le(prog, &pc, imm_val);
            } else {
                emit_byte(prog, &pc, b1);
                emit_byte(prog, &pc, 0);
                emit_byte(prog, &pc, 0);
                emit_byte(prog, &pc, 0);
            }
            continue;
        }

        int nat_opc = native_mnemonic_to_opcode(pl->mnem);
        if (nat_opc < 0) continue;

        uint8_t b1 = 0x40 | (nat_opc & 0x3F);
        uint8_t b2 = 0, b3 = 0;
        int has_imm = 0; uint32_t imm_value = 0;

        char ops_copy[256]; strcpy(ops_copy, pl->ops);
        char *toks[8] = {0}; int ntok = 0;
        char *tt = strtok(ops_copy, ",");
        while (tt && ntok < 8) { while(*tt&&isspace(*tt))tt++; toks[ntok++] = tt; tt = strtok(NULL, ","); }

        if (is_no_operand(nat_opc)) {
            /* nothing */
        } else if (is_one_reg(nat_opc)) {
            if (ntok >= 1) { int r = parse_register(toks[0]); if (r >= 0) b2 = r & 0x1F; }
        } else if (is_two_reg(nat_opc)) {
            if (ntok >= 2) {
                int dr = parse_register(toks[0]);
                if (dr >= 0) b2 = dr & 0x1F;
                int sr = parse_register(toks[1]);
                if (sr >= 0) {
                    b3 = sr & 0x1F;
                } else if (is_two_reg_imm_compat(nat_opc)) {
                    uint32_t val;
                    if (parse_imm_or_label(toks[1], labels, nlabels, &val)) {
                        b2 = (dr & 0x1F) | 0x20;
                        b3 = 0;
                        has_imm = 1;
                        imm_value = val;
                    }
                }
            }
        } else if (is_imm_native(nat_opc)) {
            if (ntok >= 2) {
                int dr = parse_register(toks[0]);
                if (dr >= 0) b2 = dr & 0x1F;
                uint32_t val;
                if (parse_imm_or_label(toks[1], labels, nlabels, &val)) {
                    has_imm = 1; imm_value = val;
                }
            } else if (ntok == 1) {
                uint32_t val;
                if (parse_imm_or_label(toks[0], labels, nlabels, &val)) {
                    has_imm = 1; imm_value = val;
                }
            }
        }

        emit_byte(prog, &pc, b1);
        emit_byte(prog, &pc, b2);
        emit_byte(prog, &pc, b3);
        if (has_imm) emit_word_le(prog, &pc, imm_value);
    }

    vm->program_size = pc;
    free(src);
    free(lines_arr);
    return pc;
}

int ichingvm2_load_assembled(IChingVM2 *vm, const char *asm_source) {
    uint32_t size = ichingvm2_assemble(vm, asm_source);
    if (size == 0) return -1;
    vm->pc = 0;
    vm->state = ICHINGVM2_INIT;
    return 0;
}

void ichingvm2_register_syscall(IChingVM2 *vm, int num, IChingVM2_SyscallHandler handler) {
    (void)vm;
    if (num >= 0 && num < MAX_SYSCALLS) g_syscalls[num] = handler;
}

const char *ichingvm2_get_output(IChingVM2 *vm) {
    vm->output_buffer[vm->output_len] = 0;
    return vm->output_buffer;
}

void ichingvm2_clear_output(IChingVM2 *vm) {
    vm->output_len = 0;
    vm->output_buffer[0] = 0;
}
