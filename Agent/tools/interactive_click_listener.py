from __future__ import annotations

from typing import Any, Dict, List, Optional
import time
import subprocess
import threading
import queue


class InteractiveClickListener:
    """
    交互式点击监听器类
    """
    def __init__(self):
        self.process = None
        self.stdout_queue = queue.Queue()
        self.stderr_queue = queue.Queue()
        self.running = False
        self.stdout_thread = None
        self.stderr_thread = None
    
    def start(self) -> Dict[str, Any]:
        """
        启动交互式点击监听器
        
        Returns:
            包含启动结果的字典
        """
        print("=" * 60)
        print("启动交互式点击监听器...")
        print("请在网页上点击任意按钮...")
        print("=" * 60)
        
        # 启动node命令
        try:
            self.process = subprocess.Popen(
                ["node", "bin/cli.js", "click", "start"],
                cwd=r"d:\Projects\Dagent\Agent\CDP",
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                encoding='utf-8'
            )
            
            self.running = True
            
            # 启动线程读取输出
            self.stdout_thread = threading.Thread(target=self._read_stdout)
            self.stderr_thread = threading.Thread(target=self._read_stderr)
            
            self.stdout_thread.daemon = True
            self.stderr_thread.daemon = True
            
            self.stdout_thread.start()
            self.stderr_thread.start()
            
            # 等待监听器启动完成
            time.sleep(2)
            
            # 检查是否有错误
            if self.process.poll() is not None:
                return {
                    "success": False,
                    "message": "监听器启动失败",
                    "error": self._get_error_output()
                }
            
            return {
                "success": True,
                "message": "监听器已成功启动，正在等待点击事件..."
            }
        except Exception as e:
            return {
                "success": False,
                "message": "监听器启动失败",
                "error": str(e)
            }
    
    def _read_stdout(self):
        """
        读取标准输出
        """
        while self.running and self.process:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                line = line.strip()
                self.stdout_queue.put(line)
                print(f"[监听器输出] {line}")
            except Exception as e:
                print(f"读取标准输出错误: {e}")
                break
    
    def _read_stderr(self):
        """
        读取标准错误
        """
        while self.running and self.process:
            try:
                line = self.process.stderr.readline()
                if not line:
                    break
                line = line.strip()
                self.stderr_queue.put(line)
                print(f"[监听器错误] {line}")
            except Exception as e:
                print(f"读取标准错误错误: {e}")
                break
    
    def _get_error_output(self) -> str:
        """
        获取错误输出
        """
        error_output = []
        while not self.stderr_queue.empty():
            error_output.append(self.stderr_queue.get())
        return "\n".join(error_output)
    
    def execute_command(self, command: str) -> Dict[str, Any]:
        """
        在交互式会话中执行命令
        
        Args:
            command: 要执行的命令
        
        Returns:
            包含命令执行结果的字典
        """
        if not self.running or not self.process:
            return {
                "success": False,
                "message": "监听器未启动"
            }
        
        print("=" * 60)
        print(f"执行命令: {command}")
        print("=" * 60)
        
        try:
            # 发送命令
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()
            
            # 等待命令执行完成
            time.sleep(1)
            
            # 收集输出
            output = []
            while not self.stdout_queue.empty():
                output.append(self.stdout_queue.get())
            
            # 检查是否有错误
            error_output = self._get_error_output()
            
            if error_output:
                return {
                    "success": False,
                    "message": f"命令 {command} 执行失败",
                    "error": error_output,
                    "output": "\n".join(output)
                }
            
            return {
                "success": True,
                "message": f"命令 {command} 执行成功",
                "output": "\n".join(output)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"命令 {command} 执行失败",
                "error": str(e)
            }
    
    def stop(self) -> Dict[str, Any]:
        """
        停止监听器
        
        Returns:
            包含停止结果的字典
        """
        if not self.running or not self.process:
            return {
                "success": False,
                "message": "监听器未启动"
            }
        
        print("=" * 60)
        print("停止监听器...")
        print("=" * 60)
        
        try:
            # 发送停止命令
            self.process.stdin.write("stop\n")
            self.process.stdin.flush()
            
            # 等待进程结束
            self.process.wait(timeout=5)
            
            self.running = False
            
            # 收集剩余输出
            output = []
            while not self.stdout_queue.empty():
                output.append(self.stdout_queue.get())
            
            return {
                "success": True,
                "message": "监听器已成功停止",
                "output": "\n".join(output)
            }
        except Exception as e:
            # 强制终止进程
            if self.process:
                self.process.terminate()
                self.process.wait(timeout=2)
            
            self.running = False
            
            return {
                "success": False,
                "message": "监听器停止失败",
                "error": str(e)
            }


def start_interactive_listener() -> InteractiveClickListener:
    """
    启动交互式点击监听器
    
    Returns:
        InteractiveClickListener实例
    """
    listener = InteractiveClickListener()
    result = listener.start()
    print(f"启动结果: {result['message']}")
    return listener


def execute_command(listener: InteractiveClickListener, command: str) -> Dict[str, Any]:
    """
    在交互式会话中执行命令
    
    Args:
        listener: InteractiveClickListener实例
        command: 要执行的命令
    
    Returns:
        包含命令执行结果的字典
    """
    return listener.execute_command(command)


def stop_listener(listener: InteractiveClickListener) -> Dict[str, Any]:
    """
    停止监听器
    
    Args:
        listener: InteractiveClickListener实例
    
    Returns:
        包含停止结果的字典
    """
    return listener.stop()
