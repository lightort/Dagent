import re
import sys
import os
import signal
from typing import Dict, List, Any

# 添加项目根目录到模块搜索路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.model_config import llm

# 处理Ctrl+C信号
def signal_handler(sig, frame):
    print('\n用户中断了程序')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

class TokenAnalyzerAgent:
    """分析代码路径追踪文件，识别潜在的token生成代码"""
    
    def __init__(self, file_path: str = '', description: str = ''):
        self.file_path = file_path
        self.description = description
        self.function_context_map = {}
        self.token_generation_functions = {}
    
    def parse_code_trace(self) -> Dict[str, List[str]]:
        """解析代码路径追踪文件，构建函数到代码上下文的映射"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 正则表达式匹配步骤块
        step_pattern = re.compile(r'步骤 #\d+[\s\S]+?============================================================', re.MULTILINE)
        steps = step_pattern.findall(content)
        
        # 用于去重的函数名集合
        function_names_seen = set()
        
        for step in steps:
            # 提取调用栈最顶层函数（第一个）
            call_stack_match = re.search(r'调用栈:\s*([\s\S]+?)\n\n代码上下文:', step)
            if call_stack_match:
                call_stack = call_stack_match.group(1).strip()
                # 提取顶层调用栈完整信息，如 "e.value (app~2a42e354.08d36f4a.js:1:268822)"
                # 处理有换行符和没有换行符的情况
                top_stack_match = re.search(r'0\.\s*(.+?)(?:\n|$)', call_stack)
                if top_stack_match:
                    top_stack_full = top_stack_match.group(1).strip()
                    # 提取函数名部分（括号前的部分），如 "e.value"
                    top_function_match = re.match(r'(.+?)\s*\(', top_stack_full)
                    if top_function_match:
                        top_function_name = top_function_match.group(1).strip()
                    else:
                        # 如果没有括号，使用完整内容作为函数名
                        top_function_name = top_stack_full
                else:
                    # 如果没有调用栈信息，提取函数名
                    function_match = re.search(r'函数:\s*(.+?)\n', step)
                    if function_match:
                        top_function_name = function_match.group(1).strip()
                        top_stack_full = top_function_name
                    else:
                        continue
            else:
                # 如果没有调用栈信息，提取函数名
                function_match = re.search(r'函数:\s*(.+?)\n', step)
                if function_match:
                    top_function_name = function_match.group(1).strip()
                    top_stack_full = top_function_name
                else:
                    continue
            
            # 提取代码上下文
            context_match = re.search(r'代码上下文:\s*([\s\S]+?)============================================================', step)
            if context_match:
                context = context_match.group(1).strip()
                # 清理上下文格式
                context = re.sub(r'→\s*\d+\s*\|', '', context)
                context = context.replace('▼', '').strip()
                
                # 检查函数名是否已存在，避免重复添加
                # 对于匿名函数，每一个都创建一个键值对，不需要去重
                if top_function_name != '(匿名函数)':
                    if top_function_name not in function_names_seen:
                        function_names_seen.add(top_function_name)
                        # 使用完整的调用栈顶层信息作为键
                        self.function_context_map[top_stack_full] = [context]
                else:
                    # 对于匿名函数，直接添加，不需要去重
                    self.function_context_map[top_stack_full] = [context]
        
        return self.function_context_map
    
    def analyze_with_llm(self, function_name: str, context: str, description: str) -> bool:
        """使用LLM分析代码上下文，判断是否可能是token生成代码"""

        prompt = f"判断函数 {function_name} 是否可能是这段描述“{description}”的生成代码：\n{context} \n只能回答是或否"
        
        try:
            print("正在调用LLM...")
            #print(prompt)
            # 实际LLM调用

            response = llm.invoke(prompt, timeout=30)  # 添加30秒超时
            #print(response)
            if response.content == "是":
                return True
            else:
                return False
            '''
            if function_name == 's.accountSubmit (chunk-858ed276.7bbb8c3f.js:12:106286)':
                return True
            else:
                return False
            '''
            
        except KeyboardInterrupt:
            print("\n用户中断了程序")
            raise
        except Exception as e:
            print(f"LLM调用出错: {e}")
            return False
    
    def analyze_token_generation(self) -> Dict[str, List[str]]:
        """分析函数上下文，判断是否可能是token生成代码"""
        try:
            total_functions = len(self.function_context_map)
            print(f"开始分析 {total_functions} 个函数...")
            
            for idx, (function_name, contexts) in enumerate(self.function_context_map.items(), 1):
                print(f"正在分析第 {idx}/{total_functions} 个函数: {function_name}")
                for context in contexts:
                    # 使用LLM分析
                    if self.analyze_with_llm(function_name, context, self.description):
                        if function_name not in self.token_generation_functions:
                            self.token_generation_functions[function_name] = []
                        self.token_generation_functions[function_name].append(context)
        except KeyboardInterrupt:
            print("\n分析被用户中断")
        
        return self.token_generation_functions
    
agent = TokenAnalyzerAgent('', '')
# 定义agent nodes
class ParseCodeTraceNode:
    """解析代码路径追踪文件的节点"""
    def run(self, file_path: str, description: str) -> Dict[str, List[str]]:
        agent = TokenAnalyzerAgent(file_path, description)
        return agent.parse_code_trace()

class AnalyzeTokenGenerationNode:
    """分析token生成代码的节点"""
    def run(self, function_context_map: Dict[str, List[str]], description: str) -> Dict[str, List[str]]:
        agent = TokenAnalyzerAgent('', description)
        agent.function_context_map = function_context_map
        return agent.analyze_token_generation()

class OutputResultsNode:
    """输出结果的节点"""
    def run(self, token_functions: Dict[str, List[str]]) -> None:
        print(f"\n最终结果: {len(token_functions)} 个潜在的token生成函数")
        for function_name, contexts in token_functions.items():
            print(f"\n函数: {function_name}")
            for i, context in enumerate(contexts, 1):
                print(f"  上下文 {i}:\n{context[:500]}...\n")

# 主函数
def main():
    file_path = r'code_path_trace.txt'
    description = '这是一段登录的加密代码，会将用户名15924231565加密成token:04d635d2ccea813cf9f7645cbd974dcb4a797edc21894e9be2d948f1b033574a104027da8b9e94a0c7dd025801e64a02f2a5c89b76c10cb031d724cd38f7316af6dde84bda0b6ad7226d98ebd12be31408ccee3bede2de61b130f4ab15255213eae113373ad015f489aece2b，将密码13819912565加密成token:0436679559170009c0c7a7702fae527b0498ce64f6da4011ac39281f4ffeb616aaff3ad42d21b0eca88999fd2dbfe49a0a0390391eb66fe101337d92aa2048e5687ee90c59c81f6da16034aa53713d040ced7f9f58c35cb0922d036a356a2559f9de88ed0d657e4ffe0ef4aceb6f8cb9d3952a40248ef5d1e8c971b2add815c9a13bcba575ea752445ecf0534ab2ca846ef52bc96a80a5696ff93de2555a7831cc'
    
    try:
        # 创建节点
        parse_node = ParseCodeTraceNode()
        analyze_node = AnalyzeTokenGenerationNode()
        output_node = OutputResultsNode()
        
        # 运行流程
        function_context_map = parse_node.run(file_path, description)
        #print(function_context_map.keys())
        token_functions = analyze_node.run(function_context_map, description)
        #print(token_functions)
        output_node.run(token_functions)
    except KeyboardInterrupt:
        print("\n程序被用户中断")

def static_code_analyzer(description: str):
    
    try:
        # 创建节点
        file_path = r'code_path_trace.txt'
        parse_node = ParseCodeTraceNode()
        analyze_node = AnalyzeTokenGenerationNode()
        
        # 运行流程
        function_context_map = parse_node.run(file_path, description)
        #print(function_context_map.keys())
        token_functions = analyze_node.run(function_context_map, description)
        #print(token_functions)
        return token_functions
    except KeyboardInterrupt:
        print("\n程序被用户中断")

if __name__ == "__main__":
    try:
        print(static_code_analyzer("1"))
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(0)
