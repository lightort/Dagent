from graph.variable_analyzer_graph import build_variable_analyzer_graph
from state.agent_state import AgentState


def test_variable_analyzer():
    """
    测试变量分析功能
    """
    print("=" * 60)
    print("测试变量分析功能...")
    print("=" * 60)
    
    # 构建变量分析图
    graph = build_variable_analyzer_graph()
    
    # 初始化状态
    initial_state = AgentState(
        user_request="分析类似这样的Token: WTZ1.mmy9jbeq.9ddda7c9.a8ec0500ab2a670d183ad79db79e91be456ff31fb58e06e7d86d311427e2a13478eba28e会在哪个函数生成",
        target_variable="token"
    )
    
    # 执行图
    result = graph.invoke(initial_state)
    
    # 打印结果
    print("=" * 60)
    print("变量分析结果:")
    print("=" * 60)
    print(f"成功: {result.get('variable_origin') is not None}")
    print(f"最终响应: {result.get('final_response')}")
    
    if 'action_history' in result:
        print(f"\n执行的操作数: {len(result['action_history'])}")
    
    if 'variable_origin' in result and result['variable_origin']:
        print(f"\n变量产生位置:")
        print(f"类型: {result['variable_origin'].get('type')}")
        print(f"操作次数: {result['variable_origin'].get('action_count')}")
        print(f"上下文: {result['variable_origin'].get('context', '')[:300]}...")


if __name__ == "__main__":
    test_variable_analyzer()
