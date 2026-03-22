/**
 * 点击事件监听命令
 * 用于监听网页点击操作并在点击时中断执行，提供交互式调试功能
 */

class ClickCommand {
  constructor(debuggerModule) {
    this.debugger = debuggerModule;
    this._rl = null;
    this._clickListener = null;
    this._resumedListener = null;
  }

  /**
   * 注册命令
   * @param {Object} program - Commander实例
   */
  register(program) {
    const click = program.command('click')
      .alias('clk')
      .description('点击事件监听命令');

    click.command('start')
      .description('开始监听点击事件，点击时触发断点')
      .action(async () => {
        try {
          await this._startClickMonitoring();
        } catch (error) {
          console.error('启动点击监听失败:', error.message);
          process.exit(1);
        }
      });

    click.command('stop')
      .description('停止监听点击事件')
      .action(async () => {
        try {
          await this._stopClickMonitoring();
          process.exit(0);
        } catch (error) {
          console.error('停止点击监听失败:', error.message);
          process.exit(1);
        }
      });

    click.command('status')
      .description('查看点击事件监听状态')
      .action(async () => {
        try {
          const isEnabled = await this.debugger.isClickBreakpointEnabled();
          console.log(`\n🖱️  点击事件监听状态: ${isEnabled ? '✅ 已启用' : '❌ 未启用'}`);
          process.exit(0);
        } catch (error) {
          console.error('查看状态失败:', error.message);
          process.exit(1);
        }
      });
  }

  /**
   * 开始点击事件监听
   * @private
   */
  async _startClickMonitoring() {
    try {
      await this.debugger.enableClickBreakpoint();

      if (!this._rl) {
        const readline = require('readline');
        this._rl = readline.createInterface({
          input: process.stdin,
          output: process.stdout,
          prompt: 'click-debug> '
        });

        this._setupReadlineHandlers();
      }

      if (!this._clickListener) {
        this._clickListener = (event) => {
          console.log('\n🎯 点击事件触发断点!');
          console.log(`   位置: ${event.url} 第 ${event.lineNumber} 行`);

          if (event.formattedPosition) {
            console.log(`   格式化代码位置: 第 ${event.formattedPosition.formattedLine} 行`);
          }

          console.log(`   调用栈:`);

          if (event.callFrames && event.callFrames.length > 0) {
            event.callFrames.forEach((frame, index) => {
              const functionName = frame.functionName || '(匿名函数)';
              let locationInfo = 'unknown';
              
              if (frame.url && frame.url !== 'unknown') {
                const urlParts = frame.url.split('/');
                const fileName = urlParts[urlParts.length - 1] || frame.url;
                const lineNum = frame.lineNumber !== undefined && !isNaN(frame.lineNumber) 
                  ? parseInt(frame.lineNumber) + 1 
                  : '?';
                const colNum = frame.columnNumber !== undefined && !isNaN(frame.columnNumber) 
                  ? parseInt(frame.columnNumber) + 1 
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

          if (this._rl) {
            this._rl.prompt();
          }
        };

        this.debugger.on('breakpointHit', this._clickListener);
      }

      if (!this._resumedListener) {
        this._resumedListener = () => {
          console.log('\n▶️  程序已恢复执行，等待下次点击...');
          if (this._rl) {
            this._rl.prompt();
          }
        };

        this.debugger.on('resumed', this._resumedListener);
      }

      console.log('\n💡 点击页面上的任何元素都会触发断点');
      console.log('💡 断点触发后可以使用以下命令:');
      console.log('   code - 查看当前代码上下文');
      console.log('   var - 查看当前作用域变量');
      console.log('   continue (c) - 继续执行');
      console.log('   next (n) - 单步跳过');
      console.log('   step (s) - 步入函数');
      console.log('   out (o) - 步出函数');
      console.log('   eval <expr> - 执行表达式');
      console.log('   quit (q) - 退出调试');
      console.log('   stop - 停止点击监听');

      if (this._rl) {
        this._rl.prompt();
      }
    } catch (error) {
      console.error('启动点击监听失败:', error.message);
      throw error;
    }
  }

  /**
   * 停止点击事件监听
   * @private
   */
  async _stopClickMonitoring() {
    try {
      await this.debugger.disableClickBreakpoint();
      console.log('✅ 点击事件监听已停止');
      this._cleanup();
    } catch (error) {
      console.error('停止点击监听失败:', error.message);
      throw error;
    }
  }

  /**
   * 设置readline处理器
   * @private
   */
  _setupReadlineHandlers() {
    this._rl.on('line', async (line) => {
      line = line.trim();

      try {
        const parts = line.split(/\s+/);
        const command = parts[0].toLowerCase();

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
        } else if (command === 'var') {
          try {
            console.log('🔍 正在获取当前作用域变量...');
            const variables = await this.debugger.getAllScopeVariables(0, 3);
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
            const contextLines = parts.length > 1 ? parseInt(parts[1], 10) : 30;
            const frameIndex = parts.length > 2 ? parseInt(parts[2], 10) : 0;
            
            console.log(`🔍 正在获取当前断点位置的代码上下文...`);
            const codeContext = await this.debugger.getCurrentCodeContext(contextLines, frameIndex, true);
            
            console.log(`\n📄 代码上下文 (${codeContext.url})`);
            console.log(`📌 断点位置: 第 ${codeContext.lineNumber} 行`);
            if (codeContext.columnNumber) {
              console.log(`📌 断点列号: 第 ${codeContext.columnNumber} 列`);
            }
            if (codeContext.formatted) {
              console.log(`✨ 代码已格式化`);
            }
            console.log('='.repeat(80));
            
            codeContext.contextLines.forEach(lineInfo => {
              const lineNumber = lineInfo.line.toString().padStart(4, ' ');
              const marker = lineInfo.isCurrent ? '→' : ' ';
              
              if (lineInfo.isCurrent && lineInfo.columnNumber !== undefined) {
                const content = lineInfo.content;
                const column = lineInfo.columnNumber;
                const safeColumn = Math.min(Math.max(0, column), content.length);
                const markedContent = content.slice(0, safeColumn) + '[我是标记]' + content.slice(safeColumn);
                console.log(`${marker} ${lineNumber} | ${markedContent}`);
                
                if (codeContext.totalLines === 1) {
                  const indent = `    | `.length;
                  const arrowLine = ' '.repeat(indent + safeColumn) + '↑';
                  console.log(arrowLine);
                }
              } else {
                console.log(`${marker} ${lineNumber} | ${lineInfo.content}`);
              }
            });
            
            console.log('='.repeat(80));
            console.log(`📊 共显示 ${codeContext.contextLines.length} 行，文件总计 ${codeContext.totalLines} 行`);
          } catch (error) {
            console.error(`❌ 获取代码上下文失败: ${error.message}`);
          }
          this._rl.prompt();
        } else if (command === 'stop') {
          await this._stopClickMonitoring();
        } else if (command === 'quit' || command === 'q') {
          console.log('👋 退出调试...');
          this._cleanup();
        } else if (command === 'help' || command === 'h' || command === '?') {
          console.log('\n🔧 可用命令:');
          console.log('  continue (c): 继续执行');
          console.log('  next (n): 单步跳过');
          console.log('  step (s): 单步进入');
          console.log('  out (o): 单步退出');
          console.log('  var: 导出当前作用域所有变量到文件');
          console.log('  code [lines] [frame]: 查看当前断点位置的代码上下文');
          console.log('  eval <expression>: 执行表达式');
          console.log('  stop: 停止点击监听');
          console.log('  quit (q): 退出调试');
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

    process.on('SIGINT', () => {
      console.log('\n👋 接收到中断信号，退出调试...');
      this._cleanup();
    });

    this._rl.on('close', () => {
      this._cleanup();
    });
  }

  /**
   * 清理资源
   * @private
   */
  _cleanup() {
    if (this._clickListener) {
      this.debugger.off('breakpointHit', this._clickListener);
      this._clickListener = null;
    }

    if (this._resumedListener) {
      this.debugger.off('resumed', this._resumedListener);
      this._resumedListener = null;
    }

    if (this._rl) {
      this._rl.close();
      this._rl = null;
    }

    process.exit(0);
  }

  /**
   * 格式化变量显示
   * @private
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

  /**
   * 初始化命令
   * @returns {Promise<void>}
   */
  async initialize() {
    try {
      await this.debugger.initialize();
      console.log('点击监听命令模块初始化成功');
    } catch (error) {
      console.error('点击监听命令模块初始化失败:', error.message);
      throw error;
    }
  }
}

module.exports = ClickCommand;
