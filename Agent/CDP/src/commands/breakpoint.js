/**
 * 断点命令模块
 * 处理命令行中的断点相关操作
 */

class BreakpointCommand {
  constructor(debuggerModule) {
    this.debugger = debuggerModule;
  }

  /**
   * 注册断点命令
   * @param {Commander} program - Commander实例
   */
  register(program) {
    // 断点命令组
    const breakpoint = program.command('breakpoint')
      .alias('bp')
      .description('断点管理命令');

    // 设置断点
    breakpoint.command('set <url> <line>')
      .description('在指定文件的指定行设置断点')
      .option('-c, --condition <condition>', '设置条件表达式')
      .option('-i, --ignore <count>', '设置忽略次数', parseInt)
      .option('-b, --breakpoints', '行号是基于格式化代码的行号（与view -b/--breakpoints显示的虚拟行号对应）')
      .action(async (url, line, options) => {
        try {
          // 调用_setupInteractiveDebugger方法来设置断点并启动交互式调试
          await this._setupInteractiveDebugger(url, line, options);
        } catch (error) {
          console.error(`设置断点失败: ${error.message}`);
          process.exit(1);
        }
      });

    // 移除断点
    breakpoint.command('remove <id>')
      .description('移除指定ID的断点')
      .action(async (id) => {
        try {
          await this.debugger.removeBreakpoint(id);
          process.exit(0);
        } catch (error) {
          console.error(`移除断点失败: ${error.message}`);
          process.exit(1);
        }
      });

    // 列出所有断点
    breakpoint.command('list')
      .description('列出所有已设置的断点')
      .action(async () => {
        try {
          const breakpoints = await this.debugger.getAllBreakpoints();
          
          if (breakpoints.length === 0) {
            console.log('当前没有设置任何断点');
          } else {
            console.log('\n🔍 已设置的断点:');
            console.log('------------------------------------------');
            console.log('ID                 位置                        类型');
            console.log('------------------------------------------');
            
            breakpoints.forEach(bp => {
              if (bp.type === 'dom') {
                console.log(`${bp.id.padEnd(18)} ${bp.selector.padEnd(30)} ${bp.domType}`);
              } else {
                console.log(`${bp.id.padEnd(18)} ${bp.url.padEnd(24)}:${bp.lineNumber.toString().padStart(4)} 普通断点`);
              }
            });
            console.log('------------------------------------------');
          }
          process.exit(0);
        } catch (error) {
          console.error(`❌ 列出断点失败: ${error.message}`);
        }
      });

    // 清除所有断点
    breakpoint.command('clear')
      .description('清除所有断点')
      .action(async () => {
        try {
          await this.debugger.clearAllBreakpoints();
          process.exit(0);
        } catch (error) {
          console.error(`清除断点失败: ${error.message}`);
          process.exit(1);
        }
      });

    // 启用断点
    breakpoint.command('enable <id>')
      .description('启用指定ID的断点')
      .action(async (id) => {
        try {
          await this.debugger.setBreakpointEnabled(id, true);
          process.exit(0);
        } catch (error) {
          console.error(`启用断点失败: ${error.message}`);
          process.exit(1);
        }
      });

    // 禁用断点
    breakpoint.command('disable <id>')
      .description('禁用指定ID的断点')
      .action(async (id) => {
        try {
          await this.debugger.setBreakpointEnabled(id, false);
          process.exit(0);
        } catch (error) {
          console.error(`禁用断点失败: ${error.message}`);
          process.exit(1);
        }
      });

    // 设置条件断点
    breakpoint.command('conditional <url> <line> <condition>')
      .description('在指定文件的指定行设置条件断点')
      .action(async (url, line, condition) => {
        try {
          const lineNumber = parseInt(line);
          if (isNaN(lineNumber) || lineNumber < 1) {
            console.error('行号必须是大于0的整数');
            process.exit(1);
          }

          const breakpointId = await this.debugger.setConditionalBreakpoint(url, lineNumber, condition);
          console.log(`条件断点ID: ${breakpointId}`);
          console.log(`条件: ${condition}`);
          process.exit(0);
        } catch (error) {
          console.error(`设置条件断点失败: ${error.message}`);
          process.exit(1);
        }
      });



    // 设置DOM断点
    breakpoint.command('dom <selector> <type>')
      .description('设置DOM断点')
      .action(async (selector, type) => {
        try {
          const validTypes = ['subtree-modified', 'attribute-modified', 'node-removed'];
          if (!validTypes.includes(type)) {
            console.error(`无效的DOM断点类型。有效值: ${validTypes.join(', ')}`);
            process.exit(1);
          }

          const breakpointId = await this.debugger.setDOMBreakpoint(selector, type);
          console.log(`DOM断点ID: ${breakpointId}`);
        } catch (error) {
          console.error(`设置DOM断点失败: ${error.message}`);
          process.exit(1);
        }
      });

    // 继续执行
    program.command('continue')
      .alias('c')
      .description('继续执行代码')
      .action(async () => {
        try {
          await this.debugger.resume();
          process.exit(0);
        } catch (error) {
          console.error(`继续执行失败: ${error.message}`);
          process.exit(1);
        }
      });

    // 单步执行
    program.command('next')
      .alias('n')
      .description('单步执行（跳过函数调用）')
      .action(async () => {
        try {
          await this.debugger.stepOver();
          process.exit(0);
        } catch (error) {
          console.error(`单步执行失败: ${error.message}`);
          process.exit(1);
        }
      });

    // 步入函数
    program.command('step')
      .alias('s')
      .description('步入函数')
      .action(async () => {
        try {
          await this.debugger.stepInto();
          process.exit(0);
        } catch (error) {
          console.error(`步入函数失败: ${error.message}`);
          process.exit(1);
        }
      });

    // 步出函数
    program.command('out')
      .alias('o')
      .description('步出函数')
      .action(async () => {
        try {
          await this.debugger.stepOut();
          process.exit(0);
        } catch (error) {
          console.error(`步出函数失败: ${error.message}`);
          process.exit(1);
        }
      });

    // 计算表达式
    program.command('eval <expression>')
      .description('在当前断点处计算表达式')
      .option('-f, --frame <index>', '指定调用栈帧索引', parseInt, 0)
      .action(async (expression, options) => {
        try {
          const result = await this.debugger.evaluate(expression, options.frame);
          console.log('\n表达式结果:');
          console.log(result);
          process.exit(0);
        } catch (error) {
          console.error(`计算表达式失败: ${error.message}`);
          process.exit(1);
        }
      });

    // 添加别名命令，简化常用操作
    program.command('break <url> <line>')
      .description('快速在指定位置设置断点（breakpoint set的别名）')
      .option('-c, --condition <condition>', '设置条件表达式')
      .option('-i, --ignore <count>', '设置忽略次数', parseInt)
      .option('-f, --formatted', '行号是基于格式化代码的行号')
      .action(async (url, line, options) => {
        await this._setupInteractiveDebugger(url, line, options);
      });
    
    // 添加create命令别名，用于创建新断点
    program.command('create <url> <line>')
      .description('创建新断点（与break命令功能相同）')
      .option('-c, --condition <condition>', '设置条件表达式')
      .option('-i, --ignore <count>', '设置忽略次数', parseInt)
      .option('-f, --formatted', '行号是基于格式化代码的行号')
      .action(async (url, line, options) => {
        await this._setupInteractiveDebugger(url, line, options);
      });

    // 调试器信息
    program.command('breakpoints')
      .description('显示所有断点（breakpoint list的别名）')
      .action(async () => {
        try {
          const breakpoints = await this.debugger.getAllBreakpoints();
          
          if (breakpoints.length === 0) {
            console.log('当前没有设置任何断点');
          } else {
            console.log('\n已设置的断点:');
            console.log('------------------------------------------');
            console.log('ID                 位置                        类型');
            console.log('------------------------------------------');
            
            breakpoints.forEach(bp => {
              if (bp.type === 'dom') {
                console.log(`${bp.id.padEnd(18)} ${bp.selector.padEnd(30)} ${bp.domType}`);
              } else {
                console.log(`${bp.id.padEnd(18)} ${bp.url.padEnd(24)}:${bp.lineNumber.toString().padStart(4)} 普通断点`);
              }
            });
            console.log('------------------------------------------');
          }
          process.exit(0);
        } catch (error) {
          console.error(`列出断点失败: ${error.message}`);
          process.exit(1);
        }
      });
  }

  /**
   * 初始化命令
   * @returns {Promise<void>}
   */
  async initialize() {
    try {
      await this.debugger.initialize();
      console.log('断点命令模块初始化成功');
      
      // 初始化内部状态
      this._rl = null; // readline接口
      this._breakpointsCount = 0; // 跟踪设置的断点数量
      
    } catch (error) {
      console.error('断点命令模块初始化失败:', error.message);
      process.exit(1);
    }
  }
  
  /**
   * 设置交互式调试环境
   * @private
   */
  async _setupInteractiveDebugger(url, line, options = {}) {
    try {
      const lineNumber = parseInt(line);
      if (isNaN(lineNumber) || lineNumber < 1) {
        console.error('❌ 行号必须是大于0的整数');
        return;
      }
      
        // 当使用--breakpoints选项时，需要先获取文件内容以生成位置映射
      if (options.breakpoints && this.debugger.fileViewer) {
        try {
          // 获取文件内容以生成位置映射
          await this.debugger.fileViewer.getFileContent(url, 1, null, null, true);
          console.log('已获取文件位置映射信息');
        } catch (err) {
          console.error('获取文件位置映射失败:', err.message);
        }
      }
      
      // 设置断点，传递格式化选项
      const breakpointOptions = {
        condition: options.condition,
        ignoreCount: options.ignore,
        formatted: options.breakpoints
      };
      
      const breakpointId = await this.debugger.setBreakpoint(url, lineNumber, breakpointOptions);
      
      // 检查是否是重复断点
      if (breakpointId === null) {
        console.log(`ℹ️  不设置断点，但已打开调试页面`);
      } else {
        this._breakpointsCount++;
        console.log(`✅ 断点设置成功!`);
        console.log(`   断点ID: ${breakpointId}`);
        console.log(`   文件: ${url}`);
        console.log(`   行号: ${lineNumber}`);
        console.log(`   当前断点总数: ${this._breakpointsCount}`);
      }
      
      // 检查是否已有活跃的readline界面
      if (!this._rl) {
        // 首次创建readline接口
        const readline = require('readline');
        this._rl = readline.createInterface({
          input: process.stdin,
          output: process.stdout,
          prompt: 'debug> '
        });
        
        // 设置事件处理器（只设置一次）
        this._setupReadlineHandlers();
        
        // 提示可用命令
        console.log('\n🔧 可用调试命令:');
        console.log('  continue (c): 继续执行');
        console.log('  next (n): 单步跳过');
        console.log('  step (s): 单步进入');
        console.log('  out (o): 单步退出');
        console.log('  quit (q): 退出调试');
        console.log('  eval <expression>: 执行表达式');
        console.log('  breakpoints (bps): 列出所有断点');
        console.log('  break/b/create <file> <line>: 添加新断点');
        console.log('  remove <id>: 删除指定断点');
        console.log('  clear: 清除所有断点');
        console.log('  help: 显示此帮助信息');
      }
      
      // 设置断点命中事件监听器
      if (!this._breakpointHitListener) {
        this._breakpointHitListener = (event) => {
          console.log('\n🎯 断点命中!');
          console.log(`   位置: ${event.url} 第 ${event.lineNumber} 行`);
          
          // 如果有格式化位置信息，显示出来
          if (event.formattedPosition) {
            console.log(`   格式化代码位置: 第 ${event.formattedPosition.formattedLine} 行 第 ${event.formattedPosition.formattedColumn} 列`);
          }
          
          console.log(`   调用栈:`);
          
          // 显示调用栈信息
          if (event.callFrames && event.callFrames.length > 0) {
            event.callFrames.forEach((frame, index) => {
              // 确保frame有所有必要的属性
              const functionName = frame.functionName || '(匿名函数)';
              
              // 构造更友好的位置信息
              let locationInfo = 'unknown';
              if (frame.url && frame.url !== 'unknown') {
                // 尝试提取文件名
                const urlParts = frame.url.split('/');
                const fileName = urlParts[urlParts.length - 1] || frame.url;
                
                // 确保行号和列号存在且是数字
                const lineNum = frame.lineNumber !== undefined && !isNaN(frame.lineNumber) 
                  ? parseInt(frame.lineNumber) + 1 // 转换为1基行号
                  : '?';
                
                const colNum = frame.columnNumber !== undefined && !isNaN(frame.columnNumber) 
                  ? parseInt(frame.columnNumber) + 1 // 转换为1基列号
                  : '?';
                
                locationInfo = `${fileName}:${lineNum}:${colNum}`;
              } else if (frame.scriptId) {
                locationInfo = `script:${frame.scriptId}`;
              }
              
              console.log(`     ${index}. ${functionName} (${locationInfo})`);
            });
          } else {
            console.log('     无可用调用栈信息');
          }
          
          // 继续提示用户输入命令
          if (this._rl) {
            this._rl.prompt();
          }
        };
        
        this.debugger.on('breakpointHit', this._breakpointHitListener);
      }
      
      // 设置断点恢复执行事件监听器
      if (!this._resumedListener) {
        this._resumedListener = () => {
          console.log('\n▶️  程序已恢复执行，等待下一个断点命中...');
          if (this._rl) {
            this._rl.prompt();
          }
        };
        
        this.debugger.on('resumed', this._resumedListener);
      }
      
      // 启动或重新显示命令提示
      if (this._rl) {
        console.log('\n💡 可以继续设置更多断点或等待断点命中...');
        this._rl.prompt();
      }
      
    } catch (error) {
      console.error(`❌ 设置断点失败: ${error.message}`);
      // 错误时也不立即退出，让用户可以继续尝试
      if (this._rl) {
        this._rl.prompt();
      }
    }
  }
  
  /**
   * 设置readline处理器，处理用户输入的调试命令
   * @private
   */
  _setupReadlineHandlers() {
    // 处理用户输入的调试命令
    this._rl.on('line', async (line) => {
      line = line.trim();
      
      try {
        // 命令解析
        const parts = line.split(/\s+/);
        const command = parts[0].toLowerCase();
        
        // 基础调试命令
        if (command === 'continue' || command === 'c') {
          await this.debugger.resume();
        } else if (command === 'next' || command === 'n') {
          await this.debugger.stepOver();
        } else if (command === 'step' || command === 's') {
          await this.debugger.stepInto();
        } else if (command === 'out' || command === 'o') {
          await this.debugger.stepOut();
        } else if (command.startsWith('eval')) {
          const expression = parts.slice(1).join(' ');
          if (expression) {
            const result = await this.debugger.evaluate(expression);
            console.log(`📝 表达式结果: ${result}`);
          } else {
            console.log('请输入要执行的表达式');
          }
          this._rl.prompt();
        } else if (command === 'quit' || command === 'q') {
          console.log('👋 退出调试...');
          this._cleanup();
        } 
        // 断点管理命令
        else if (command === 'breakpoints' || command === 'bps') {
          try {
            const breakpoints = await this.debugger.getAllBreakpoints();
            
            if (breakpoints.length === 0) {
              console.log('当前没有设置任何断点');
            } else {
              console.log('\n🔍 已设置的断点:');
              console.log('------------------------------------------');
              console.log('ID                 位置                        类型');
              console.log('------------------------------------------');
              
              breakpoints.forEach(bp => {
                if (bp.type === 'dom') {
                  console.log(`${bp.id.padEnd(18)} ${bp.selector.padEnd(30)} ${bp.domType}`);
                } else {
                  console.log(`${bp.id.padEnd(18)} ${bp.url.padEnd(24)}:${bp.lineNumber.toString().padStart(4)} 普通断点`);
                }
              });
              console.log('------------------------------------------');
            }
          } catch (error) {
            console.error(`❌ 列出断点失败: ${error.message}`);
          }
          this._rl.prompt();
        } else if (command === 'break' || command === 'b' || command === 'create') {
          if (parts.length >= 3) {
            const url = parts[1];
            const lineNumber = parseInt(parts[2], 10);
            if (!isNaN(lineNumber)) {
              await this._setupInteractiveDebugger(url, lineNumber);
            } else {
              console.log('❌ 无效的行号');
              this._rl.prompt();
            }
          } else {
            console.log('❌ 用法: break/create <file> <line>');
            this._rl.prompt();
          }
        } else if (command === 'remove') {
          if (parts.length >= 2) {
            try {
              await this.debugger.removeBreakpoint(parts[1]);
              this._breakpointsCount = Math.max(0, this._breakpointsCount - 1);
              console.log(`✅ 已删除断点: ${parts[1]}`);
            } catch (error) {
              console.error(`❌ 移除断点失败: ${error.message}`);
            }
            this._rl.prompt();
          } else {
            console.log('❌ 用法: remove <breakpointId>');
            this._rl.prompt();
          }
        } else if (command === 'clear') {
          try {
            await this.debugger.clearAllBreakpoints();
            this._breakpointsCount = 0;
            console.log('✅ 已清除所有断点');
          } catch (error) {
            console.error(`❌ 清除断点失败: ${error.message}`);
          }
          this._rl.prompt();
        } else if (command === 'var') {
          try {
            console.log('🔍 正在获取当前作用域变量...');
            const variables = await this.debugger.getAllScopeVariables(0, 3);
            
            // 导出到文件
            const outputPath = await this.debugger.exportVariablesToFile(variables);
            
            console.log('\n📋 当前作用域变量摘要:');
            console.log('='.repeat(80));
            
            let varCount = 0;
            for (const [scopeName, scopeVars] of Object.entries(variables)) {
              if (scopeName === '调用信息') {
                console.log(`\n🔍 ${scopeName}:`);
                for (const [key, value] of Object.entries(scopeVars)) {
                  console.log(`  ${key}: ${value}`);
                }
              } else if (scopeName === 'this') {
                console.log(`\n🔍 this: ${this._formatVariableDisplay(scopeVars)}`);
              } else if (typeof scopeVars === 'object' && scopeVars !== null) {
                const keys = Object.keys(scopeVars);
                console.log(`\n🔍 ${scopeName}: ${keys.length} 个变量`);
                varCount += keys.length;
                
                // 显示前5个变量的预览
                for (const [varName, varValue] of Object.entries(scopeVars).slice(0, 5)) {
                  console.log(`  ${varName}: ${this._formatVariableDisplay(varValue, 2)}`);
                }
                if (keys.length > 5) {
                  console.log(`  ... (还有 ${keys.length - 5} 个变量，已导出到文件)`);
                }
              }
            }
            
            console.log(`\n总计: ${varCount} 个变量`);
            console.log(`✅ 详细信息已导出到: ${outputPath}`);
          } catch (error) {
            console.error(`❌ 获取变量失败: ${error.message}`);
          }
          this._rl.prompt();
        } else if (command === 'code') {
          try {
            // 解析参数
            const contextLines = parts.length > 1 ? parseInt(parts[1], 10) : 3;
            const frameIndex = parts.length > 2 ? parseInt(parts[2], 10) : 0;
            
            console.log(`🔍 正在获取当前断点位置的代码上下文...`);
            const codeContext = await this.debugger.getCurrentCodeContext(contextLines, frameIndex);
            
            // 格式化输出
            console.log(`\n📄 代码上下文 (${codeContext.url})`);
            console.log(`📌 断点位置: 第 ${codeContext.lineNumber} 行`);
            if (codeContext.columnNumber) {
              console.log(`📌 断点列号: 第 ${codeContext.columnNumber} 列`);
            }
            console.log('='.repeat(80));
            
            codeContext.contextLines.forEach(lineInfo => {
              const lineNumber = lineInfo.line.toString().padStart(4, ' ');
              const marker = lineInfo.isCurrent ? '→' : ' ';
              
              // 处理当前执行行的情况（单行和多行文件通用）
              if (lineInfo.isCurrent && lineInfo.columnNumber !== undefined) {
                // 在执行位置插入标记
                const content = lineInfo.content;
                const column = lineInfo.columnNumber;
                
                // 确保列号在有效范围内
                const safeColumn = Math.min(Math.max(0, column), content.length);
                
                // 插入标记 [我是标记]
                const markedContent = content.slice(0, safeColumn) + '[我是标记]' + content.slice(safeColumn);
                
                // 显示带有标记的行内容
                console.log(`${marker} ${lineNumber} | ${markedContent}`);
                
                // 对于单行文件，仍然显示箭头标记
                if (codeContext.totalLines === 1) {
                  const indent = `    | `.length;
                  const arrowLine = ' '.repeat(indent + safeColumn) + '↑';
                  console.log(arrowLine);
                }
              } else {
                // 处理非当前行的情况
                console.log(`${marker} ${lineNumber} | ${lineInfo.content}`);
              }
            });
            
            console.log('='.repeat(80));
            console.log(`📊 共显示 ${codeContext.contextLines.length} 行，文件总计 ${codeContext.totalLines} 行`);
            if (codeContext.totalLines === 1) {
              console.log(`📏 行长度: ${codeContext.contextLines[0].content.length} 字符`);
            }
          } catch (error) {
            console.error(`❌ 获取代码上下文失败: ${error.message}`);
          }
          this._rl.prompt();
        }
        // 帮助命令
        else if (command === 'help' || command === 'h' || command === '?') {
          console.log('\n🔧 可用命令:');
          console.log('  continue (c): 继续执行');
          console.log('  next (n): 单步跳过');
          console.log('  step (s): 单步进入');
          console.log('  out (o): 单步退出');
          console.log('  var: 导出当前作用域所有变量到文件');
          console.log('  code [lines] [frame]: 查看当前断点位置的代码上下文');
          console.log('  quit (q): 退出调试');
          console.log('  eval <expression>: 执行表达式');
          console.log('  breakpoints (bps): 列出所有断点');
          console.log('  break/b/create <file> <line>: 添加新断点');
          console.log('  remove <id>: 删除指定断点');
          console.log('  clear: 清除所有断点');
          console.log('  help/h/?: 显示帮助信息');
          this._rl.prompt();
        } else {
          console.log('❓ 未知命令，请输入 "help" 查看可用命令');
          this._rl.prompt();
        }
      } catch (error) {
        console.error('❌ 执行命令失败:', error.message);
        this._rl.prompt();
      }
    });
    
    // 处理SIGINT信号（Ctrl+C）
    process.on('SIGINT', () => {
      console.log('\n👋 接收到中断信号，退出调试...');
      this._cleanup();
    });
    
    // 处理readline关闭事件
    this._rl.on('close', () => {
      this._cleanup();
    });
  }
  
  /**
   * 清理资源并退出
   * @private
   */
  _cleanup() {
    // 移除事件监听器
    if (this._breakpointHitListener) {
      this.debugger.off('breakpointHit', this._breakpointHitListener);
      this._breakpointHitListener = null;
    }
    
    if (this._resumedListener) {
      this.debugger.off('resumed', this._resumedListener);
      this._resumedListener = null;
    }
    
    // 关闭readline接口
    if (this._rl) {
      this._rl.close();
      this._rl = null;
    }
    
    // 退出进程
    process.exit(0);
  }

  /**
   * 获取帮助信息
   * @returns {string}
   */
  getHelp() {
    return `
断点管理命令帮助:

  基本断点操作:
    cdp breakpoint set <url> <line>  - 在指定文件的指定行设置断点
    cdp break <url> <line>           - 快速设置断点（别名）
    cdp breakpoint remove <id>       - 移除指定ID的断点
    cdp breakpoint list              - 列出所有已设置的断点
    cdp breakpoints                  - 显示所有断点（别名）
    cdp breakpoint clear             - 清除所有断点

  断点控制:
    cdp breakpoint enable <id>       - 启用指定ID的断点
    cdp breakpoint disable <id>      - 禁用指定ID的断点

  高级断点:
    cdp breakpoint conditional <url> <line> <condition> - 设置条件断点
    cdp breakpoint dom <selector> <type> - 设置DOM断点（类型: subtree-modified, attribute-modified, node-removed）

  调试控制:
    cdp continue | c                 - 继续执行代码
    cdp next | n                     - 单步执行（跳过函数调用）
    cdp step | s                     - 步入函数
    cdp out | o                      - 步出函数
    cdp eval <expression>            - 在当前断点处计算表达式
    cdp code [lines] [frame]         - 查看当前断点位置的代码上下文

  示例:
    cdp break index.js 10
    cdp breakpoint conditional app.js 20 "x > 10"
    cdp breakpoint dom ".container" subtree-modified
    cdp continue
    cdp eval "document.title"
`;
  }

  /**
   * 格式化变量显示
   * @private
   * @param {*} value - 变量值
   * @param {number} indent - 缩进级别
   * @returns {string} 格式化的字符串
   */
  _formatVariableDisplay(value, indent = 0) {
    const indentStr = '  '.repeat(indent);
    
    if (value === null) return 'null';
    if (value === undefined) return 'undefined';
    if (typeof value === 'string') {
      return `"${value}"`;
    }
    if (typeof value === 'number' || typeof value === 'boolean') {
      return String(value);
    }
    if (typeof value === 'function') {
      return '[Function]';
    }
    if (typeof value === 'object') {
      if (value.type === 'object' && value.description) {
        return `[Object: ${value.description}]`;
      }
      if (value.type === 'array') {
        return `[Array(${value.preview || value.description || 'length unknown'})]`;
      }
      if (value.type === 'string') {
        return `"${value.value}"`;
      }
      if (value.type === 'number') {
        return String(value.value);
      }
      if (value.type === 'boolean') {
        return String(value.value);
      }
      return JSON.stringify(value, null, 2);
    }
    
    return String(value);
  }
}

module.exports = BreakpointCommand;