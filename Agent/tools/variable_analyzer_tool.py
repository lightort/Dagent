from typing import Dict, Any, Optional
from tools.interactive_click_listener import start_interactive_listener, execute_command, stop_listener
import time
import re


def analyze_context_with_llm(context: str, target: str) -> Dict[str, Any]:
    """
    使用LLM分析上下文，判断是否找到目标变量的生成位置
    
    Args:
        context: 上下文信息
        target: 目标变量或Token
    
    Returns:
        分析结果
    """
    try:
        # 尝试导入LLM
        from config.model_config import llm
        
        prompt = f"""
        你是一个代码分析专家，负责分析代码上下文并找出指定Token的生成位置。
        
        目标Token: {target}
        
        请分析以下上下文，回答以下问题：
        1. 是否找到Token的生成位置？
        2. 如果找到，Token是在哪个函数中生成的？
        3. 生成Token的代码逻辑是什么？
        4. 下一步应该执行什么操作？（code/var/out/next/stop）
        
        上下文：
        {context[:2000]}...
        
        请以JSON格式返回结果，包含以下字段：
        - found: boolean，是否找到
        - function_name: string，生成Token的函数名
        - logic: string，生成逻辑
        - next_action: string，下一步操作
        """
        
        response = llm.invoke(prompt)
        try:
            import json
            result = json.loads(response.content)
            return result
        except Exception as e:
            # 如果解析失败，返回默认结果
            print(f"LLM返回结果解析失败: {e}")
            return {
                "found": False,
                "function_name": "",
                "logic": "",
                "next_action": "out"
            }
    except Exception as e:
        # 如果LLM调用失败，返回默认结果
        print(f"LLM调用失败: {e}")
        # 使用简单的启发式方法来分析上下文
        if target in context:
            # 尝试提取函数名
            function_match = re.search(r'function\s+(\w+)\s*\(', context)
            function_name = function_match.group(1) if function_match else "unknown"
            return {
                "found": True,
                "function_name": function_name,
                "logic": f"在代码中找到Token {target}",
                "next_action": "stop"
            }
        return {
            "found": False,
            "function_name": "",
            "logic": "",
            "next_action": "out"
        }


def analyze_variable_origin(user_request: str) -> Dict[str, Any]:
    """
    分析变量产生的位置
    
    Args:
        user_request: 用户请求，包含要分析的Token
    
    Returns:
        分析结果
    """
    print("=" * 60)
    print("开始变量分析...")
    print("=" * 60)
    
    # 从用户请求中提取目标Token
    target_variable = ""
    token_match = re.search(r'Token:\s*([\w\.]+)', user_request)
    if token_match:
        target_variable = token_match.group(1)
    else:
        return {
            "success": False,
            "message": "未指定目标Token",
            "error": "请在请求中指定要分析的Token"
        }
    
    print(f"目标Token: {target_variable}")
    
    # 启动交互式点击监听器
    print("启动交互式点击监听器...")
    listener = start_interactive_listener()
    
    # 等待用户点击
    print("\n请在网页上点击包含目标Token的元素...")
    print("点击后将自动开始分析Token产生位置")
    
    # 等待一段时间让用户点击
    time.sleep(5)
    
    # 初始化操作历史和计数器
    action_history = []
    action_count = 0
    max_actions = 20
    found = False
    variable_origin = None
    
    # 开始自动化分析循环
    while action_count < max_actions and not found:
        action_count += 1
        print(f"\n操作 {action_count}/{max_actions}:")
        
        # 1. 执行code命令查看当前代码上下文
        print("执行 code 命令查看当前代码上下文...")
        code_result = execute_command(listener, "code")
        action_history.append({"action": "code", "result": code_result})
        
        # 收集上下文信息
        context = ""
        if code_result["success"] and "output" in code_result:
            context = code_result["output"]
        
        # 2. 执行var命令查看当前作用域变量
        print("执行 var 命令查看当前作用域变量...")
        var_result = execute_command(listener, "var")
        action_history.append({"action": "var", "result": var_result})
        
        if var_result["success"] and "output" in var_result:
            context += "\n\n变量信息:\n" + var_result["output"]
        
        # 3. 使用LLM分析上下文
        print("分析上下文...")
        llm_result = analyze_context_with_llm(context, target_variable)
        print(f"分析结果: {llm_result}")
        
        # 检查是否找到Token生成位置
        if llm_result.get("found", False):
            print(f"找到Token {target_variable} 的生成位置")
            variable_origin = {
                "type": "identified",
                "function_name": llm_result.get("function_name", "unknown"),
                "logic": llm_result.get("logic", ""),
                "context": context,
                "action_count": action_count
            }
            found = True
            break
        
        # 4. 根据分析结果执行下一步操作
        next_action = llm_result.get("next_action", "out")
        print(f"执行建议的操作: {next_action}")
        
        if next_action != "stop":
            action_result = execute_command(listener, next_action)
            action_history.append({"action": next_action, "result": action_result})
        else:
            # 如果建议停止，就停止分析
            break
        
        # 等待一下让命令执行完成
        time.sleep(1)
    
    # 停止监听器
    print("\n停止监听器...")
    stop_result = stop_listener(listener)
    
    # 生成结果
    if found:
        final_response = f"成功找到Token {target_variable} 的产生位置！\n"
        final_response += f"生成函数: {variable_origin['function_name']}\n"
        final_response += f"操作次数: {variable_origin['action_count']}\n"
        final_response += f"生成逻辑: {variable_origin['logic'][:500]}..."
        return {
            "success": True,
            "message": f"成功找到Token {target_variable} 的产生位置",
            "variable_origin": variable_origin,
            "action_history": action_history,
            "final_response": final_response
        }
    else:
        final_response = f"在 {max_actions} 次操作后未找到Token {target_variable} 的产生位置\n"
        final_response += "可能需要手动分析或调整分析策略"
        return {
            "success": False,
            "message": f"未找到Token {target_variable} 的产生位置",
            "action_history": action_history,
            "final_response": final_response
        }
