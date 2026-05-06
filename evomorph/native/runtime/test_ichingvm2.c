#include "ichingvm2.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

static int test_basic_assemble_run(void) {
    printf("Test 1: Basic assemble and run... ");
    IChingVM2 *vm = ichingvm2_create();
    const char *asm_src =
        "CREA.1 R0, R0, #42\n"
        "CREA.1 R1, R1, #8\n"
        "GATHER.0 R0, R1\n"
        "RETURN.1 R0, R0\n";
    uint32_t size = ichingvm2_assemble(vm, asm_src);
    assert(size > 0);
    vm->pc = 0;
    vm->state = ICHINGVM2_RUNNING;
    ichingvm2_run(vm, 1000);
    assert(vm->state == ICHINGVM2_HALTED);
    assert(vm->regs[0] == 50);
    printf("PASSED (R0=%u)\n", vm->regs[0]);
    ichingvm2_destroy(vm);
    return 0;
}

static int test_branch(void) {
    printf("Test 2: Conditional branch... ");
    IChingVM2 *vm = ichingvm2_create();
    const char *asm_src =
        "CREA.1 R0, R0, #10\n"
        "CREA.1 R1, R1, #10\n"
        "FELLOWSHIP.1 R0, R1\n"
        "BRANCH.2 @equal\n"
        "CREA.1 R2, R2, #0\n"
        "RETURN.1 R0, R0\n"
        "equal:\n"
        "CREA.1 R2, R2, #1\n"
        "RETURN.1 R0, R0\n";
    uint32_t size = ichingvm2_assemble(vm, asm_src);
    assert(size > 0);
    vm->pc = 0;
    vm->state = ICHINGVM2_RUNNING;
    ichingvm2_run(vm, 1000);
    assert(vm->state == ICHINGVM2_HALTED);
    assert(vm->regs[2] == 1);
    printf("PASSED (R2=%u)\n", vm->regs[2]);
    ichingvm2_destroy(vm);
    return 0;
}

static int test_call_ret(void) {
    printf("Test 3: CALL/RET... ");
    IChingVM2 *vm = ichingvm2_create();
    const char *asm_src =
        "BRANCH.1 @main\n"
        "add_func:\n"
        "GATHER.0 R0, R1\n"
        "RETURN.0 R0, R0\n"
        "main:\n"
        "CREA.1 R0, R0, #20\n"
        "CREA.1 R1, R1, #22\n"
        "ABUNDANCE.1 R0, R0, @add_func\n"
        "RETURN.1 R0, R0\n";
    uint32_t size = ichingvm2_assemble(vm, asm_src);
    assert(size > 0);
    vm->pc = 0;
    vm->state = ICHINGVM2_RUNNING;
    ichingvm2_run(vm, 1000);
    assert(vm->state == ICHINGVM2_HALTED);
    assert(vm->regs[0] == 42);
    printf("PASSED (R0=%u)\n", vm->regs[0]);
    ichingvm2_destroy(vm);
    return 0;
}

static int test_memory_ops(void) {
    printf("Test 4: Memory operations... ");
    IChingVM2 *vm = ichingvm2_create();
    const char *asm_src =
        "CREA.1 R0, R0, #0x1000\n"
        "CREA.1 R1, R1, #0xDEADBEEF\n"
        "ALLOC.1 R0, R1\n"
        "RECV.1 R2, R0\n"
        "RETURN.1 R0, R0\n";
    uint32_t size = ichingvm2_assemble(vm, asm_src);
    assert(size > 0);
    vm->pc = 0;
    vm->state = ICHINGVM2_RUNNING;
    ichingvm2_run(vm, 1000);
    assert(vm->state == ICHINGVM2_HALTED);
    assert(vm->regs[2] == 0xDEADBEEF);
    printf("PASSED (R2=0x%X)\n", vm->regs[2]);
    ichingvm2_destroy(vm);
    return 0;
}

static int test_push_pop(void) {
    printf("Test 5: PUSH/POP... ");
    IChingVM2 *vm = ichingvm2_create();
    const char *asm_src =
        "CREA.1 R0, R0, #123\n"
        "PUSH_UP.1 R0, R0\n"
        "CREA.1 R0, R0, #0\n"
        "WELL.1 R0, R0\n"
        "RETURN.1 R0, R0\n";
    uint32_t size = ichingvm2_assemble(vm, asm_src);
    assert(size > 0);
    vm->pc = 0;
    vm->state = ICHINGVM2_RUNNING;
    ichingvm2_run(vm, 1000);
    assert(vm->state == ICHINGVM2_HALTED);
    assert(vm->regs[0] == 123);
    printf("PASSED (R0=%u)\n", vm->regs[0]);
    ichingvm2_destroy(vm);
    return 0;
}

static int test_loop(void) {
    printf("Test 6: Loop (sum 1..10)... ");
    IChingVM2 *vm = ichingvm2_create();
    const char *asm_src =
        "CREA.1 R0, R0, #0\n"
        "CREA.1 R1, R1, #1\n"
        "loop:\n"
        "FELLOWSHIP.2 R1, R1, #11\n"
        "BRANCH.2 @done\n"
        "GATHER.0 R0, R1\n"
        "MICRO.1 R1, R1\n"
        "BRANCH.1 @loop\n"
        "done:\n"
        "RETURN.1 R0, R0\n";
    uint32_t size = ichingvm2_assemble(vm, asm_src);
    assert(size > 0);
    vm->pc = 0;
    vm->state = ICHINGVM2_RUNNING;
    ichingvm2_run(vm, 10000);
    assert(vm->state == ICHINGVM2_HALTED);
    assert(vm->regs[0] == 55);
    printf("PASSED (R0=%u)\n", vm->regs[0]);
    ichingvm2_destroy(vm);
    return 0;
}

static int test_string_ops(void) {
    printf("Test 7: String load/read... ");
    IChingVM2 *vm = ichingvm2_create();
    ichingvm2_load_string(vm, 0x1000, "Hello Evomorph!");
    char buf[64] = {0};
    ichingvm2_read_string(vm, 0x1000, buf, sizeof(buf));
    assert(strcmp(buf, "Hello Evomorph!") == 0);
    printf("PASSED ('%s')\n", buf);
    ichingvm2_destroy(vm);
    return 0;
}

static int test_native_instructions(void) {
    printf("Test 8: Native CPU instructions... ");
    IChingVM2 *vm = ichingvm2_create();
    const char *asm_src =
        "MOVI R0, #100\n"
        "MOVI R1, #50\n"
        "SUB R0, R1\n"
        "HLT\n";
    uint32_t size = ichingvm2_assemble(vm, asm_src);
    assert(size > 0);
    vm->pc = 0;
    vm->state = ICHINGVM2_RUNNING;
    ichingvm2_run(vm, 1000);
    assert(vm->state == ICHINGVM2_HALTED);
    assert(vm->regs[0] == 50);
    printf("PASSED (R0=%u)\n", vm->regs[0]);
    ichingvm2_destroy(vm);
    return 0;
}

static int test_evob_load(void) {
    printf("Test 9: EVOB load... ");
    IChingVM2 *vm = ichingvm2_create();
    uint8_t evob[68];
    memset(evob, 0, sizeof(evob));
    evob[0]='E'; evob[1]='V'; evob[2]='O'; evob[3]='B';
    evob[4]=0x00; evob[5]=0x03;
    evob[6]=0x00; evob[7]=0x40;
    evob[8]=0x00; evob[9]=0x01;
    evob[64]=0x80; evob[65]=0x3F; evob[66]=0x00; evob[67]=0x00;
    int r = ichingvm2_load_evob(vm, evob, sizeof(evob));
    assert(r == 0);
    assert(vm->program_size == 4);
    printf("PASSED\n");
    ichingvm2_destroy(vm);
    return 0;
}

static int test_syscall(void) {
    printf("Test 10: Syscall (print string)... ");
    IChingVM2 *vm = ichingvm2_create();
    ichingvm2_load_string(vm, 0x1000, "Hello from C VM!");
    const char *asm_src =
        "CREA.1 R0, R0, #1\n"
        "CREA.1 R1, R1, #0x1000\n"
        "SHOCK.1 R0, R0, #0x80\n"
        "RETURN.1 R0, R0\n";
    uint32_t size = ichingvm2_assemble(vm, asm_src);
    assert(size > 0);
    vm->pc = 0;
    vm->state = ICHINGVM2_RUNNING;
    ichingvm2_run(vm, 1000);
    assert(vm->state == ICHINGVM2_HALTED);
    const char *out = ichingvm2_get_output(vm);
    assert(strcmp(out, "Hello from C VM!") == 0);
    printf("PASSED ('%s')\n", out);
    ichingvm2_destroy(vm);
    return 0;
}

int main(void) {
    printf("=== IChingVM2 C Implementation Tests ===\n\n");
    int failures = 0;
    failures += test_basic_assemble_run();
    failures += test_branch();
    failures += test_call_ret();
    failures += test_memory_ops();
    failures += test_push_pop();
    failures += test_loop();
    failures += test_string_ops();
    failures += test_native_instructions();
    failures += test_evob_load();
    failures += test_syscall();
    printf("\n=== Results: %d failures ===\n", failures);
    return failures;
}
