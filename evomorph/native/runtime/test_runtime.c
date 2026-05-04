/*
 * Evomorph 原生运行时测试程序
 * 测试虚拟机和进化引擎的基本功能
 */

#include <stdio.h>
#include <stdlib.h>
#include "evomorph_runtime.h"

static void test_vm_basic(void) {
    printf("\n=== 测试虚拟机基本功能 ===\n");
    
    EvoVM* vm = evo_vm_create();
    if (!vm) {
        printf("ERROR: 无法创建虚拟机\n");
        return;
    }
    
    printf("✓ 虚拟机创建成功\n");
    printf("  版本: %s\n", evo_version_string());
    
    int major, minor, patch;
    evo_get_version(&major, &minor, &patch);
    printf("  版本号: %d.%d.%d\n", major, minor, patch);
    
    evo_vm_dump_state(vm);
    
    evo_vm_destroy(vm);
    printf("✓ 虚拟机销毁成功\n");
}

static void test_evolution_config(void) {
    printf("\n=== 测试进化配置 ===\n");
    
    EvoEvolutionConfig* config = evo_config_create();
    if (!config) {
        printf("ERROR: 无法创建进化配置\n");
        return;
    }
    
    printf("✓ 进化配置创建成功\n");
    printf("  种群大小: %zu\n", config->population_size);
    printf("  最大代数: %u\n", config->max_generations);
    printf("  变异率: %.3f\n", config->mut_rate);
    printf("  交叉率: %.3f\n", config->crossover_rate);
    printf("  精英数: %zu\n", config->elite_count);
    printf("  选择方法: %d\n", config->selection_method);
    printf("  交叉方法: %d\n", config->crossover_method);
    
    evo_config_destroy(config);
    printf("✓ 进化配置销毁成功\n");
}

static void test_population(void) {
    printf("\n=== 测试种群管理 ===\n");
    
    EvoPopulation* pop = evo_population_create(10);
    if (!pop) {
        printf("ERROR: 无法创建种群\n");
        return;
    }
    
    printf("✓ 种群创建成功\n");
    printf("  容量: %zu\n", pop->capacity);
    printf("  大小: %zu\n", pop->size);
    
    for (size_t i = 0; i < 5; i++) {
        EvoIndividual* ind = evo_individual_create(8);
        if (!ind) {
            printf("ERROR: 无法创建个体\n");
            evo_population_destroy(pop);
            return;
        }
        
        for (size_t g = 0; g < 8; g++) {
            ind->genes[g].opcode = (uint8_t)(rand() % 64);
            ind->genes[g].modifier = 0;
            ind->genes[g].operands[0] = (uint8_t)(rand() % 16);
            ind->genes[g].operands[1] = (uint8_t)(rand() % 16);
        }
        
        ind->fitness = (double)(rand() % 100) / 10.0;
        
        pop->individuals[pop->size++] = *ind;
        free(ind);
    }
    
    printf("  添加 %zu 个个体\n", pop->size);
    
    EvoIndividual* clone = evo_individual_clone(&pop->individuals[0]);
    if (clone) {
        printf("✓ 个体克隆成功\n");
        printf("  克隆个体基因数: %zu\n", clone->num_genes);
        evo_individual_destroy(clone);
    }
    
    evo_population_destroy(pop);
    printf("✓ 种群销毁成功\n");
}

static void test_evolution_operators(void) {
    printf("\n=== 测试进化算子 ===\n");
    
    EvoGeneInstruction gene;
    gene.opcode = 63;
    gene.modifier = 0;
    
    printf("原始操作码: %d (二进制: ", gene.opcode);
    for (int i = 5; i >= 0; i--) {
        printf("%d", (gene.opcode >> i) & 1);
    }
    printf(")\n");
    
    evo_mutation_flip_yao(&gene, 0);
    printf("翻转爻位0后: %d (二进制: ", gene.opcode);
    for (int i = 5; i >= 0; i--) {
        printf("%d", (gene.opcode >> i) & 1);
    }
    printf(")\n");
    
    evo_mutation_modifier(&gene);
    printf("✓ 修饰符变异成功\n");
    
    EvoIndividual* p1 = evo_individual_create(10);
    EvoIndividual* p2 = evo_individual_create(10);
    EvoIndividual* c1 = evo_individual_create(10);
    EvoIndividual* c2 = evo_individual_create(10);
    
    if (p1 && p2 && c1 && c2) {
        for (size_t i = 0; i < 10; i++) {
            p1->genes[i].opcode = (uint8_t)i;
            p2->genes[i].opcode = (uint8_t)(63 - i);
            c1->genes[i].opcode = 0;
            c2->genes[i].opcode = 0;
        }
        
        evo_crossover_single_point(p1, p2, c1, c2);
        printf("✓ 单点交叉成功\n");
        
        evo_crossover_two_point(p1, p2, c1, c2);
        printf("✓ 两点交叉成功\n");
        
        evo_crossover_uniform(p1, p2, c1, c2);
        printf("✓ 均匀交叉成功\n");
    }
    
    evo_individual_destroy(p1);
    evo_individual_destroy(p2);
    evo_individual_destroy(c1);
    evo_individual_destroy(c2);
}

static void test_full_evolution(void) {
    printf("\n=== 测试完整进化流程 ===\n");
    
    EvoVM* vm = evo_vm_create();
    if (!vm) {
        printf("ERROR: 无法创建虚拟机\n");
        return;
    }
    
    vm->evo_config = evo_config_create();
    if (!vm->evo_config) {
        printf("ERROR: 无法创建进化配置\n");
        evo_vm_destroy(vm);
        return;
    }
    
    vm->evo_config->population_size = 20;
    vm->evo_config->max_generations = 10;
    vm->evo_config->mut_rate = 0.05;
    
    EvoGeneInstruction seed_genes[8];
    for (size_t i = 0; i < 8; i++) {
        seed_genes[i].opcode = (uint8_t)(i * 8);
        seed_genes[i].modifier = 0;
        seed_genes[i].operands[0] = (uint8_t)i;
        seed_genes[i].operands[1] = (uint8_t)(i + 1);
    }
    
    EvoError err = evo_initialize_population(vm, seed_genes, 8);
    if (err != EVO_OK) {
        printf("ERROR: 无法初始化种群 (错误码: %d)\n", err);
        evo_vm_destroy(vm);
        return;
    }
    
    printf("✓ 种群初始化成功\n");
    printf("  种群大小: %zu\n", vm->population->size);
    printf("  个体基因数: %zu\n", vm->population->individuals[0].num_genes);
    
    printf("\n开始进化...\n");
    for (uint32_t gen = 0; gen < vm->evo_config->max_generations; gen++) {
        err = evo_evolve_one_generation(vm);
        if (err != EVO_OK) {
            printf("ERROR: 进化失败在第 %u 代\n", gen + 1);
            break;
        }
        
        double best_fitness = 0.0;
        if (vm->population->size > 0) {
            best_fitness = vm->population->individuals[0].fitness;
        }
        
        printf("  第 %u 代: 最佳适应度 = %.4f\n", vm->current_generation, best_fitness);
    }
    
    if (vm->best_ever) {
        printf("\n✓ 进化完成\n");
        printf("  最佳个体适应度: %.4f\n", vm->best_ever->fitness);
        printf("  最佳个体基因数: %zu\n", vm->best_ever->num_genes);
    }
    
    evo_vm_destroy(vm);
    printf("✓ 虚拟机销毁成功\n");
}

int main(void) {
    printf("========================================\n");
    printf("  Evomorph 原生运行时测试 v3.0\n");
    printf("========================================\n");
    
    srand((unsigned int)time(NULL));
    
    test_vm_basic();
    test_evolution_config();
    test_population();
    test_evolution_operators();
    test_full_evolution();
    
    printf("\n========================================\n");
    printf("  所有测试完成!\n");
    printf("========================================\n");
    
    return 0;
}
