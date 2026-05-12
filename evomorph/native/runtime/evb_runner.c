/*
 * EVB Runner - 独立的 EVB v3 / ExtendedVM2 字节码执行器
 * 基于 ichingvm2.c，提供命令行接口
 * 
 * 用法: ./evb_runner <file.evob|file.raw>
 *   .evob - EVB v3 格式文件 (带 header)
 *   .raw  - 裸字节码文件
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ichingvm2.h"

/* 测试程序: CREA.1 R0, #42; HALT
 * 执行后 R0 应为 42，VM 状态为 HALTED
 */
static uint8_t test_program[] = {
    0xBF, 0x81, 0x00, 0x00, 0x2A, 0x00, 0x00, 0x00,  /* CREA.1 R0, #42 */
    0xB8, 0x00, 0x00, 0x00                             /* HALT */
};

/* 复杂测试程序: 计算 1+2+...+10 = 55
 * R0=0, R1=1, R2=10
 * loop: R0 = R0 + R1, R1 = R1 + 1, if R1 <= R2 goto loop
 * R0 should be 55
 *
 * CREA.1 R0, #0       ; R0 = 0
 * CREA.1 R1, #1       ; R1 = 1  
 * CREA.1 R2, #10      ; R2 = 10
 * GATHER.0 R0, R1     ; R0 = R0 + R1
 * GRADUAL.0 R1        ; R1 = R1 + 1
 * FELLOWSHIP.1 R1, R2 ; compare R1 <= R2 (sets flags)
 * BRANCH.5 @loop      ; if R1 <= R2, jump to GATHER
 * HALT
 */
static uint8_t sum_test_program[] = {
    0xBF, 0x81, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  /* CREA.1 R0, #0 */
    0xBF, 0x81, 0x01, 0x00, 0x01, 0x00, 0x00, 0x00,  /* CREA.1 R1, #1 */
    0xBF, 0x81, 0x02, 0x00, 0x0A, 0x00, 0x00, 0x00,  /* CREA.1 R2, #10 */
    0x98, 0x40, 0x00, 0x01,                          /* GATHER.0 R0, R1  (sub_op=0, ext_mode=1) */
    0xB4, 0x40, 0x01, 0x00,                          /* GRADUAL.0 R1       (sub_op=0, ext_mode=1) */
    0xBD, 0x41, 0x01, 0x02,                          /* FELLOWSHIP.1 R1, R2 (sub_op=1, ext_mode=1) */
    0x82, 0x85, 0x00, 0x00,                          /* BRANCH.5 back to offset 24 (GATHER) -- sub_op=5: ble, ext_mode=2 */
    0x18, 0x00, 0x00, 0x00,                          /* imm32_le = 24 (offset of GATHER.0) */
    0xB8, 0x00, 0x00, 0x00                           /* HALT */
};

static uint8_t *read_file(const char *filename, uint32_t *out_size) {
    FILE *f = fopen(filename, "rb");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (size <= 0) { fclose(f); return NULL; }
    uint8_t *buf = (uint8_t *)malloc((size_t)size);
    if (!buf) { fclose(f); return NULL; }
    if (fread(buf, 1, (size_t)size, f) != (size_t)size) {
        free(buf); fclose(f); return NULL;
    }
    fclose(f);
    *out_size = (uint32_t)size;
    return buf;
}

static void run_test(const char *name, uint8_t *prog, uint32_t size,
                     uint32_t expected_r0, uint32_t max_cycles) {
    printf("\n=== Test: %s ===\n", name);
    printf("  Program size: %u bytes\n", size);
    
    IChingVM2 *vm = ichingvm2_create();
    if (!vm) {
        printf("  [FAIL] Failed to create VM\n");
        return;
    }
    
    if (ichingvm2_load_program(vm, prog, size) != 0) {
        printf("  [FAIL] Failed to load program\n");
        ichingvm2_destroy(vm);
        return;
    }
    
    int ret = ichingvm2_run(vm, max_cycles);
    const char *state_str = "UNKNOWN";
    switch (vm->state) {
        case ICHINGVM2_HALTED: state_str = "HALTED"; break;
        case ICHINGVM2_ERROR:  state_str = "ERROR"; break;
        case ICHINGVM2_PAUSED: state_str = "PAUSED"; break;
        default: break;
    }
    
    printf("  State: %s, Cycles: %llu, Exit code: %d\n",
           state_str, (unsigned long long)vm->cycle_count, ret);
    printf("  R0 = %u (expected: %u)\n", vm->regs[0], expected_r0);
    
    if (vm->state == ICHINGVM2_HALTED && vm->regs[0] == expected_r0) {
        printf("  [PASS] Test passed!\n");
    } else {
        printf("  [FAIL] Test failed!\n");
        printf("  All registers:\n");
        for (int i = 0; i < 16; i++) {
            printf("    R%d = %u\n", i, vm->regs[i]);
        }
    }
    
    ichingvm2_destroy(vm);
}

static void run_file(const char *filename, uint32_t max_cycles) {
    uint32_t size = 0;
    uint8_t *data = read_file(filename, &size);
    if (!data) {
        printf("Error: Cannot read file '%s'\n", filename);
        return;
    }
    
    IChingVM2 *vm = ichingvm2_create();
    if (!vm) {
        printf("Error: Failed to create VM\n");
        free(data);
        return;
    }
    
    int ret;
    const char *ext = strrchr(filename, '.');
    if (ext && strcmp(ext, ".evob") == 0) {
        ret = ichingvm2_load_evob(vm, data, size);
        printf("Loading EVB file: %s (%u bytes, header stripped)\n", filename, size);
    } else {
        ret = ichingvm2_load_program(vm, data, size);
        printf("Loading raw bytecode: %s (%u bytes)\n", filename, size);
    }
    
    if (ret != 0) {
        printf("Error: Failed to load program\n");
        goto cleanup;
    }
    
    printf("Running...\n");
    ret = ichingvm2_run(vm, max_cycles);
    
    printf("State: %d, Cycles: %llu, Exit: %d\n",
           vm->state, (unsigned long long)vm->cycle_count, ret);
    
    printf("Registers:\n");
    for (int i = 0; i < 16; i++) {
        printf("  R%d = %u (0x%08X)\n", i, vm->regs[i], vm->regs[i]);
    }
    if (vm->regs[ICHINGVM2_SP_REG] != ICHINGVM2_STACK_SIZE) {
        printf("  SP = %u\n", vm->regs[ICHINGVM2_SP_REG]);
    }
    if (vm->regs[ICHINGVM2_LR_REG] != 0) {
        printf("  LR = %u\n", vm->regs[ICHINGVM2_LR_REG]);
    }
    
    const char *output = ichingvm2_get_output(vm);
    if (output && output[0]) {
        printf("Output: %s\n", output);
    }
    
cleanup:
    ichingvm2_destroy(vm);
    free(data);
}

static void run_self_test(void) {
    printf("=== EVB Runner Self-Test ===\n");
    printf("Testing ichingvm2 C runtime...\n");
    
    /* Test 1: Simple register set */
    run_test("Set R0 = 42", test_program, sizeof(test_program), 42, 1000);
    
    /* Test 2: Sum 1..10 = 55 */
    run_test("Sum 1..10 = 55", sum_test_program, sizeof(sum_test_program), 55, 100000);
}

int main(int argc, char **argv) {
    printf("EVB Runner v1.0 - Native C Runtime for ExtendedVM2\n");
    printf("Based on ichingvm2.c\n\n");
    
    if (argc < 2) {
        printf("Running self-tests...\n");
        run_self_test();
    } else if (strcmp(argv[1], "--test") == 0 || strcmp(argv[1], "-t") == 0) {
        run_self_test();
    } else if (strcmp(argv[1], "--help") == 0 || strcmp(argv[1], "-h") == 0) {
        printf("Usage: evb_runner [options] <file>\n");
        printf("  <file.evob>  Run EVB v3 bytecode file\n");
        printf("  <file.raw>   Run raw bytecode file\n");
        printf("  --test, -t   Run self-tests\n");
        printf("  --help, -h   Show this help\n");
    } else {
        run_file(argv[1], 10000000);
    }
    
    return 0;
}
