import sys
import os

# 添加项目根目录到导入路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.cdp_target_resolver import resolve_cdp_target
from tools.user_action_tracker import track_user_action


def test_action_tracker():
    """
    测试用户操作跟踪器
    """
    try:
        # 提示用户启动浏览器
        print("请确保Chrome浏览器已完全关闭，然后使用以下命令启动：")
        print("=" * 80)
        print("Start-Process -FilePath \"D:\\Projects\\debug_tool\\CDP\\chrome-win64\\chrome.exe\" -ArgumentList \"--remote-debugging-port=9222\", \"--remote-allow-origins=*\", \"D:\\Projects\\Dagent\\Agent\\WebPage\\index.html\"")
        print("=" * 80)
        print("\n重要：请完全关闭所有Chrome窗口后再运行上述命令！")
        print("\n按Enter键继续...")
        input()
        
        # 尝试不同的远程调试URL
        remote_debugging_urls = [
            "http://127.0.0.1:9222",
            "http://localhost:9222"
        ]
        
        result = None
        for url in remote_debugging_urls:
            try:
                # 解析 CDP 目标
                print(f"\n正在尝试连接到浏览器: {url}...")
                result = resolve_cdp_target(
                    remote_debugging_url=url,
                    target_url="file:///D:/Projects/Dagent/Agent/WebPage/index.html"
                )
                if result:
                    print(f"成功连接到 {url}！")
                    break
            except Exception as e:
                print(f"连接 {url} 失败: {e}")
        
        if not result:
            print("\n无法连接到任何远程调试端口")
            print("请检查：")
            print("1. 是否完全关闭了所有Chrome窗口")
            print("2. 是否使用了正确的启动命令，包含 --remote-allow-origins=* 参数")
            print("3. 浏览器是否成功启动并打开了网页")
            print("4. 尝试在浏览器中访问 http://127.0.0.1:9222 看看是否能打开调试页面")
            return
        
        cdp_session = result.get("cdp_session")
        if not cdp_session:
            print("无法连接到浏览器，请确保浏览器已启动并开启远程调试模式")
            return
        
        print("连接成功！")
        print("=" * 60)
        
        # 跟踪用户操作
        tracking_result = track_user_action(
            cdp=cdp_session,
            prompt_message="请在网页上点击任意元素或进行其他交互操作",
            timeout=30
        )
        
        print("=" * 60)
        print("跟踪结果:")
        print(f"成功: {tracking_result['success']}")
        print(f"消息: {tracking_result['message']}")
        
        if tracking_result['actions']:
            print("\n捕获到的操作:")
            for i, action in enumerate(tracking_result['actions'], 1):
                print(f"\n操作 #{i}:")
                print(f"类型: {action['type']}")
                print(f"时间: {action['timestamp']}")
                print(f"目标: {action['target']}")
                print("函数调用链:")
                for j, func in enumerate(action['function_chain'], 1):
                    print(f"  {j}. {func}")
        else:
            print("未捕获到任何操作")
        
        # 关闭会话
        cdp_session.close()
        
    except Exception as e:
        print(f"测试失败: {e}")


if __name__ == "__main__":
    test_action_tracker()
