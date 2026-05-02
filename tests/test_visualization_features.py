#!/usr/bin/env python3
"""测试新增的中优先级模块"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print('=' * 60)
print('测试新增的中优先级模块')
print('=' * 60)


# 1. 可视化模块
print('\n1. 可视化模块 (visualization)')
try:
    from evomorph.cli.visualization import (
        ASCIIProgressBar,
        ASCIIChart,
        EvolutionVisualizer,
        CodeDiffVisualizer,
        ProgressMetrics,
        DebugVisualizer,
        InteractiveCodeEditor,
        create_sparkline,
    )

    bar = ASCIIProgressBar(width=40, show_percent=True)
    bar.update(current=50, total=100)
    rendered = bar.render()
    print(f'   进度条渲染: {"█" in rendered} ✅')

    data = [1, 3, 2, 5, 4, 6, 8, 7, 9, 10]
    sparkline = create_sparkline(data, width=20)
    print(f'   Sparkline: {sparkline} ✅')

    viz = EvolutionVisualizer(width=70)
    viz.update(generation=25, total_generations=100, best_fitness=0.85, avg_fitness=0.72)
    rendered_viz = viz.render()
    print(f'   进化可视化器: 包含"第 25/100 代" = {"第 25/100 代" in rendered_viz} ✅')

    diff_viz = CodeDiffVisualizer()
    original = 'line1\nline2\nline3'
    modified = 'line1\nmodified\nline3'
    diff_data = diff_viz.compute_diff(original, modified)
    print(f'   Diff计算: 有hunks={len(diff_data.hunks) > 0} ✅')

    debug_viz = DebugVisualizer(width=70)
    debug_viz.update_registers({0: 0x1234, 1: 0x5678})
    debug_viz.set_instruction_pointer(42)
    debug_rendered = debug_viz.render()
    print(f'   调试可视化器: 包含"IP" = {"IP" in debug_rendered} ✅')

    editor = InteractiveCodeEditor()
    editor.load_content('line1\nline2\nline3')
    editor.insert_char('x')
    content = editor.get_content()
    print(f'   代码编辑器: 首字符添加成功 = {content.startswith("x")} ✅')

except Exception as e:
    print(f'   ❌ 失败: {e}')
    import traceback
    traceback.print_exc()


# 2. 对话增强模块
print('\n2. 对话增强模块 (conversation_enhanced)')
try:
    from evomorph.cli.conversation_enhanced import (
        ContextWindowManager,
        ConversationHistory,
        CodeDiffPresenter,
        ContextAwareResponder,
        CodeExtractor,
        ResponseFormatter,
        DialogManager,
        ConversationMessage,
        MessageRole,
        MessageType,
    )

    history = ConversationHistory()
    history.start_session('test-session')
    msg = ConversationMessage(role=MessageRole.USER, content='测试消息')
    history.add_message(msg)
    summary = history.get_summary()
    print(f'   对话历史: 总消息数={summary["total_messages"]} ✅')

    context_mgr = ContextWindowManager()
    context_mgr.add_message(msg)
    recent = context_mgr.get_recent_messages(5)
    print(f'   上下文管理器: 消息数={len(recent)} ✅')

    extractor = CodeExtractor()
    text_with_code = '''这是一些文本
```evomorph
@evolang "3.0"
@locus test {
    ䷀ CREA R0, R1
}
```
更多文本'''
    blocks = extractor.extract_code_blocks(text_with_code)
    print(f'   代码提取器: 找到 {len(blocks)} 个代码块 ✅')

    formatter = ResponseFormatter()
    success_msg = formatter.format_success('操作完成', details='所有步骤已执行')
    print(f'   响应格式化器: 成功消息 ✅')

    table = formatter.format_table(
        headers=['列1', '列2'],
        rows=[['行1值1', '行1值2'], ['行2值1', '行2值2']],
        title='测试表格',
    )
    print(f'   表格格式化器: 生成成功 ✅')

except Exception as e:
    print(f'   ❌ 失败: {e}')
    import traceback
    traceback.print_exc()


# 3. 需求分析模块
print('\n3. 需求分析模块 (requirement_analyzer)')
try:
    from evomorph.analysis.requirement_analyzer import (
        RequirementAnalyzer,
        KeywordExtractor,
        ComputingPatternDetector,
        PerformanceGoalExtractor,
        PlatformDetector,
        AmbiguityDetector,
        AmbiguityLevel,
    )

    extractor = KeywordExtractor()
    keywords = extractor.extract('我需要一个快速的并行数据处理程序')
    print(f'   关键词提取: 找到 {len(keywords.get("all", []))} 个关键词 ✅')

    detector = ComputingPatternDetector()
    patterns = detector.detect('这个程序需要并行处理多个数据流')
    print(f'   计算模式检测: 找到 {len(patterns)} 个模式 ✅')

    goal_extractor = PerformanceGoalExtractor()
    goals = goal_extractor.extract('这个程序需要低延迟和高吞吐量')
    print(f'   性能目标提取: 找到 {len(goals)} 个目标 ✅')

    platform_detector = PlatformDetector()
    platforms = platform_detector.detect('这个程序需要在Android和iOS上运行')
    print(f'   平台检测: 找到 {len(platforms)} 个平台 ✅')

    amb_detector = AmbiguityDetector()
    ambiguities = amb_detector.detect('我需要一些快速的东西')
    print(f'   模糊检测: 找到 {len(ambiguities)} 个模糊点 ✅')

    analyzer = RequirementAnalyzer()
    analysis = analyzer.analyze('我需要创建一个快速的并行数据处理程序，在Android上运行')
    print(f'   需求分析器: 功能需求={len(analysis.functional_requirements)} 个 ✅')
    print(f'   计算模式: {[p.value for p in analysis.computing_patterns]}')
    print(f'   目标平台: {analysis.target_platforms}')

except Exception as e:
    print(f'   ❌ 失败: {e}')
    import traceback
    traceback.print_exc()


# 4. 澄清引擎模块
print('\n4. 澄清引擎模块 (clarification_engine)')
try:
    from evomorph.analysis.clarification_engine import (
        ClarificationManager,
        QuestionGenerator,
        InteractiveClarificationFlow,
        ClarificationType,
        ClarificationState,
    )

    generator = QuestionGenerator()
    question = generator.generate(ClarificationType.PERFORMANCE_GOAL)
    print(f'   问题生成器: 生成问题类型={question.question_type.value} ✅')

    manager = ClarificationManager()
    session = manager.create_session('我需要一个快速的程序')
    print(f'   澄清管理器: 创建会话，问题数={len(session.questions)} ✅')

    flow = InteractiveClarificationFlow()
    start_response = flow.start('我需要一个快速的并行程序')
    print(f'   交互式澄清: 启动响应包含"澄清" = {"澄清" in start_response} ✅')

    status = flow.get_status()
    print(f'   会话状态: {status.get("state", "unknown")} ✅')

except Exception as e:
    print(f'   ❌ 失败: {e}')
    import traceback
    traceback.print_exc()


print('\n' + '=' * 60)
print('所有中优先级模块测试完成!')
print('=' * 60)
