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
    description = "这是一段登录的加密代码，会将用户名15924231565加密成token:04d635d2ccea813cf9f7645cbd974dcb4a797edc21894e9be2d948f1b033574a104027da8b9e94a0c7dd025801e64a02f2a5c89b76c10cb031d724cd38f7316af6dde84bda0b6ad7226d98ebd12be31408ccee3bede2de61b130f4ab15255213eae113373ad015f489aece2b，将密码13819912565加密成token:0436679559170009c0c7a7702fae527b0498ce64f6da4011ac39281f4ffeb616aaff3ad42d21b0eca88999fd2dbfe49a0a0390391eb66fe101337d92aa2048e5687ee90c59c81f6da16034aa53713d040ced7f9f58c35cb0922d036a356a2559f9de88ed0d657e4ffe0ef4aceb6f8cb9d3952a40248ef5d1e8c971b2add815c9a13bcba575ea752445ecf0534ab2ca846ef52bc96a80a5696ff93de2555a7831cc"
    #description = "分析类似这样的Token: WTZ1.mmy9jbeq.9ddda7c9.a8ec0500ab2a670d183ad79db79e91be456ff31fb58e06e7d86d311427e2a13478eba28e会在哪个函数生成"
    # 初始化状态
    initial_state = AgentState(
        user_request=f"分析这样描述的生成代码：{description}",
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
