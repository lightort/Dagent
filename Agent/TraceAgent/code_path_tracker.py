"""
测试代码路径追踪工具
"""

from tools.code_path_tracker import track_code_path, CodePathTracker


def test_code_path_tracker():
    """
    测试代码路径追踪功能
    """
    print("=" * 60)
    print("测试代码路径追踪工具...")
    print("=" * 60)
    
    # 使用便捷函数进行追踪
    result = track_code_path("code_path_trace.txt")
    
    # 打印结果
    print("\n" + "=" * 60)
    print("追踪结果:")
    print("=" * 60)
    print(f"成功: {result.get('success')}")
    print(f"消息: {result.get('message')}")
    
    if result.get('success'):
        print(f"\n总步数: {result.get('total_steps')}")
        print(f"记录的位置数: {result.get('recorded_locations')}")
        print(f"输出文件: {result.get('output_file')}")
        
        # 显示输出文件内容
        print("\n" + "=" * 60)
        print("输出文件内容预览:")
        print("=" * 60)
        try:
            with open(result['output_file'], 'r', encoding='utf-8') as f:
                content = f.read()
                # 只显示前2000个字符
                print(content[:2000])
                if len(content) > 2000:
                    print(f"\n... (还有 {len(content) - 2000} 个字符)")
        except Exception as e:
            print(f"读取文件失败: {e}")



if __name__ == "__main__":
    test_code_path_tracker()

