from __future__ import annotations

from typing import Any, Dict, List, Optional
import time


def _cdp_call(cdp: Any, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = params or {}
    if hasattr(cdp, "call"):
        return cdp.call(method, params) or {}
    if hasattr(cdp, "send"):
        return cdp.send(method, params) or {}
    raise AttributeError("CDP client must provide .call(...) or .send(...)")


def _eval(cdp: Any, expression: str, return_by_value: bool = True) -> Any:
    result = _cdp_call(
        cdp,
        "Runtime.evaluate",
        {
            "expression": expression,
            "returnByValue": return_by_value,
            "awaitPromise": True,
        },
    )
    if return_by_value:
        return (((result or {}).get("result") or {}).get("value"))
    return (result or {}).get("result")


def _enable_domains(cdp: Any) -> None:
    _cdp_call(cdp, "Runtime.enable")
    _cdp_call(cdp, "DOM.enable")
    _cdp_call(cdp, "Page.enable")


def install_action_tracker(cdp: Any) -> None:
    """
    在页面中注入用户操作跟踪器。
    该跟踪器会监听用户的各种交互事件，并捕获调用栈。
    """
    _enable_domains(cdp)

    expression = r"""
    (() => {
        // 检查是否已经安装
        if (window.__RUNTIME_ACTION_TRACKER_INSTALLED__) {
            console.log('=== 用户操作跟踪器已安装，跳过安装步骤 ===');
            return true;
        }

        // 完全重置所有状态
        delete window.__RUNTIME_ACTION_TRACKER__;
        delete window.__RUNTIME_ACTION_TRACKER_CLICK_HANDLER__;
        delete window.__RUNTIME_ACTION_TRACKER_INSTALLED__;

        console.log('=== 开始安装用户操作跟踪器 ===');

        // 创建一个全新的跟踪器
        window.__RUNTIME_ACTION_TRACKER__ = {
            actions: [],
            isTracking: false,
            startTracking: function() {
                console.log('=== 开始跟踪用户操作 ===');
                this.isTracking = true;
                this.actions = [];
            },
            stopTracking: function() {
                console.log('=== 停止跟踪用户操作 ===');
                this.isTracking = false;
                console.log('捕获到的操作数:', this.actions.length);
            },
            addAction: function(action) {
                if (this.isTracking) {
                    console.log('=== 捕获到用户操作 ===');
                    console.log('操作类型:', action.type);
                    console.log('目标元素:', action.target);
                    console.log('调用链:', action.callChain);
                    this.actions.push(action);
                }
            }
        };

        // 标记已安装
        window.__RUNTIME_ACTION_TRACKER_INSTALLED__ = true;
        console.log('=== 用户操作跟踪器安装完成 ===');
        return true;
    })()
    """

    result = _eval(cdp, expression, return_by_value=True)
    print(f"跟踪器安装结果: {result}")


def start_tracking(cdp: Any) -> bool:
    """
    开始跟踪用户操作
    """
    expression = r"""
    (() => {
        if (window.__RUNTIME_ACTION_TRACKER__) {
            window.__RUNTIME_ACTION_TRACKER__.startTracking();
            
            // 移除可能存在的旧监听器
            if (window.__RUNTIME_ACTION_TRACKER_CLICK_HANDLER__) {
                document.removeEventListener('click', window.__RUNTIME_ACTION_TRACKER_CLICK_HANDLER__, true);
            }
            
            // 增强的调用栈获取函数
            function getEnhancedCallStack() {
                try {
                    // 创建一个错误对象来获取调用栈
                    const error = new Error();
                    let stack = error.stack || '';
                    
                    // 增强调用栈信息
                    console.log('原始调用栈:', stack);
                    
                    // 解析调用栈
                    const stackLines = stack.split('\n').filter(line => line.trim() !== '');
                    const callChain = [];
                    
                    console.log('解析的调用栈行数:', stackLines.length);
                    
                    // 遍历所有栈行，不跳过任何行
                    for (let i = 0; i < stackLines.length; i++) {
                        const line = stackLines[i].trim();
                        console.log(`第 ${i} 行: ${line}`);
                        
                        // 尝试匹配各种调用栈格式
                        let match = null;
                        
                        // 格式1: at functionName (location)
                        match = line.match(/at\s+([^\(]+)\s+\(([^\)]+)\)/);
                        if (match) {
                            console.log('匹配格式1:', match);
                            let funcName = match[1] || 'anonymous';
                            let location = match[2] || 'unknown';
                            
                            // 清理函数名
                            funcName = funcName.trim().replace(/^function\s+/, '');
                            
                            // 过滤掉无关的函数调用
                            const irrelevantKeywords = ['clickHandler', 'addEventListener', '__RUNTIME_ACTION_TRACKER__'];
                            const isIrrelevant = irrelevantKeywords.some(keyword => funcName.includes(keyword) || location.includes(keyword));
                            
                            if (!isIrrelevant) {
                                callChain.push({
                                    function: funcName,
                                    location: location
                                });
                            }
                            continue;
                        }
                        
                        // 格式2: at location
                        match = line.match(/at\s+([^\s]+)/);
                        if (match) {
                            console.log('匹配格式2:', match);
                            let location = match[1] || 'unknown';
                            
                            // 过滤掉无关的位置
                            const irrelevantKeywords = ['clickHandler', 'addEventListener', '__RUNTIME_ACTION_TRACKER__'];
                            const isIrrelevant = irrelevantKeywords.some(keyword => location.includes(keyword));
                            
                            if (!isIrrelevant) {
                                callChain.push({
                                    function: 'anonymous',
                                    location: location
                                });
                            }
                            continue;
                        }
                        
                        // 格式3: 直接的函数名
                        match = line.match(/^(\w+)(?:\s*\()/);
                        if (match) {
                            console.log('匹配格式3:', match);
                            let funcName = match[1] || 'anonymous';
                            
                            callChain.push({
                                function: funcName,
                                location: 'unknown'
                            });
                        }
                    }
                    
                    // 如果调用链为空，尝试使用替代方法获取
                    if (callChain.length === 0 && stack) {
                        console.log('调用链为空，尝试使用替代方法获取');
                        // 直接返回原始栈信息
                        callChain.push({
                            function: 'stack_info',
                            location: stack.substring(0, 500) // 限制长度
                        });
                    }
                    
                    console.log('最终调用链:', callChain);
                    return callChain;
                } catch (err) {
                    console.error('获取调用栈错误:', err);
                    return [{
                        function: 'error',
                        location: err.message
                    }];
                }
            }
            
            // 定义点击处理函数
            const clickHandler = function(e) {
                // 只处理按钮点击事件
                if (e.target.tagName === 'BUTTON' || e.target.classList.contains('btn')) {
                    // 捕获增强的调用链
                    const callChain = getEnhancedCallStack();
                    console.log('增强的调用链:', callChain);
                    
                    // 记录操作
                    window.__RUNTIME_ACTION_TRACKER__.addAction({
                        type: 'click',
                        timestamp: new Date().toISOString(),
                        target: {
                            tagName: e.target.tagName,
                            id: e.target.id,
                            className: e.target.className,
                            innerText: e.target.innerText ? e.target.innerText.substring(0, 100) : ''
                        },
                        callChain: callChain
                    });
                    
                    // 停止事件传播，避免其他监听器捕获
                    e.stopPropagation();
                    // 移除监听器，确保只处理一次点击
                    document.removeEventListener('click', clickHandler, true);
                    console.log('点击事件监听器已移除，确保只处理一次点击');
                }
            };
            
            // 添加监听器
            document.addEventListener('click', clickHandler, true);
            // 保存监听器引用
            window.__RUNTIME_ACTION_TRACKER_CLICK_HANDLER__ = clickHandler;
            console.log('添加点击事件监听器完成');
            
            return true;
        }
        console.error('RUNTIME_ACTION_TRACKER 未安装');
        return false;
    })()
    """
    result = _eval(cdp, expression, return_by_value=True)
    print(f"开始跟踪结果: {result}")
    return result


def stop_tracking(cdp: Any) -> bool:
    """
    停止跟踪用户操作
    """
    expression = r"""
    (() => {
        if (window.__RUNTIME_ACTION_TRACKER__) {
            window.__RUNTIME_ACTION_TRACKER__.stopTracking();
            return true;
        }
        console.error('RUNTIME_ACTION_TRACKER 未安装');
        return false;
    })()
    """
    result = _eval(cdp, expression, return_by_value=True)
    print(f"停止跟踪结果: {result}")
    return result


def get_tracking_results(cdp: Any) -> List[Dict[str, Any]]:
    """
    获取跟踪结果，只返回按钮点击事件
    """
    expression = r"""
    (() => {
        if (window.__RUNTIME_ACTION_TRACKER__) {
            console.log('获取跟踪结果:', window.__RUNTIME_ACTION_TRACKER__.actions.length, '个操作');
            // 过滤只保留按钮点击事件
            const buttonClickActions = window.__RUNTIME_ACTION_TRACKER__.actions.filter(action => {
                return action.type === 'click' && 
                       (action.target.tagName === 'BUTTON' || 
                        action.target.className.includes('btn'));
            });
            console.log('过滤后按钮点击事件数量:', buttonClickActions.length);
            // 只返回第一个操作，避免重复输出
            return buttonClickActions.length > 0 ? [buttonClickActions[0]] : [];
        }
        console.error('RUNTIME_ACTION_TRACKER 未安装');
        return [];
    })()
    """
    result = _eval(cdp, expression, return_by_value=True)
    print(f"获取跟踪结果数量: {len(result) if isinstance(result, list) else 0}")
    return result if isinstance(result, list) else []


def track_user_action(cdp: Any, prompt_message: str, timeout: int = 30) -> Dict[str, Any]:
    """
    跟踪用户操作并返回操作经过的函数调用链
    
    Args:
        cdp: CDP会话对象
        prompt_message: 提示用户进行操作的消息
        timeout: 超时时间（秒）
    
    Returns:
        包含操作信息和函数调用链的字典
    """
    print("=" * 60)
    print(f"提示：{prompt_message}")
    print(f"请在 {timeout} 秒内完成操作...")
    print("=" * 60)
    
    # 安装跟踪器
    print("1. 安装用户操作跟踪器...")
    install_action_tracker(cdp)
    
    # 开始跟踪
    print("2. 开始跟踪用户操作...")
    start_tracking(cdp)
    
    # 等待用户操作
    print("3. 等待用户操作...")
    start_time = time.time()
    elapsed = 0
    actions = []
    while elapsed < timeout:
        time.sleep(1)
        elapsed = time.time() - start_time
        # 检查是否有操作记录
        temp_actions = get_tracking_results(cdp)
        if temp_actions:
            print(f"   检测到 {len(temp_actions)} 个操作，停止等待")
            actions = temp_actions
            break
        print(f"   已等待 {int(elapsed)} 秒...")
    
    # 停止跟踪
    print("4. 停止跟踪用户操作...")
    stop_tracking(cdp)
    
    # 如果没有获取到操作，再获取一次
    if not actions:
        print("5. 获取跟踪结果...")
        actions = get_tracking_results(cdp)
    
    if not actions:
        print("   未捕获到任何操作")
        return {
            "success": False,
            "message": "超时：未检测到用户操作",
            "actions": []
        }
    
    # 处理结果，提取函数调用链
    print(f"   成功捕获 {len(actions)} 个用户操作")
    result = {
        "success": True,
        "message": f"成功捕获 {len(actions)} 个用户操作",
        "actions": []
    }
    
    for i, action in enumerate(actions):
        print(f"   操作 {i+1}: {action.get('type', 'unknown')}")
        action_info = {
            "type": action.get("type", "unknown"),
            "timestamp": action.get("timestamp", ""),
            "target": action.get("target", {}),
            "function_chain": [
                f"{item.get('function', 'unknown')} ({item.get('location', 'unknown')})"
                for item in action.get("callChain", [])
            ]
        }
        result["actions"].append(action_info)
    
    print("=" * 60)
    return result
