from typing import Dict, Any, Optional
from state.agent_state import AgentState
from tools.interactive_click_listener import start_interactive_listener, execute_command, stop_listener
from config.model_config import llm
import time
import re


def analyze_with_llm(code_context: str, var_context: str, target_pattern: str, action_history: list, user_request: str) -> Dict[str, Any]:
    """
    使用LLM分析上下文，决策下一步操作
    
    Args:
        code_context: 代码上下文
        var_context: 变量上下文
        target_pattern: 目标Token的模式描述
        action_history: 已执行的操作历史
        user_request: 完整的用户请求描述
    
    Returns:
        分析结果，包含决策的下一步操作
    """
    try:
        history_str = "\n".join([f"{i+1}. {h['action']}: {h.get('result', {}).get('message', '执行完成')}" 
                                for i, h in enumerate(action_history[-5:])])  # 只显示最近5次操作
        
        prompt = f"""你是一个代码分析专家，正在根据用户的完整任务描述来定位Token的生成位置。

完整任务描述:
{user_request}

目标Token特征: {target_pattern}

可用命令说明:
- code: 查看当前断点位置的代码上下文（显示当前函数的源代码）
- var: 查看当前作用域的所有变量及其值
- out: 步出当前函数（跳出到调用当前函数的位置）
- next: 单步执行下一行代码
- stop: 停止分析

已执行的操作历史:
{history_str if history_str else "无"}

当前代码上下文:
```javascript
{code_context[:1500] if code_context else "暂无代码上下文"}
```

当前变量上下文:
```
{var_context[:1000] if var_context else "暂无变量上下文"}
```

请分析以上信息，判断:
1. 是否找到Token的生成位置？（Token赋值或生成的代码行）
2. 如果找到，具体是哪一行代码生成的？
3. 下一步应该执行哪个命令？（code/var/out/next/stop）

重要提示:
- 请仔细分析完整任务描述，理解用户想要定位的具体函数
- 你需要在代码中寻找Token的生成逻辑（如字符串拼接、hash计算、加密算法、编码转换等）
- 如果当前代码中没有Token生成逻辑，使用out命令跳出当前函数继续查找
- 如果看到疑似Token生成的代码，使用code命令仔细查看上下文
- 如果看到Token相关的变量，使用var命令查看变量值
- 注意识别不同类型的Token：
  * 多段由点号分隔的字符串（如WTZ1.mmy9jbeq.9ddda7c9...）
  * 长字符串，可能是加密或哈希结果（如04d635d2ccea813cf9f7645cbd974dcb...）
- 注意查找与用户描述相关的加密逻辑，如用户名、密码的加密处理
- 确保定位到的函数确实是生成目标Token的函数，而不是中间过程

请以JSON格式返回:
{{
    "found": true/false,
    "reason": "判断理由",
    "next_action": "code/var/out/next/stop",
    "token_generation_code": "如果找到，返回生成Token的具体代码行",
    "function_name": "Token生成的函数名"
}}
"""
        
        response = llm.invoke(prompt)
        content = response.content.strip()
        
        # 尝试从响应中提取JSON
        try:
            # 如果响应包含markdown代码块，提取其中的JSON
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content
            
            import json
            result = json.loads(json_str)
            return result
        except Exception as e:
            print(f"LLM返回结果解析失败: {e}")
            print(f"原始响应: {content[:200]}")
            # 根据响应内容做简单判断
            if "found" in content.lower() and "true" in content.lower():
                return {"found": True, "next_action": "stop", "reason": "LLM指示找到"}
            elif "out" in content.lower():
                return {"found": False, "next_action": "out", "reason": "LLM指示跳出"}
            else:
                return {"found": False, "next_action": "code", "reason": "默认查看代码"}
                
    except Exception as e:
        print(f"LLM调用失败: {e}")
        # LLM失败时默认执行out
        return {"found": False, "next_action": "out", "reason": "LLM调用失败，默认跳出"}


def variable_analyzer_node(state: AgentState) -> AgentState:
    """
    变量分析节点 - 使用LLM决策每一步操作
    
    Args:
        state: AgentState
    
    Returns:
        更新后的AgentState
    """
    print("=" * 60)
    print("开始变量分析...")
    print("=" * 60)
    
    # 从用户请求中提取目标Token模式
    user_request = state.get("user_request", "")
    
    # 提取Token模式描述
    token_pattern = "类似XXX.XXX.XXX.XXX结构的多段字符串（如WTZ1.mmy9jbeq.9ddda7c9...）"
    
    # 尝试提取具体的Token示例 - 支持两种格式
    # 格式1: Token: WTZ1.mmy9jbeq.9ddda7c9.a8ec0500ab2a670d183ad79db79e91be456ff31fb58e06e7d86d311427e2a13478eba28e
    token_match = re.search(r'Token[:\s]+([\w\.]+)', user_request, re.IGNORECASE)
    
    # 格式2: token:04d635d2ccea813cf9f7645cbd974dcb4a797edc21894e9be2d948f1b033574a104027da8b9e94a0c7dd025801e64a02f2a5c89b76c10cb031d724cd38f7316af6dde84bda0b6ad7226d98ebd12be31408ccee3bede2de61b130f4ab15255213eae113373ad015f489aece2b
    if not token_match:
        token_match = re.search(r'token:([0-9a-f]+)', user_request, re.IGNORECASE)
    
    if token_match:
        token_example = token_match.group(1)
        if '.' in token_example:
            token_pattern = f"类似{token_example}的结构（多段由点号分隔的字符串）"
        else:
            token_pattern = f"类似{token_example}的结构（长字符串，可能是加密或哈希结果）"
    
    print(f"目标Token模式: {token_pattern}")
    
    # 启动交互式点击监听器
    print("\n启动交互式点击监听器...")
    listener = start_interactive_listener()
    
    # 等待用户点击
    print("\n" + "=" * 60)
    print("请在网页上点击包含目标Token的元素...")
    print("点击后系统将自动分析Token产生位置")
    print("=" * 60)
    
    # 等待用户点击（给足够时间）
    time.sleep(8)
    
    # 初始化
    action_history = []
    action_count = 0
    max_actions = 25
    found = False
    token_generation_info = None
    
    # 获取初始代码上下文
    print("\n获取初始代码上下文...")
    code_result = execute_command(listener, "code")
    current_code = code_result.get("output", "") if code_result.get("success") else ""
    
    # 获取初始变量上下文
    print("获取初始变量上下文...")
    var_result = execute_command(listener, "var")
    current_vars = var_result.get("output", "") if var_result.get("success") else ""
    
    # 开始自动化分析循环
    while action_count < max_actions and not found:
        action_count += 1
        print(f"\n{'='*60}")
        print(f"操作 {action_count}/{max_actions}")
        print(f"{'='*60}")
        
        # 使用LLM分析当前上下文并决策
        print("使用LLM分析上下文并决策...")
        llm_decision = analyze_with_llm(current_code, current_vars, token_pattern, action_history, user_request)
        print(f"LLM决策: {llm_decision}")
        
        # 检查是否找到
        if llm_decision.get("found", False):
            print(f"\n✅ LLM判断已找到Token生成位置!")
            token_generation_info = {
                "found": True,
                "function_name": llm_decision.get("function_name", "unknown"),
                "token_generation_code": llm_decision.get("token_generation_code", ""),
                "reason": llm_decision.get("reason", ""),
                "code_context": current_code,
                "var_context": current_vars,
                "action_count": action_count,
                "action_history": action_history
            }
            found = True
            break
        
        # 获取LLM决策的下一步操作
        next_action = llm_decision.get("next_action", "out")
        print(f"执行操作: {next_action}")
        
        if next_action == "stop":
            print("LLM指示停止分析")
            break
        
        # 执行LLM决策的操作
        action_result = execute_command(listener, next_action)
        action_history.append({
            "action": next_action,
            "result": action_result,
            "llm_reason": llm_decision.get("reason", "")
        })
        
        # 根据操作更新上下文
        if next_action == "code":
            if action_result.get("success"):
                current_code = action_result.get("output", current_code)
        elif next_action == "var":
            if action_result.get("success"):
                current_vars = action_result.get("output", current_vars)
        elif next_action in ["out", "next"]:
            # 执行out或next后，重新获取代码和变量上下文
            time.sleep(0.5)
            print("更新代码上下文...")
            code_result = execute_command(listener, "code")
            if code_result.get("success"):
                current_code = code_result.get("output", "")
            
            print("更新变量上下文...")
            var_result = execute_command(listener, "var")
            if var_result.get("success"):
                current_vars = var_result.get("output", "")
        
        # 短暂等待让命令执行完成
        time.sleep(0.5)
    
    # 停止监听器
    print("\n" + "=" * 60)
    print("停止监听器...")
    print("=" * 60)
    stop_listener(listener)
    
    # 生成最终结果
    if found and token_generation_info:
        final_response = f"""✅ 成功找到Token生成位置!

生成函数: {token_generation_info['function_name']}
操作次数: {token_generation_info['action_count']}

Token生成代码:
```javascript
{token_generation_info['token_generation_code'][:800]}
```

完整代码上下文:
```javascript
{token_generation_info['code_context'][:1500]}
```

判断理由: {token_generation_info['reason']}
"""
    else:
        final_response = f"""❌ 在 {action_count} 次操作后未找到Token生成位置

最后查看的代码上下文:
```javascript
{current_code[:1000] if current_code else "无"}
```

操作历史:
"""
        for i, h in enumerate(action_history[-10:], 1):
            final_response += f"{i}. {h['action']}: {h.get('llm_reason', '执行完成')}\n"
    
    return {
        **state,
        "action_history": action_history,
        "token_generation_info": token_generation_info,
        "final_response": final_response,
        "last_code_context": current_code,
        "last_var_context": current_vars
    }
