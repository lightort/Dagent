from interactive_click_listener import start_interactive_listener, execute_command, stop_listener
import time


def test_interactive_listener():
    """
    测试交互式点击监听器
    """
    print("测试交互式点击监听器...")
    
    # 启动监听器
    listener = start_interactive_listener()
    
    # 等待用户点击
    print("\n请在网页上点击任意元素...")
    print("点击后，程序会捕获断点，然后可以执行命令")
    print("按Enter键继续...")
    input()
    
    # 执行code命令
    print("\n执行 code 命令查看代码上下文...")
    result = execute_command(listener, "code")
    print(f"命令执行结果: {result['message']}")
    if 'output' in result:
        print("输出:")
        print(result['output'])
    
    # 等待用户输入
    print("\n按Enter键继续...")
    input()
    
    # 执行var命令
    print("\n执行 var 命令查看变量...")
    result = execute_command(listener, "var")
    print(f"命令执行结果: {result['message']}")
    if 'output' in result:
        print("输出:")
        print(result['output'])
    
    # 等待用户输入
    print("\n按Enter键继续...")
    input()
    
    # 执行out命令
    print("\n执行 out 命令步出函数...")
    result = execute_command(listener, "out")
    print(f"命令执行结果: {result['message']}")
    if 'output' in result:
        print("输出:")
        print(result['output'])
    
    # 等待用户输入
    print("\n按Enter键继续...")
    input()
    
    # 停止监听器
    print("\n停止监听器...")
    result = stop_listener(listener)
    print(f"停止结果: {result['message']}")
    if 'output' in result:
        print("输出:")
        print(result['output'])


if __name__ == "__main__":
    test_interactive_listener()
