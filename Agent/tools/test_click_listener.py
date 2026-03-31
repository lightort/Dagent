from click_listener import start_click_listener, execute_terminal_command


def test_click_listener():
    """
    测试点击监听器
    """
    print("测试点击监听器...")
    result = start_click_listener()
    print("\n监听器结果:")
    print(f"成功: {result['success']}")
    print(f"消息: {result['message']}")
    if 'output' in result:
        print("输出:")
        print(result['output'])
    if 'error' in result:
        print("错误:")
        print(result['error'])


def test_terminal_commands():
    """
    测试终端命令执行
    """
    print("\n测试终端命令执行...")
    
    # 测试 code 命令
    print("\n测试 code 命令:")
    result = execute_terminal_command("code")
    print(f"成功: {result['success']}")
    print(f"消息: {result['message']}")
    if 'output' in result:
        print("输出:")
        print(result['output'])
    
    # 测试 var 命令
    print("\n测试 var 命令:")
    result = execute_terminal_command("var")
    print(f"成功: {result['success']}")
    print(f"消息: {result['message']}")
    if 'output' in result:
        print("输出:")
        print(result['output'])
    
    # 测试 out 命令
    print("\n测试 out 命令:")
    result = execute_terminal_command("out")
    print(f"成功: {result['success']}")
    print(f"消息: {result['message']}")
    if 'output' in result:
        print("输出:")
        print(result['output'])


if __name__ == "__main__":
    # 先测试点击监听器
    test_click_listener()
    
    # 然后测试终端命令
    test_terminal_commands()
