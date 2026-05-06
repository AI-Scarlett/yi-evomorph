#ifndef ICHINGVM2_H
#define ICHINGVM2_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ICHINGVM2_NUM_REGS    32
#define ICHINGVM2_STACK_SIZE  65536
#define ICHINGVM2_HEAP_SIZE   1048576
#define ICHINGVM2_MAX_PROGRAM 2097152
#define ICHINGVM2_MAX_LABELS  4096
#define ICHINGVM2_MAX_CALLS   4096

#define ICHINGVM2_SP_REG  29
#define ICHINGVM2_FP_REG  28
#define ICHINGVM2_LR_REG  30

typedef enum {
    ICHINGVM2_INIT = 0,
    ICHINGVM2_RUNNING = 1,
    ICHINGVM2_PAUSED = 2,
    ICHINGVM2_HALTED = 3,
    ICHINGVM2_ERROR = 4
} IChingVM2State;

typedef struct {
    uint32_t regs[ICHINGVM2_NUM_REGS];
    uint8_t  *heap;
    uint8_t  *stack;
    uint8_t  *program;
    uint32_t  program_size;
    uint32_t  pc;
    uint32_t  heap_ptr;
    IChingVM2State state;
    uint64_t  cycle_count;
    double    energy_cost;

    int       flag_zero;
    int       flag_carry;
    int       flag_negative;
    int       flag_overflow;
    int       flag_direction;
    int       flag_interrupt;

    uint32_t  call_stack[ICHINGVM2_MAX_CALLS];
    int       call_stack_top;

    char      output_buffer[65536];
    uint32_t  output_len;
} IChingVM2;

typedef void (*IChingVM2_SyscallHandler)(IChingVM2 *vm);

IChingVM2 *ichingvm2_create(void);
void       ichingvm2_destroy(IChingVM2 *vm);
void       ichingvm2_reset(IChingVM2 *vm);
int        ichingvm2_step(IChingVM2 *vm);
int        ichingvm2_run(IChingVM2 *vm, uint64_t max_cycles);
int        ichingvm2_load_program(IChingVM2 *vm, const uint8_t *data, uint32_t size);
int        ichingvm2_load_evob(IChingVM2 *vm, const uint8_t *data, uint32_t size);
int        ichingvm2_load_string(IChingVM2 *vm, uint32_t addr, const char *s);
void       ichingvm2_read_string(IChingVM2 *vm, uint32_t addr, char *buf, uint32_t buf_size);
uint32_t   ichingvm2_assemble(IChingVM2 *vm, const char *asm_source);
int        ichingvm2_load_assembled(IChingVM2 *vm, const char *asm_source);
void       ichingvm2_register_syscall(IChingVM2 *vm, int num, IChingVM2_SyscallHandler handler);
const char *ichingvm2_get_output(IChingVM2 *vm);
void       ichingvm2_clear_output(IChingVM2 *vm);

uint32_t   ichingvm2_load_word(IChingVM2 *vm, uint32_t addr);
void       ichingvm2_store_word(IChingVM2 *vm, uint32_t addr, uint32_t val);

#ifdef __cplusplus
}
#endif

#endif
