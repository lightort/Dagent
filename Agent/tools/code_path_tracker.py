"""
代码路径追踪工具
用于追踪用户操作过程中经过的代码路径
"""

import subprocess
import threading
import time
import os
import re
from typing import Dict, Any, List, Optional
from datetime import datetime


class CodePathTracker:
    """代码路径追踪器"""
    
    # 库代码黑名单 - 当检测到这些库时跳过记录
    LIBRARY_BLACKLIST = [
        'jquery', 'react', 'lodash', 'underscore', 'vue', 'angular',
        'bootstrap', 'moment', 'axios', 'fetch', 'webpack', 'babel',
        'typescript', 'core-js', 'regenerator-runtime', 'polyfill',
        'modernizr', 'sizzle', 'qunit', 'mocha', 'jest', 'chai',
        'd3', 'chart', 'three', 'pixi', 'phaser', 'babylon',
        'antd', 'element-ui', 'vuetify', 'material-ui', 'bootstrap-vue',
        'semantic-ui', 'foundation', 'bulma', 'tailwind',
        'immutable', 'redux', 'mobx', 'vuex', 'pinia', 'zustand',
        'react-router', 'vue-router', 'react-dom', 'next', 'nuxt',
        'express', 'koa', 'fastify', 'hapi', 'nestjs', 'egg',
        'mongoose', 'sequelize', 'typeorm', 'prisma', 'knex',
        'socket.io', 'ws', 'sockjs', 'stomp',
        'webpack', 'rollup', 'parcel', 'vite', 'esbuild', 'swc',
        'babel', 'typescript', 'coffeescript', 'livescript',
        'sass', 'less', 'stylus', 'postcss', 'autoprefixer',
        'eslint', 'prettier', 'stylelint', 'tslint',
        'jest', 'mocha', 'chai', 'sinon', 'cypress', 'playwright',
        'puppeteer', 'selenium', 'webdriver', 'karma', 'jasmine',
        'lodash', 'underscore', 'ramda', 'immutable', 'mori',
        'moment', 'date-fns', 'dayjs', 'luxon', 'timezone',
        'axios', 'fetch', 'superagent', 'request', 'got', 'node-fetch',
        'cheerio', 'jsdom', 'puppeteer', 'playwright', 'selenium',
        'canvas', 'fabric', 'konva', 'paper', 'two', 'p5',
        'three', 'babylon', 'phaser', 'pixi', 'cocos', 'unity',
        'tensorflow', 'onnx', 'brain', 'synaptic', 'ml5',
        'chart', 'd3', 'highcharts', 'echarts', 'plotly', 'recharts',
        'mapbox', 'leaflet', 'openlayers', 'google-maps', 'baidu-maps',
        'video', 'audio', 'mediaelement', 'plyr', 'videojs', 'hls',
        'pdf', 'jspdf', 'pdfmake', 'pdfkit', 'pagedjs',
        'xlsx', 'csv', 'papaparse', 'sheetjs', 'exceljs',
        'crypto', 'bcrypt', 'hash', 'uuid', 'nanoid',
        'validator', 'ajv', 'joi', 'yup', 'zod', 'superstruct',
        'i18n', 'intl', 'react-intl', 'vue-i18n', 'i18next',
        'analytics', 'gtag', 'mixpanel', 'amplitude', 'segment',
        'sentry', 'bugsnag', 'rollbar', 'airbrake', 'honeybadger',
        'log', 'winston', 'bunyan', 'pino', 'log4js', 'debug',
        'config', 'dotenv', 'convict', 'nconf', 'configstore',
        'cache', 'lru-cache', 'node-cache', 'redis', 'memcached',
        'queue', 'bull', 'bee-queue', 'kue', 'agenda', 'node-schedule',
        'email', 'nodemailer', 'sendgrid', 'mailgun', 'aws-ses',
        'sms', 'twilio', 'nexmo', 'plivo', 'messagebird',
        'push', 'web-push', 'onesignal', 'firebase', 'pusher',
        'payment', 'stripe', 'paypal', 'braintree', 'square',
        'auth', 'passport', 'jsonwebtoken', 'oauth', 'openid',
        'oauth2', 'oidc', 'keycloak', 'auth0', 'firebase-auth',
        'storage', 'localforage', 'pouchdb', 'rxdb', 'watermelon',
        'webrtc', 'simple-peer', 'peerjs', 'socket.io', 'ws',
        'worker', 'workerize', 'comlink', 'threads', 'piscina',
        'wasm', 'assemblyscript', 'rust', 'emscripten', 'wasmer',
        'graphql', 'apollo', 'relay', 'urql', 'graphql-request',
        'rest', 'restify', 'feathers', 'loopback', 'sails',
        'rpc', 'grpc', 'trpc', 'json-rpc', 'xml-rpc',
        'soap', 'wsdl', 'rest', 'graphql', 'odata',
        'swagger', 'openapi', 'postman', 'insomnia', 'hoppscotch',
        'testing', 'cypress', 'playwright', 'puppeteer', 'selenium',
        'jest', 'mocha', 'chai', 'sinon', 'vitest', 'ava',
        'storybook', 'loki', 'chromatic', 'percy', 'backstop',
        'build', 'webpack', 'rollup', 'parcel', 'vite', 'esbuild',
        'deploy', 'vercel', 'netlify', 'heroku', 'aws', 'azure',
        'docker', 'kubernetes', 'helm', 'terraform', 'ansible',
        'ci', 'github-actions', 'gitlab-ci', 'jenkins', 'travis',
        'cd', 'argo', 'spinnaker', 'flux', 'flagger'
    ]
    
    def __init__(self, output_file: str = "code_path_trace.txt"):
        """
        初始化追踪器
        
        Args:
            output_file: 输出文件路径
        """
        self.output_file = output_file
        self.process = None
        self.output_thread = None
        self.error_thread = None
        self.running = False
        self.output_buffer = []
        self.error_buffer = []
        self.last_function = None
        self.last_location = None
        self.last_call_stack = None  # 存储上一次的调用栈
        self.code_path = []
        self.step_count = 0
        self.max_steps = 500
        self.in_library_code = False  # 标记是否在库代码中
        self.current_function = None  # 当前调用栈顶端函数
        self.function_count = 0  # 当前函数停留次数
        
    def _read_output(self):
        """读取标准输出"""
        try:
            while self.running:
                line = self.process.stdout.readline()
                if line:
                    decoded_line = line.decode('utf-8', errors='replace').strip()
                    self.output_buffer.append(decoded_line)
                    print(f"[输出] {decoded_line}")
        except Exception as e:
            print(f"读取标准输出错误: {e}")
    
    def _read_error(self):
        """读取标准错误"""
        try:
            while self.running:
                line = self.process.stderr.readline()
                if line:
                    decoded_line = line.decode('utf-8', errors='replace').strip()
                    self.error_buffer.append(decoded_line)
                    print(f"[错误] {decoded_line}")
        except Exception as e:
            print(f"读取标准错误错误: {e}")
    
    def start(self) -> Dict[str, Any]:
        """
        启动代码路径追踪
        
        Returns:
            启动结果
        """
        try:
            print("=" * 60)
            print("启动代码路径追踪器...")
            print("=" * 60)
            
            cdp_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "CDP")
            
            self.process = subprocess.Popen(
                ["node", "bin/cli.js", "click", "start"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cdp_path,
                shell=False
            )
            
            self.running = True
            
            self.output_thread = threading.Thread(target=self._read_output, daemon=True)
            self.output_thread.start()
            
            self.error_thread = threading.Thread(target=self._read_error, daemon=True)
            self.error_thread.start()
            
            time.sleep(2)
            
            return {
                "success": True,
                "message": "代码路径追踪器已启动，等待用户点击..."
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"启动失败: {str(e)}"
            }
    
    def _send_command(self, command: str) -> bool:
        """
        发送命令到进程
        
        Args:
            command: 命令字符串
        
        Returns:
            是否成功
        """
        try:
            if self.process and self.process.stdin:
                self.process.stdin.write((command + "\n").encode('utf-8'))
                self.process.stdin.flush()
                return True
            return False
        except Exception as e:
            print(f"发送命令失败: {e}")
            return False
    
    def _parse_location_from_output(self) -> Optional[Dict[str, Any]]:
        """
        从输出缓冲区解析当前位置信息
        
        Returns:
            位置信息字典
        """
        for i in range(len(self.output_buffer) - 1, max(-1, len(self.output_buffer) - 50), -1):
            line = self.output_buffer[i]
            
            location_match = re.search(r'位置:\s*(.+?)\s+第\s*(\d+)\s*行', line)
            if location_match:
                script = location_match.group(1)
                line_num = location_match.group(2)
                
                # 查找调用栈中的函数名
                function_name = "unknown"
                # 从当前位置向后搜索调用栈
                for j in range(i + 1, min(i + 20, len(self.output_buffer))):
                    stack_line = self.output_buffer[j]
                    # 匹配调用栈行，如 "0. clickHandler (chunk-858ed276.7bbb8c3f.js:23:13)"
                    func_match = re.search(r'\d+\.\s+([^\s(]+)\s*\(', stack_line)
                    if func_match:
                        function_name = func_match.group(1)
                        break
                    # 如果遇到下一个命令提示符，停止搜索
                    if "click-debug>" in stack_line:
                        break
                
                return {
                    "script": script,
                    "line": line_num,
                    "function": function_name,
                    "raw": line
                }
        
        return None
    
    def _parse_call_stack_from_output(self) -> Optional[str]:
        """
        从输出缓冲区解析调用栈
        
        Returns:
            调用栈字符串
        """
        for i in range(len(self.output_buffer) - 1, max(-1, len(self.output_buffer) - 50), -1):
            line = self.output_buffer[i]
            if "调用栈:" in line:
                stack_lines = []
                for j in range(i + 1, min(i + 15, len(self.output_buffer))):
                    stack_line = self.output_buffer[j]
                    if stack_line.strip() and not stack_line.startswith("click-debug>"):
                        stack_lines.append(stack_line)
                    else:
                        break
                return "\n".join(stack_lines)
        return None
    
    def _is_paused(self) -> bool:
        """
        检查程序是否处于暂停状态
        
        Returns:
            是否暂停
        """
        for line in self.output_buffer[-30:]:
            if "click-debug>" in line and "程序已恢复执行" not in line:
                return True
        return False
    
    def _get_code_context(self) -> Optional[str]:
        """
        获取当前代码上下文
        
        Returns:
            代码上下文字符串
        """
        # 直接查找带有箭头的代码行，这是实际的代码内容
        for line in reversed(self.output_buffer):
            if line.strip().startswith("→"):
                return line.strip()
        
        # 尝试查找其他格式的代码行
        code_lines = []
        in_code_block = False
        
        # 从后往前搜索，找到最新的代码上下文
        for line in reversed(self.output_buffer):
            if "📊 共显示" in line or "共显示" in line:
                # 找到了代码上下文的结束标记
                continue
            elif "============================================================================" in line:
                # 找到了代码上下文的分隔线
                in_code_block = not in_code_block
                continue
            elif in_code_block and line.strip():
                # 收集代码行
                code_lines.append(line.strip())
        
        if code_lines:
            # 反转代码行，使其恢复正确的顺序
            return "\n".join(reversed(code_lines))
        
        return None
    
    def _is_library_code(self, call_stack: Optional[str], location: Dict[str, Any]) -> bool:
        """
        检查当前代码是否是库代码
        
        Args:
            call_stack: 调用栈信息
            location: 位置信息
        
        Returns:
            是否是库代码
        """
        if not call_stack:
            return False
        
        # 检查调用栈中的文件路径
        for line in call_stack.strip().split('\n'):
            # 提取文件路径
            match = re.search(r'\(([^:]+):\d+:\d+\)', line)
            if match:
                file_path = match.group(1).lower()
                # 检查是否在黑名单中 - 使用更精确的匹配
                for lib in self.LIBRARY_BLACKLIST:
                    # 只匹配文件名包含库名的情况，避免函数名误判
                    # 例如：避免将 push.2b0e.Jr.i._wrapper 中的 push 误判为库
                    if lib.lower() in file_path:
                        # 进一步检查：确保库名是文件名的独立部分
                        # 避免匹配到函数名中的子字符串
                        file_name = os.path.basename(file_path)
                        # 使用单词边界匹配，确保库名是独立的
                        if re.search(r'\b' + re.escape(lib.lower()) + r'\b', file_name):
                            return True
        
        # 检查位置信息中的脚本路径
        script = location.get('script', '').lower()
        for lib in self.LIBRARY_BLACKLIST:
            if lib.lower() in script:
                # 进一步检查：确保库名是文件名的独立部分
                file_name = os.path.basename(script)
                if re.search(r'\b' + re.escape(lib.lower()) + r'\b', file_name):
                    return True
        
        return False
    
    def _normalize_call_stack(self, call_stack: Optional[str]) -> Optional[str]:
        """
        标准化调用栈，去除行号和列号的差异，并提取调用栈的关键特征
        
        Args:
            call_stack: 原始调用栈
        
        Returns:
            标准化后的调用栈
        """
        if not call_stack:
            return None
        
        normalized_lines = []
        for line in call_stack.strip().split('\n'):
            # 匹配调用栈行，如 "0. Object.fix (jquery-1.8.2.min.js:2:39097)" 或 "0. new p.Event (jquery-1.8.2.min.js:2:40118)"
            # 修改正则表达式，使其能够匹配包含方括号的函数名，如 "Function.bc [as find]"
            match = re.search(r'(\d+\.\s+)(?:new\s+)?([^\s(]+(?:\s+\[[^\]]+\])?)\s*\(([^:]+):\d+:\d+\)', line)
            if match:
                # 提取序号、函数名和文件路径，去除行号和列号
                index = match.group(1)
                function_name = match.group(2).strip()
                file_path = match.group(3)
                # 标准化为统一格式，只保留函数名和文件路径
                normalized_line = f"{function_name} ({file_path})"
                normalized_lines.append(normalized_line)
        
        # 返回调用栈的关键特征（函数名和文件路径的列表）
        # 使用管道符连接，便于比较
        return '|'.join(normalized_lines)
    
    def _get_call_stack_signature(self, call_stack: Optional[str]) -> Optional[str]:
        """
        获取调用栈的签名，用于比较调用栈是否相同
        
        Args:
            call_stack: 原始调用栈
        
        Returns:
            调用栈签名（包含完整的调用栈）
        """
        if not call_stack:
            return None
        
        # 标准化调用栈
        normalized = self._normalize_call_stack(call_stack)
        if not normalized:
            return None
        
        # 返回完整的标准化调用栈
        return normalized
    
    def _record_code_location(self, location: Dict[str, Any], call_stack: Optional[str], code_context: Optional[str] = None) -> bool:
        """
        记录代码位置
        
        Args:
            location: 位置信息
            call_stack: 调用栈信息
            code_context: 代码上下文
        
        Returns:
            是否记录成功
        """
        # 获取调用栈签名，用于比较调用栈是否相同
        call_stack_signature = self._get_call_stack_signature(call_stack)
        
        # 检查调用栈是否发生变化
        if call_stack_signature == self.last_call_stack:
            # 调用栈没有变化，不记录
            print("调用栈未变化，跳过记录")
            return False
        
        current_function = location.get("function", "")
        current_location = f"{location.get('script')}:{location.get('line')}"
        
        # 更新记录信息
        self.last_function = current_function
        self.last_location = current_location
        self.last_call_stack = call_stack_signature
        
        record = {
            "step": self.step_count,
            "timestamp": datetime.now().isoformat(),
            "location": location,
            "call_stack": call_stack,
            "code_context": code_context
        }
        
        self.code_path.append(record)
        
        with open(self.output_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"步骤 #{self.step_count}\n")
            f.write(f"时间: {record['timestamp']}\n")
            f.write(f"函数: {location.get('function', 'unknown')}\n")
            f.write(f"位置: {location.get('script', 'unknown')} 第 {location.get('line', '?')} 行\n")
            if call_stack:
                f.write(f"调用栈:\n{call_stack}\n")
            if code_context:
                f.write(f"\n代码上下文:\n{code_context}\n")
            f.write(f"{'='*60}\n")
        
        return True
    
    def track_until_complete(self, wait_for_click: bool = True) -> Dict[str, Any]:
        """
        追踪代码路径直到完成
        
        Args:
            wait_for_click: 是否等待用户点击
        
        Returns:
            追踪结果
        """
        try:
            if wait_for_click:
                print("\n" + "=" * 60)
                print("请在网页上点击任意元素...")
                print("点击后将自动开始追踪代码执行路径")
                print("=" * 60)
                
                timeout = 60
                start_time = time.time()
                breakpoint_hit = False
                
                while time.time() - start_time < timeout:
                    for line in self.output_buffer[-20:]:
                        if "点击事件触发断点" in line:
                            breakpoint_hit = True
                            break
                    
                    if breakpoint_hit:
                        break
                    
                    time.sleep(1)
                
                if not breakpoint_hit:
                    return {
                        "success": False,
                        "message": "等待用户点击超时"
                    }
                
                print("\n检测到断点触发，等待程序稳定...")
                time.sleep(1)
            
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(f"代码路径追踪记录\n")
                f.write(f"开始时间: {datetime.now().isoformat()}\n")
                f.write(f"{'='*60}\n\n")
            
            self.step_count = 0
            program_completed = False
            waiting_for_next_breakpoint = False
            
            while self.step_count < self.max_steps and not program_completed:
                # 检查是否有错误信息表明程序已结束
                for line in self.error_buffer[-30:]:
                    if "获取代码上下文失败: 当前未处于断点暂停状态" in line:
                        print("\n检测到程序已结束（未处于断点暂停状态），停止追踪")
                        program_completed = True
                        break
                
                if program_completed:
                    break
                
                if waiting_for_next_breakpoint:
                    print("等待下一次断点触发...")
                    timeout = 30
                    start_time = time.time()
                    breakpoint_hit = False
                    
                    while time.time() - start_time < timeout:
                        for line in self.output_buffer[-20:]:
                            if "点击事件触发断点" in line:
                                breakpoint_hit = True
                                break
                        
                        if breakpoint_hit:
                            break
                        
                        time.sleep(0.5)
                    
                    if not breakpoint_hit:
                        print("等待断点超时，追踪完成")
                        program_completed = True
                        break
                    
                    waiting_for_next_breakpoint = False
                    print("检测到新的断点，继续追踪...")
                    time.sleep(0.5)
                    continue
                
                self.step_count += 1
                
                # 先发送code命令获取代码上下文
                print("发送code命令获取代码上下文...")
                self._send_command("code")
                
                # 等待代码上下文输出
                code_wait_time = 0
                code_max_wait = 8  # 调整等待时间
                code_context = None
                
                while code_wait_time < code_max_wait:
                    time.sleep(0.2)  # 调整等待间隔
                    code_wait_time += 0.2
                    
                    # 每次等待后尝试获取代码上下文
                    code_context = self._get_code_context()
                    if code_context:
                        print("成功获取代码上下文")
                        break
                    
                    # 检查是否有错误信息
                    for line in self.output_buffer[-10:]:
                        if "获取代码上下文失败" in line or "未找到代码" in line:
                            print("获取代码上下文失败")
                            break
                
                if not code_context:
                    print("未获取到代码上下文，尝试再次获取...")
                    # 再次尝试获取
                    code_context = self._get_code_context()
                    if code_context:
                        print("第二次尝试成功获取代码上下文")
                    else:
                        print("仍然未获取到代码上下文")
                
                # 解析位置信息
                location = self._parse_location_from_output()
                call_stack = self._parse_call_stack_from_output()
                
                # 检查是否是库代码
                if location and self._is_library_code(call_stack, location):
                    if not self.in_library_code:
                        print(f"步骤 {self.step_count}: 进入库代码，使用 out 命令快速跳出...")
                        self.in_library_code = True
                    else:
                        print(f"步骤 {self.step_count}: 仍在库代码中，继续跳出...")
                    
                    # 发送 out 命令快速跳出当前函数
                    self._send_command("out")
                    
                    # 等待跳出完成
                    out_wait_time = 0
                    out_max_wait = 5
                    while out_wait_time < out_max_wait:
                        time.sleep(0.2)
                        out_wait_time += 0.2
                        
                        # 检查是否已跳出库代码
                        for line in self.output_buffer[-10:]:
                            if "click-debug>" in line:
                                break
                    
                    # 重置循环检测计数器
                    self.current_function = None
                    self.function_count = 0
                    continue
                else:
                    # 不在库代码中，重置标记
                    if self.in_library_code:
                        print(f"步骤 {self.step_count}: 已跳出库代码")
                        self.in_library_code = False
                
                # 循环检测：检查调用栈顶端函数是否停留三次不变
                # if location:
                #     # 提取调用栈顶端函数
                #     top_function = location.get('function', 'unknown')
                #     
                #     # 检查是否与当前函数相同
                #     if top_function == self.current_function:
                #         self.function_count += 1
                #         print(f"步骤 {self.step_count}: 函数 {top_function} 已停留 {self.function_count} 次")
                #         
                #         # 如果停留超过5次，认为陷入循环
                #         if self.function_count >= 5:
                #             print(f"步骤 {self.step_count}: 函数 {top_function} 停留超过5次，使用 out 命令快速跳出...")
                #             # 发送 out 命令快速跳出当前函数
                #             self._send_command("out")
                #             
                #             # 等待跳出完成
                #             out_wait_time = 0
                #             out_max_wait = 5
                #             while out_wait_time < out_max_wait:
                #                 time.sleep(0.2)
                #                 out_wait_time += 0.2
                #                 
                #                 # 检查是否已跳出循环
                #                 for line in self.output_buffer[-10:]:
                #                     if "click-debug>" in line:
                #                         break
                #             
                #             # 重置循环检测计数器
                #             self.current_function = None
                #             self.function_count = 0
                #             continue
                #     else:
                #         # 函数变化，重置计数器
                #         self.current_function = top_function
                #         self.function_count = 1
                #         print(f"步骤 {self.step_count}: 新函数 {top_function}")
                
                if location:
                    recorded = self._record_code_location(location, call_stack, code_context)
                    if recorded:
                        print(f"步骤 {self.step_count}: {location.get('function', 'unknown')} @ {location.get('script')}:{location.get('line')}")
                        if code_context:
                            print("  已记录代码上下文")
                    else:
                        print(f"步骤 {self.step_count}: 跳过记录（调用栈未变化）")
                else:
                    print(f"步骤 {self.step_count}: 未获取到位置信息")
                
                # 发送单步命令
                self._send_command("s")
                
                buffer_len_before = len(self.output_buffer)
                wait_time = 0
                max_wait = 3
                
                while wait_time < max_wait:
                    time.sleep(0.1)
                    wait_time += 0.1
                    
                    if len(self.output_buffer) > buffer_len_before:
                        new_output = "\n".join(self.output_buffer[buffer_len_before:])
                        if "程序已恢复执行" in new_output or "等待下次点击" in new_output:
                            print("\n程序已恢复执行，等待下一次断点...")
                            waiting_for_next_breakpoint = True
                            break
                        if "click-debug>" in new_output:
                            break
                
                if waiting_for_next_breakpoint:
                    continue
                
                if program_completed:
                    break
            
            with open(self.output_file, 'a', encoding='utf-8') as f:
                f.write(f"\n\n{'='*60}\n")
                f.write(f"追踪结束\n")
                f.write(f"结束时间: {datetime.now().isoformat()}\n")
                f.write(f"总步数: {self.step_count}\n")
                f.write(f"记录的代码位置数: {len(self.code_path)}\n")
                f.write(f"{'='*60}\n")
            
            return {
                "success": True,
                "message": f"追踪完成，共执行 {self.step_count} 步，记录 {len(self.code_path)} 个代码位置",
                "total_steps": self.step_count,
                "recorded_locations": len(self.code_path),
                "output_file": self.output_file
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"追踪过程出错: {str(e)}"
            }
    
    def stop(self) -> Dict[str, Any]:
        """
        停止追踪器
        
        Returns:
            停止结果
        """
        try:
            self.running = False
            
            if self.process and self.process.stdin:
                try:
                    self._send_command("quit")
                    time.sleep(0.5)
                except:
                    pass
            
            if self.process:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except:
                    self.process.kill()
            
            return {
                "success": True,
                "message": "追踪器已停止"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"停止失败: {str(e)}"
            }


def track_code_path(output_file: str = "code_path_trace.txt") -> Dict[str, Any]:
    """
    追踪代码路径的便捷函数
    
    Args:
        output_file: 输出文件路径
    
    Returns:
        追踪结果
    """
    tracker = CodePathTracker(output_file)
    
    start_result = tracker.start()
    if not start_result["success"]:
        return start_result
    
    track_result = tracker.track_until_complete(wait_for_click=True)
    
    tracker.stop()
    
    return track_result


if __name__ == "__main__":
    result = track_code_path("test_code_path.txt")
    print("\n" + "=" * 60)
    print("追踪结果:")
    print("=" * 60)
    print(f"成功: {result['success']}")
    print(f"消息: {result['message']}")
    if result['success']:
        print(f"输出文件: {result['output_file']}")
