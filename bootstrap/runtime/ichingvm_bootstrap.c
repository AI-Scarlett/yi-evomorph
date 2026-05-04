/*
 * IChingVM Bootstrap - 易衍虚拟机自举版
 * 
 * 这是 Evomorph 完全自举的最小可信计算基(TCB)
 * 
 * 设计原则：
 * 1. 最小化：只包含自举所需的最少功能
 * 2. 可审计：代码简洁，易于验证
 * 3. 可扩展：支持后续功能添加
 * 
 * 系统调用约定：
 *   R0 = 系统调用号
 *   R1-R3 = 参数
 *   R0 = 返回值
 *   R15 (R_A0) = 额外返回/状态
 * 
 * 内存布局：
 *   0x00000000 - 0x0000FFFF : 栈 (64KB)
 *   0x00010000 - 0x0010FFFF : 堆 (1MB)
 *   0x00110000 - 0x0011FFFF : 程序 (64KB)
 *   0x00120000 - 0x00FFFFFF : 数据区 (14MB)
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <ctype.h>
#include <fcntl.h>

#ifdef _WIN32
#include <io.h>
#define open _open
#define read _read
#define write _write
#define close _close
#define O_RDONLY _O_RDONLY
#define O_WRONLY _O_WRONLY
#define O_CREAT _O_CREAT
#define O_TRUNC _O_TRUNC
#else
#include <unistd.h>
#include <sys/stat.h>
#endif

#ifndef S_IRUSR
#define S_IRUSR 0400
#define S_IWUSR 0200
#endif

#define NUM_REGISTERS 16
#define STACK_SIZE 65536
#define HEAP_SIZE 1048576
#define MAX_FILES 64
#define MAX_LOCKS 256
#define MAX_BARRIERS 256

#define R_FP 12
#define R_SP 13
#define R_LR 14
#define R_A0 15

#define VM_MEMORY_SIZE (16 * 1024 * 1024)

typedef enum {
    VM_INIT = 0,
    VM_RUNNING = 1,
    VM_PAUSED = 2,
    VM_HALTED = 3,
    VM_ERROR = 4,
    VM_TRAPPED = 5,
    VM_SYSCALL = 6
} VMState;

typedef enum {
    SYSCALL_OPEN = 0,
    SYSCALL_READ = 1,
    SYSCALL_WRITE = 2,
    SYSCALL_CLOSE = 3,
    SYSCALL_SEEK = 4,
    SYSCALL_TELL = 5,
    SYSCALL_MALLOC = 10,
    SYSCALL_FREE = 11,
    SYSCALL_MEMCPY = 12,
    SYSCALL_MEMSET = 13,
    SYSCALL_MEMCMP = 14,
    SYSCALL_STRLEN = 20,
    SYSCALL_STRCMP = 21,
    SYSCALL_STRCPY = 22,
    SYSCALL_STRCAT = 23,
    SYSCALL_STRCHR = 24,
    SYSCALL_ISDIGIT = 30,
    SYSCALL_ISALPHA = 31,
    SYSCALL_ISALNUM = 32,
    SYSCALL_ISSPACE = 33,
    SYSCALL_TOUPPER = 34,
    SYSCALL_TOLOWER = 35,
    SYSCALL_ATOI = 36,
    SYSCALL_PRINT = 40,
    SYSCALL_PRINTLN = 41,
    SYSCALL_SCAN = 42,
    SYSCALL_EXIT = 255
} SysCallNum;

typedef struct {
    uint32_t registers[NUM_REGISTERS];
    uint8_t *memory;
    uint32_t stack_base;
    uint32_t heap_base;
    uint32_t heap_ptr;
    uint32_t pc;
    VMState state;
    
    uint8_t flag_zero;
    uint8_t flag_carry;
    uint8_t flag_negative;
    uint8_t flag_overflow;
    
    FILE *files[MAX_FILES];
    uint32_t cycle_count;
    double energy_cost;
} IChingVM;

static void vm_init(IChingVM *vm) {
    memset(vm, 0, sizeof(IChingVM));
    vm->state = VM_INIT;
    vm->memory = (uint8_t*)calloc(1, VM_MEMORY_SIZE);
    vm->stack_base = 0;
    vm->heap_base = STACK_SIZE;
    vm->heap_ptr = vm->heap_base;
    vm->registers[R_SP] = STACK_SIZE - 1;
    vm->registers[R_FP] = STACK_SIZE - 1;
}

static void vm_free(IChingVM *vm) {
    if (vm->memory) {
        free(vm->memory);
        vm->memory = NULL;
    }
    for (int i = 0; i < MAX_FILES; i++) {
        if (vm->files[i]) {
            fclose(vm->files[i]);
            vm->files[i] = NULL;
        }
    }
}

static inline uint8_t decode_opcode(uint8_t byte1) {
    return (byte1 >> 2) & 0x3F;
}

static inline uint8_t decode_modifier(uint8_t byte1, uint8_t byte2) {
    return ((byte1 & 0x03) << 4) | (byte2 & 0x0F);
}

static uint8_t* vm_ptr(IChingVM *vm, uint32_t addr) {
    if (addr >= VM_MEMORY_SIZE) return NULL;
    return &vm->memory[addr];
}

static uint32_t vm_read_u32(IChingVM *vm, uint32_t addr) {
    if (addr + 3 >= VM_MEMORY_SIZE) return 0;
    return (vm->memory[addr] << 24) |
           (vm->memory[addr + 1] << 16) |
           (vm->memory[addr + 2] << 8) |
           (vm->memory[addr + 3]);
}

static void vm_write_u32(IChingVM *vm, uint32_t addr, uint32_t val) {
    if (addr + 3 >= VM_MEMORY_SIZE) return;
    vm->memory[addr] = (val >> 24) & 0xFF;
    vm->memory[addr + 1] = (val >> 16) & 0xFF;
    vm->memory[addr + 2] = (val >> 8) & 0xFF;
    vm->memory[addr + 3] = val & 0xFF;
}

static void vm_syscall(IChingVM *vm) {
    uint32_t syscall_num = vm->registers[0];
    uint32_t arg1 = vm->registers[1];
    uint32_t arg2 = vm->registers[2];
    uint32_t arg3 = vm->registers[3];
    uint32_t result = 0;
    
    switch (syscall_num) {
        case SYSCALL_OPEN: {
            char *filename = (char*)vm_ptr(vm, arg1);
            int mode = (int)arg2;
            FILE *f = NULL;
            if (mode == 0) f = fopen(filename, "rb");
            else if (mode == 1) f = fopen(filename, "wb");
            else if (mode == 2) f = fopen(filename, "rb+");
            if (f) {
                for (int i = 0; i < MAX_FILES; i++) {
                    if (!vm->files[i]) {
                        vm->files[i] = f;
                        result = i + 1;
                        break;
                    }
                }
            }
            break;
        }
        case SYSCALL_READ: {
            int fd = (int)arg1 - 1;
            if (fd >= 0 && fd < MAX_FILES && vm->files[fd]) {
                uint8_t *buf = vm_ptr(vm, arg2);
                size_t count = (size_t)arg3;
                result = (uint32_t)fread(buf, 1, count, vm->files[fd]);
            }
            break;
        }
        case SYSCALL_WRITE: {
            int fd = (int)arg1 - 1;
            if (fd == -1) {
                uint8_t *buf = vm_ptr(vm, arg2);
                size_t count = (size_t)arg3;
                fwrite(buf, 1, count, stdout);
                fflush(stdout);
                result = (uint32_t)count;
            } else if (fd >= 0 && fd < MAX_FILES && vm->files[fd]) {
                uint8_t *buf = vm_ptr(vm, arg2);
                size_t count = (size_t)arg3;
                result = (uint32_t)fwrite(buf, 1, count, vm->files[fd]);
            }
            break;
        }
        case SYSCALL_CLOSE: {
            int fd = (int)arg1 - 1;
            if (fd >= 0 && fd < MAX_FILES && vm->files[fd]) {
                fclose(vm->files[fd]);
                vm->files[fd] = NULL;
                result = 1;
            }
            break;
        }
        case SYSCALL_MALLOC: {
            uint32_t size = arg1;
            if (vm->heap_ptr + size < vm->heap_base + HEAP_SIZE) {
                result = vm->heap_ptr;
                vm->heap_ptr += size;
            }
            break;
        }
        case SYSCALL_FREE: {
            result = 1;
            break;
        }
        case SYSCALL_MEMCPY: {
            uint8_t *dst = vm_ptr(vm, arg1);
            uint8_t *src = vm_ptr(vm, arg2);
            uint32_t len = arg3;
            if (dst && src) {
                memcpy(dst, src, len);
                result = arg1;
            }
            break;
        }
        case SYSCALL_MEMSET: {
            uint8_t *dst = vm_ptr(vm, arg1);
            uint8_t val = (uint8_t)arg2;
            uint32_t len = arg3;
            if (dst) {
                memset(dst, val, len);
                result = arg1;
            }
            break;
        }
        case SYSCALL_MEMCMP: {
            uint8_t *p1 = vm_ptr(vm, arg1);
            uint8_t *p2 = vm_ptr(vm, arg2);
            uint32_t len = arg3;
            if (p1 && p2) {
                result = (uint32_t)(int32_t)memcmp(p1, p2, len);
            }
            break;
        }
        case SYSCALL_STRLEN: {
            char *str = (char*)vm_ptr(vm, arg1);
            if (str) {
                result = (uint32_t)strlen(str);
            }
            break;
        }
        case SYSCALL_STRCMP: {
            char *s1 = (char*)vm_ptr(vm, arg1);
            char *s2 = (char*)vm_ptr(vm, arg2);
            if (s1 && s2) {
                result = (uint32_t)(int32_t)strcmp(s1, s2);
            }
            break;
        }
        case SYSCALL_STRCPY: {
            char *dst = (char*)vm_ptr(vm, arg1);
            char *src = (char*)vm_ptr(vm, arg2);
            if (dst && src) {
                strcpy(dst, src);
                result = arg1;
            }
            break;
        }
        case SYSCALL_ISDIGIT: {
            result = isdigit((int)arg1) ? 1 : 0;
            break;
        }
        case SYSCALL_ISALPHA: {
            result = isalpha((int)arg1) ? 1 : 0;
            break;
        }
        case SYSCALL_ISALNUM: {
            result = isalnum((int)arg1) ? 1 : 0;
            break;
        }
        case SYSCALL_ISSPACE: {
            result = isspace((int)arg1) ? 1 : 0;
            break;
        }
        case SYSCALL_TOUPPER: {
            result = (uint32_t)toupper((int)arg1);
            break;
        }
        case SYSCALL_TOLOWER: {
            result = (uint32_t)tolower((int)arg1);
            break;
        }
        case SYSCALL_ATOI: {
            char *str = (char*)vm_ptr(vm, arg1);
            if (str) {
                result = (uint32_t)(int32_t)atoi(str);
            }
            break;
        }
        case SYSCALL_PRINT: {
            char *str = (char*)vm_ptr(vm, arg1);
            if (str) {
                fputs(str, stdout);
                fflush(stdout);
            }
            break;
        }
        case SYSCALL_PRINTLN: {
            char *str = (char*)vm_ptr(vm, arg1);
            if (str) {
                puts(str);
            } else {
                putchar('\n');
            }
            fflush(stdout);
            break;
        }
        case SYSCALL_EXIT: {
            vm->state = VM_HALTED;
            vm->registers[R_A0] = arg1;
            return;
        }
        default: {
            vm->state = VM_ERROR;
            vm->registers[R_A0] = syscall_num;
            return;
        }
    }
    
    vm->registers[0] = result;
}

typedef void (*OpHandler)(IChingVM*, uint8_t, uint8_t*);

static void op_crea(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    static uint32_t thread_id = 1;
    vm->registers[dst] = thread_id++;
    vm->energy_cost += 10.0;
}

static void op_recv(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t port = operands[1] & 0x0F;
    if (port == 0) {
        vm_syscall(vm);
    } else {
        vm->registers[dst] = 0;
    }
}

static void op_alloc(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint32_t size = operands[1] > 0 ? operands[1] : 256;
    if (vm->heap_ptr + size < vm->heap_base + HEAP_SIZE) {
        vm->registers[dst] = vm->heap_ptr;
        vm->heap_ptr += size;
    } else {
        vm->registers[dst] = 0;
        vm->flag_overflow = 1;
    }
}

static void op_sprt(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    vm->registers[dst] = 1;
}

static void op_wait(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t cond = operands[0] & 0x0F;
    if (vm->registers[cond] == 0) {
        vm->pc -= 4;
    }
}

static void op_lock(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint16_t lock_id = operands[0] & 0xFFFF;
    if (lock_id < MAX_LOCKS) {
        vm->memory[vm->heap_base + lock_id] = 1;
    }
}

static void op_branch(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    uint8_t cond = operands[0] & 0x0F;
    if (vm->registers[cond] != 0) {
        uint32_t target;
        if (modifier != 0) {
            uint8_t reg = operands[1] & 0x0F;
            target = vm->registers[reg];
        } else {
            target = operands[1];
        }
        if (target < VM_MEMORY_SIZE) {
            vm->pc = target;
        }
    }
}

static void op_merge(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t result = vm->registers[dst] | vm->registers[src];
    vm->registers[dst] = result;
    vm->flag_zero = (result == 0);
    vm->flag_negative = (result & 0x80000000) != 0;
}

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

static void op_step(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t reg = operands[0] & 0x0F;
    vm->registers[reg] = (vm->registers[reg] + 1) & 0xFFFFFFFF;
}

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

static void op_halt(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    vm->state = VM_HALTED;
}

static void op_fellowship(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

static void op_abundance(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t src_val = vm->registers[src];
    uint32_t addr = vm->registers[dst];
    if (addr < VM_MEMORY_SIZE) {
        vm->memory[addr] = src_val & 0xFF;
    }
}

static void op_yield(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    vm->state = VM_PAUSED;
}

static void op_speculate(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

static void op_following(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

static void op_mut(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t target = operands[0] & 0x0F;
    uint8_t bit = operands[1] & 0x1F;
    uint32_t mask = 1 << bit;
    vm->registers[target] ^= mask;
}

static void op_approach(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t result = vm->registers[dst] & vm->registers[src];
    vm->registers[dst] = result;
    vm->flag_zero = (result == 0);
    vm->flag_negative = (result & 0x80000000) != 0;
}

static void op_contemplate(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t reg = operands[0] & 0x0F;
    vm->registers[reg] = vm->cycle_count;
}

static void op_bite(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t expected = operands[0];
    uint8_t actual_reg = operands[1] & 0x0F;
    if ((vm->registers[actual_reg] & 0xFF) != expected) {
        vm->state = VM_TRAPPED;
    }
}

static void op_adorn(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t result = vm->registers[dst] ^ vm->registers[src];
    vm->registers[dst] = result;
    vm->flag_zero = (result == 0);
    vm->flag_negative = (result & 0x80000000) != 0;
}

static void op_strip(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src] & 0xFF;
}

static void op_return(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    if (vm->registers[R_SP] < STACK_SIZE - 4) {
        uint32_t addr = vm->registers[R_SP];
        vm->pc = vm_read_u32(vm, addr);
        vm->registers[R_SP] += 4;
    } else {
        vm->state = VM_HALTED;
    }
}

static void op_intrinsic(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

static void op_barrier(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

static void op_nourish(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    vm->heap_ptr = vm->heap_base;
    memset(&vm->memory[vm->heap_base], 0, HEAP_SIZE);
}

static void op_overload(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    vm->state = VM_ERROR;
}

static void op_trap(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    vm->state = VM_TRAPPED;
}

static void op_illuminate(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t reg = operands[0] & 0x0F;
    printf("%u", vm->registers[reg]);
    fflush(stdout);
}

static void op_sense(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

static void op_persist(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

static void op_retreat(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    vm->state = VM_HALTED;
}

static void op_thrust(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

static void op_advance(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t reg = operands[0] & 0x0F;
    vm->registers[reg] = (vm->registers[reg] + 1) & 0xFFFFFFFF;
}

static void op_obscure(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t val = vm->registers[src];
    vm->registers[dst] = ~val;
}

static void op_bind(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

static void op_convert(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

static void op_lame(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

static void op_unlock(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint16_t lock_id = operands[0] & 0xFFFF;
    if (lock_id < MAX_LOCKS) {
        vm->memory[vm->heap_base + lock_id] = 0;
    }
}

static void op_reduce(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t result = (vm->registers[dst] - vm->registers[src]) & 0xFFFFFFFF;
    vm->registers[dst] = result;
    vm->flag_zero = (result == 0);
    vm->flag_negative = (result & 0x80000000) != 0;
}

static void op_increase(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t result = (vm->registers[dst] + vm->registers[src]) & 0xFFFFFFFF;
    vm->registers[dst] = result;
    vm->flag_zero = (result == 0);
    vm->flag_negative = (result & 0x80000000) != 0;
}

static void op_break(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    vm->state = VM_HALTED;
}

static void op_mate(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t result = ((vm->registers[dst] + vm->registers[src]) / 2) & 0xFFFFFFFF;
    vm->registers[dst] = result;
}

static void op_gather(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    uint32_t result = (vm->registers[dst] + vm->registers[src]) & 0xFFFFFFFF;
    vm->registers[dst] = result;
}

static void op_push_up(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t reg = operands[0] & 0x0F;
    uint32_t sp = vm->registers[R_SP];
    if (sp > 4) {
        sp -= 4;
        vm_write_u32(vm, sp, vm->registers[reg]);
        vm->registers[R_SP] = sp;
    }
}

static void op_trapped(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    vm->state = VM_ERROR;
}

static void op_well(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint32_t sp = vm->registers[R_SP];
    if (sp < STACK_SIZE - 4) {
        vm->registers[dst] = vm_read_u32(vm, sp);
        vm->registers[R_SP] = sp + 4;
    }
}

static void op_replace(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

static void op_cast(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t src = operands[1] & 0x0F;
    vm->registers[dst] = vm->registers[src];
}

static void op_shock(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

static void op_still(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    vm->state = VM_PAUSED;
}

static void op_gradual(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t reg = operands[0] & 0x0F;
    vm->registers[reg] = (vm->registers[reg] + 1) & 0xFFFFFFFF;
}

static void op_mismatch(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    (void)operands;
    vm->state = VM_ERROR;
}

static void op_abound(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t count = operands[1];
    vm->registers[dst] = count;
}

static void op_travel(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

static void op_penetrate(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t addr_reg = operands[0] & 0x0F;
    uint8_t dst = operands[1] & 0x0F;
    uint32_t addr = vm->registers[addr_reg];
    if (addr < VM_MEMORY_SIZE) {
        vm->registers[dst] = vm->memory[addr];
    }
}

static void op_joy(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

static void op_disperse(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t addr_reg = operands[0] & 0x0F;
    uint8_t val_reg = operands[1] & 0x0F;
    uint32_t addr = vm->registers[addr_reg];
    uint32_t val = vm->registers[val_reg];
    if (addr < VM_MEMORY_SIZE) {
        vm->memory[addr] = val & 0xFF;
    }
}

static void op_throttle(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

static void op_trust(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

static void op_micro(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    uint8_t dst = operands[0] & 0x0F;
    uint8_t val = operands[1];
    vm->registers[dst] = (vm->registers[dst] + val) & 0xFFFFFFFF;
}

static void op_sync(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)vm;
    (void)modifier;
    (void)operands;
}

static void op_futu(IChingVM *vm, uint8_t modifier, uint8_t *operands) {
    (void)modifier;
    static uint32_t future_id = 0;
    uint8_t dst = operands[0] & 0x0F;
    vm->registers[dst] = future_id++;
}

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

static VMState vm_run(IChingVM *vm, uint32_t max_cycles) {
    vm->state = VM_RUNNING;
    
    if (max_cycles == 0) {
        max_cycles = 1000000;
    }
    
    uint32_t cycles_remaining = max_cycles;
    uint32_t pc = vm->pc;
    uint8_t *memory = vm->memory;
    uint32_t *registers = vm->registers;
    uint32_t cycle_count = vm->cycle_count;
    double energy_cost = vm->energy_cost;
    
    while (vm->state == VM_RUNNING && cycles_remaining > 0) {
        if (pc + 3 >= 0x01000000) {
            vm->state = VM_HALTED;
            break;
        }
        
        uint8_t byte1 = memory[pc];
        uint8_t byte2 = memory[pc + 1];
        uint8_t operand1 = memory[pc + 2];
        uint8_t operand2 = memory[pc + 3];
        
        uint8_t opcode = decode_opcode(byte1);
        uint8_t modifier = decode_modifier(byte1, byte2);
        uint8_t operands[2] = {operand1, operand2};
        
        pc += 4;
        
        if (opcode < 64 && opcode_handlers[opcode]) {
            opcode_handlers[opcode](vm, modifier, operands);
        } else {
            vm->state = VM_ERROR;
            break;
        }
        
        cycle_count++;
        cycles_remaining--;
    }
    
    vm->pc = pc;
    vm->cycle_count = cycle_count;
    vm->energy_cost = energy_cost;
    
    return vm->state;
}

static uint8_t* vm_read_raw_file(const char *filename, uint32_t *out_size) {
    FILE *f = fopen(filename, "rb");
    if (!f) return NULL;
    
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

static void vm_dump_state(IChingVM *vm) {
    printf("\n=== VM State ===\n");
    printf("PC: 0x%08X\n", vm->pc);
    printf("State: %d\n", vm->state);
    printf("Cycles: %u\n", vm->cycle_count);
    printf("\nRegisters:\n");
    for (int i = 0; i < NUM_REGISTERS; i++) {
        printf("  R%d: 0x%08X (%u)", i, vm->registers[i], vm->registers[i]);
        if (i == R_FP) printf(" [FP]");
        if (i == R_SP) printf(" [SP]");
        if (i == R_LR) printf(" [LR]");
        if (i == R_A0) printf(" [A0]");
        printf("\n");
    }
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
    while (*p && isspace((unsigned char)*p)) p++;
    return p;
}

static char* read_token(char *p, char *buf, int bufsize) {
    int i = 0;
    p = skip_whitespace(p);
    while (*p && !isspace((unsigned char)*p) && *p != ',' && *p != ';' && *p != '#' && i < bufsize - 1) {
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

static int assemble_file(const char *input_file, const char *output_file) {
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

static void print_usage(const char *prog) {
    printf("IChingVM Bootstrap v2.0 - 易衍自举虚拟机\n");
    printf("========================================\n");
    printf("Usage: %s <command> [options]\n", prog);
    printf("\nCommands:\n");
    printf("  run <program.raw> [max_cycles]  - 运行原始字节码\n");
    printf("  asm <input.asm> <output.raw>     - 汇编文本到字节码\n");
    printf("  help                              - 显示帮助\n");
    printf("\n系统调用:\n");
    printf("  RECV R0, 0  - 调用系统调用 (R0=调用号)\n");
    printf("    SYSCALL_OPEN    = 0  (R1=filename, R2=mode)\n");
    printf("    SYSCALL_READ    = 1  (R1=fd, R2=buf, R3=count)\n");
    printf("    SYSCALL_WRITE   = 2  (R1=fd, R2=buf, R3=count)\n");
    printf("    SYSCALL_CLOSE   = 3  (R1=fd)\n");
    printf("    SYSCALL_MALLOC  = 10 (R1=size)\n");
    printf("    SYSCALL_STRLEN  = 20 (R1=str)\n");
    printf("    SYSCALL_STRCMP  = 21 (R1=s1, R2=s2)\n");
    printf("    SYSCALL_ISDIGIT = 30 (R1=char)\n");
    printf("    SYSCALL_ISALPHA = 31 (R1=char)\n");
    printf("    SYSCALL_PRINT   = 40 (R1=str)\n");
    printf("    SYSCALL_EXIT    = 255\n");
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
        
        uint32_t load_addr = 0;
        for (uint32_t i = 0; i < program_size && i < 0x10000; i++) {
            vm.memory[load_addr + i] = program[i];
        }
        vm.pc = load_addr;
        
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
            default: printf("UNKNOWN(%d)", state);
        }
        printf("\n");
        
        vm_dump_state(&vm);
        
        free(program);
        vm_free(&vm);
        return 0;
    }
    
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
    
    uint32_t load_addr = 0;
    for (uint32_t i = 0; i < program_size && i < 0x10000; i++) {
        vm.memory[load_addr + i] = program[i];
    }
    vm.pc = load_addr;
    
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
        default: printf("UNKNOWN(%d)", state);
    }
    printf("\n");
    
    vm_dump_state(&vm);
    
    free(program);
    vm_free(&vm);
    return 0;
}
