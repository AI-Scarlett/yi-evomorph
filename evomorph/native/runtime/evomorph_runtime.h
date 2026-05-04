/*
 * Evomorph 原生运行时头文件
 * 基于六十四卦指令集的进化编程运行时
 */

#ifndef EVOMORPH_RUNTIME_H
#define EVOMORPH_RUNTIME_H

#include <stdint.h>
#include <stddef.h>

/* 编译平台检测 */
#if defined(_WIN32) || defined(_WIN64)
#define EVO_WINDOWS 1
#include <windows.h>
#else
#define EVO_POSIX 1
#include <pthread.h>
#include <unistd.h>
#endif

/* 导出/导入符号 */
#if defined(EVO_BUILD_SHARED) && defined(EVO_WINDOWS)
#define EVO_API __declspec(dllexport)
#elif defined(EVO_USE_SHARED) && defined(EVO_WINDOWS)
#define EVO_API __declspec(dllimport)
#else
#define EVO_API
#endif

/* 线程本地存储 */
#if defined(EVO_WINDOWS)
#define EVO_TLS __declspec(thread)
#else
#define EVO_TLS __thread
#endif

/* 内联函数 */
#define EVO_INLINE static inline

/* 向量类型 */
typedef float evo_vec4f __attribute__((vector_size(16)));
typedef int32_t evo_vec4i __attribute__((vector_size(16)));

/* 布尔类型 */
typedef int evo_bool;
#define evo_true 1
#define evo_false 0

/* 版本信息 */
#define EVO_VERSION_MAJOR 3
#define EVO_VERSION_MINOR 0
#define EVO_VERSION_PATCH 0

/* 虚拟机常量 */
#define EVO_NUM_REGISTERS 16
#define EVO_STACK_SIZE 65536
#define EVO_HEAP_SIZE (16 * 1024 * 1024)
#define EVO_MAX_LOCKS 256
#define EVO_MAX_BARRIERS 256
#define EVO_MAX_FUTURES 1024

/* 进化引擎常量 */
#define EVO_MAX_POPULATION 65536
#define EVO_MAX_INDIVIDUAL_SIZE 65536
#define EVO_MAX_GENERATIONS 1000000

/* 特殊寄存器 */
#define EVO_R_FP 12
#define EVO_R_SP 13
#define EVO_R_LR 14
#define EVO_R_A0 15

/* 操作码 */
typedef enum {
    EVO_OP_RECV = 0,
    EVO_OP_RETURN = 1,
    EVO_OP_BRANCH = 2,
    EVO_OP_APPROACH = 3,
    EVO_OP_YIELD = 4,
    EVO_OP_OBSCURE = 5,
    EVO_OP_PUSH_UP = 6,
    EVO_OP_FLUSH = 7,
    EVO_OP_SPECULATE = 8,
    EVO_OP_SHOCK = 9,
    EVO_OP_UNLOCK = 10,
    EVO_OP_MISMATCH = 11,
    EVO_OP_MICRO = 12,
    EVO_OP_ABOUND = 13,
    EVO_OP_PERSIST = 14,
    EVO_OP_THRUST = 15,
    EVO_OP_MERGE = 16,
    EVO_OP_ALLOC = 17,
    EVO_OP_TRAP = 18,
    EVO_OP_THROTTLE = 19,
    EVO_OP_LAME = 20,
    EVO_OP_SYNC = 21,
    EVO_OP_WELL = 22,
    EVO_OP_WAIT = 23,
    EVO_OP_GATHER = 24,
    EVO_OP_FOLLOWING = 25,
    EVO_OP_TRAPPED = 26,
    EVO_OP_JOY = 27,
    EVO_OP_SENSE = 28,
    EVO_OP_REPLACE = 29,
    EVO_OP_OVERLOAD = 30,
    EVO_OP_BREAK = 31,
    EVO_OP_STRIP = 32,
    EVO_OP_NOURISH = 33,
    EVO_OP_SPRT = 34,
    EVO_OP_REDUCE = 35,
    EVO_OP_STILL = 36,
    EVO_OP_ADORN = 37,
    EVO_OP_MUT = 38,
    EVO_OP_BARRIER = 39,
    EVO_OP_ADVANCE = 40,
    EVO_OP_BITE = 41,
    EVO_OP_FUTU = 42,
    EVO_OP_CONVERT = 43,
    EVO_OP_TRAVEL = 44,
    EVO_OP_ILLUMINATE = 45,
    EVO_OP_CAST = 46,
    EVO_OP_ABUNDANCE = 47,
    EVO_OP_CONTEMPLATE = 48,
    EVO_OP_INCREASE = 49,
    EVO_OP_DISPERSE = 50,
    EVO_OP_TRUST = 51,
    EVO_OP_GRADUAL = 52,
    EVO_OP_BIND = 53,
    EVO_OP_PENETRATE = 54,
    EVO_OP_PREFETCH = 55,
    EVO_OP_HALT = 56,
    EVO_OP_INTRINSIC = 57,
    EVO_OP_LOCK = 58,
    EVO_OP_STEP = 59,
    EVO_OP_RETREAT = 60,
    EVO_OP_FELLOWSHIP = 61,
    EVO_OP_MATE = 62,
    EVO_OP_CREA = 63
} EvoOpcode;

/* 修饰符 */
typedef enum {
    EVO_MOD_ASYNC = 0x20,
    EVO_MOD_ATOMIC = 0x10,
    EVO_MOD_PRIV = 0x08,
    EVO_MOD_WEAK = 0x04,
    EVO_MOD_STRONG = 0x02,
    EVO_MOD_VOLATILE = 0x01
} EvoModifier;

/* VM状态 */
typedef enum {
    EVO_VM_INIT = 0,
    EVO_VM_RUNNING = 1,
    EVO_VM_PAUSED = 2,
    EVO_VM_HALTED = 3,
    EVO_VM_ERROR = 4,
    EVO_VM_TRAPPED = 5
} EvoVMState;

/* 选择方法 */
typedef enum {
    EVO_SELECT_ROULETTE = 0,
    EVO_SELECT_TOURNAMENT = 1,
    EVO_SELECT_RANK = 2
} EvoSelectionMethod;

/* 交叉方法 */
typedef enum {
    EVO_CROSS_SINGLE_POINT = 0,
    EVO_CROSS_TWO_POINT = 1,
    EVO_CROSS_UNIFORM = 2
} EvoCrossoverMethod;

/* 错误码 */
typedef enum {
    EVO_OK = 0,
    EVO_ERROR_INVALID_ARG = -1,
    EVO_ERROR_OUT_OF_MEMORY = -2,
    EVO_ERROR_INVALID_OPCODE = -3,
    EVO_ERROR_STACK_OVERFLOW = -4,
    EVO_ERROR_HEAP_OVERFLOW = -5,
    EVO_ERROR_PROGRAM_TOO_LARGE = -6,
    EVO_ERROR_FILE_NOT_FOUND = -7,
    EVO_ERROR_INVALID_FORMAT = -8,
    EVO_ERROR_EVOLUTION_FAILED = -9,
    EVO_ERROR_CONVERGENCE = -10
} EvoError;

/* 基因指令 */
typedef struct {
    uint8_t opcode;
    uint8_t modifier;
    uint8_t operands[2];
} EvoGeneInstruction;

/* 个体 */
typedef struct {
    EvoGeneInstruction* genes;
    size_t num_genes;
    double fitness;
    uint32_t age;
    uint32_t origin;
    double* platform_scores;
    size_t num_platforms;
} EvoIndividual;

/* 种群 */
typedef struct {
    EvoIndividual* individuals;
    size_t size;
    size_t capacity;
} EvoPopulation;

/* 进化配置 */
typedef struct {
    size_t population_size;
    uint32_t max_generations;
    double mut_rate;
    double crossover_rate;
    size_t elite_count;
    EvoSelectionMethod selection_method;
    EvoCrossoverMethod crossover_method;
    size_t tournament_size;
    double fitness_weights[4];
    char** env_targets;
    size_t num_env_targets;
    char* cross_pool;
} EvoEvolutionConfig;

/* 未来值 */
typedef struct {
    uint8_t resolved;
    uint32_t value;
} EvoFuture;

/* 虚拟机 */
typedef struct {
    uint32_t registers[EVO_NUM_REGISTERS];
    uint8_t* stack;
    uint8_t* heap;
    uint32_t heap_ptr;
    uint32_t pc;
    EvoVMState state;
    uint8_t* program;
    uint32_t program_len;
    
    uint8_t flag_zero;
    uint8_t flag_carry;
    uint8_t flag_negative;
    uint8_t flag_overflow;
    
    uint32_t future_id_counter;
    uint8_t locks[EVO_MAX_LOCKS];
    uint32_t barriers[EVO_MAX_BARRIERS];
    EvoFuture futures[EVO_MAX_FUTURES];
    
    uint64_t cycle_count;
    double energy_cost;
    
    /* 进化引擎状态 */
    EvoPopulation* population;
    EvoEvolutionConfig* evo_config;
    uint32_t current_generation;
    EvoIndividual* best_ever;
    
    /* 随机数生成器状态 */
    uint64_t rng_state[2];
} EvoVM;

/* 操作码处理器函数类型 */
typedef void (*EvoOpHandler)(EvoVM*, uint8_t, uint8_t*);

#ifdef __cplusplus
extern "C" {
#endif

/* 虚拟机API */
EVO_API EvoVM* evo_vm_create(void);
EVO_API void evo_vm_destroy(EvoVM* vm);
EVO_API void evo_vm_init(EvoVM* vm);
EVO_API void evo_vm_reset(EvoVM* vm);
EVO_API EvoError evo_vm_load_program(EvoVM* vm, const uint8_t* program, uint32_t len);
EVO_API EvoVMState evo_vm_run(EvoVM* vm, uint64_t max_cycles);
EVO_API void evo_vm_step(EvoVM* vm);
EVO_API void evo_vm_dump_state(const EvoVM* vm);

/* 进化引擎API */
EVO_API EvoEvolutionConfig* evo_config_create(void);
EVO_API void evo_config_destroy(EvoEvolutionConfig* config);
EVO_API EvoPopulation* evo_population_create(size_t capacity);
EVO_API void evo_population_destroy(EvoPopulation* pop);
EVO_API EvoIndividual* evo_individual_create(size_t num_genes);
EVO_API void evo_individual_destroy(EvoIndividual* ind);
EVO_API EvoIndividual* evo_individual_clone(const EvoIndividual* ind);

/* 进化算子 */
EVO_API void evo_mutation_flip_yao(EvoGeneInstruction* gene, uint8_t position);
EVO_API void evo_mutation_modifier(EvoGeneInstruction* gene);
EVO_API void evo_crossover_single_point(const EvoIndividual* p1, const EvoIndividual* p2,
                                         EvoIndividual* c1, EvoIndividual* c2);
EVO_API void evo_crossover_two_point(const EvoIndividual* p1, const EvoIndividual* p2,
                                      EvoIndividual* c1, EvoIndividual* c2);
EVO_API void evo_crossover_uniform(const EvoIndividual* p1, const EvoIndividual* p2,
                                    EvoIndividual* c1, EvoIndividual* c2);

/* 选择算法 */
EVO_API size_t evo_select_roulette(const EvoPopulation* pop, uint64_t* rng_state);
EVO_API size_t evo_select_tournament(const EvoPopulation* pop, size_t tournament_size,
                                      uint64_t* rng_state);
EVO_API size_t evo_select_rank(const EvoPopulation* pop, uint64_t* rng_state);

/* 主进化循环 */
EVO_API EvoError evo_initialize_population(EvoVM* vm, const EvoGeneInstruction* seed_genes,
                                            size_t num_seed_genes);
EVO_API double evo_evaluate_fitness(const EvoVM* vm, EvoIndividual* ind);
EVO_API EvoError evo_evolve_one_generation(EvoVM* vm);
EVO_API const EvoIndividual* evo_evolve(EvoVM* vm, uint32_t max_generations);

/* 随机数生成 */
EVO_INLINE uint64_t evo_rng_next(uint64_t* state);
EVO_INLINE double evo_rng_next_double(uint64_t* state);
EVO_INLINE uint32_t evo_rng_next_uint32(uint64_t* state, uint32_t max);

/* 字节码工具 */
EVO_API uint8_t* evo_read_raw_file(const char* filename, uint32_t* out_size);
EVO_API int evo_assemble_file(const char* input_file, const char* output_file);

/* 版本信息 */
EVO_API const char* evo_version_string(void);
EVO_API void evo_get_version(int* major, int* minor, int* patch);

/* 内联函数实现 */
EVO_INLINE uint64_t evo_rng_next(uint64_t* state) {
    uint64_t s0 = state[0];
    uint64_t s1 = state[1];
    uint64_t result = s0 + s1;
    s1 ^= s0;
    state[0] = ((s0 << 55) | (s0 >> 9)) ^ s1 ^ (s1 << 14);
    state[1] = (s1 << 36) | (s1 >> 28);
    return result;
}

EVO_INLINE double evo_rng_next_double(uint64_t* state) {
    uint64_t x = evo_rng_next(state);
    return (x >> 11) * (1.0 / 9007199254740992.0);
}

EVO_INLINE uint32_t evo_rng_next_uint32(uint64_t* state, uint32_t max) {
    if (max == 0) return 0;
    uint64_t threshold = (UINT64_MAX - (uint64_t)max + 1) % (uint64_t)max;
    uint64_t x;
    do {
        x = evo_rng_next(state);
    } while (x < threshold);
    return (uint32_t)(x % (uint64_t)max);
}

#ifdef __cplusplus
}
#endif

#endif /* EVOMORPH_RUNTIME_H */
