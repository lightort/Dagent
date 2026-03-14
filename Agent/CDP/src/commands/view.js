/**
 * 文件查看命令
 * 用于查看指定文件的代码内容
 */

class ViewCommand {
  /**
   * 构造函数
   * @param {Object} fileViewer - 文件查看器模块实例
   */
  constructor(fileViewer) {
    this.fileViewer = fileViewer;
  }
  
  /**
   * 注册命令
   * @param {Object} program - Commander实例
   */
  register(program) {
    program
      .command('view <url>')
      .description('查看指定文件的代码内容')
      .option('-l, --lines <number>', '查看前N行代码', parseInt)
      .option('-s, --start <line>', '开始行号', parseInt, 1)
      .option('-e, --end <line>', '结束行号', parseInt)
      .option('-r, --range <range>', '行范围，格式为"开始行-结束行"')
      .option('-t, --type <type>', '文件类型 (script, stylesheet)')
      .option('-g, --grep <term>', '搜索关键词')
      .option('-b, --breakpoints', '显示断点位置和虚拟行号，或使用虚拟行号来指定行范围')
      .action(async (url, options) => {
        try {
          // 处理range参数
          let startLine = options.start || 1; // 默认值1
          let endLine = options.end;
          
          if (options.range) {
            const rangeParts = options.range.split('-');
            if (rangeParts.length === 2) {
              startLine = parseInt(rangeParts[0]) || 1; // 确保是有效数字
              endLine = parseInt(rangeParts[1]) || null; // 确保是有效数字或null
              if (isNaN(startLine)) {
                throw new Error('无效的行范围格式，请使用"开始行-结束行"格式');
              }
            } else {
              throw new Error('无效的行范围格式，请使用"开始行-结束行"格式');
            }
          } else {
            // 确保startLine始终是有效数字
            startLine = parseInt(startLine) || 1;
          }
          
          if (options.grep) {
            // 搜索文件内容
            console.log(`在文件中搜索: ${options.grep}`);
            const matches = await this.fileViewer.searchInFile(url, options.grep);
            
            if (matches.length > 0) {
              console.log(`找到 ${matches.length} 个匹配:`);
              matches.forEach(match => {
                console.log(`${match.lineNumber.toString().padStart(4)}| ${match.line}`);
              });
            } else {
              console.log('未找到匹配内容');
            }
          } else if (options.lines) {
            // 查看前N行
            console.log(`文件 ${url} 的前 ${options.lines} 行:`);
            const content = await this.fileViewer.getFirstNLines(url, options.lines, false, options.breakpoints);
            console.log(content);
          } else {
            if (options.breakpoints) {
              // 显示断点位置信息
              console.log(`=== 断点位置和虚拟行号信息 (${url}) ===`);
              console.log(`使用以下命令设置断点: cdp breakpoint set ${url} <虚拟行号>`);
              console.log('');
            }
            
            // 查看指定范围的行
            console.log(`文件 ${url} 的内容:`);
            // 当使用断点选项时，将format参数设置为true，以便创建基于断点位置的虚拟行结构
            const content = await this.fileViewer.getFileContent(url, startLine, endLine, options.type, options.breakpoints, options.breakpoints);
            console.log(content);
            console.log(`\n显示行范围: ${startLine}${endLine ? ' - ' + endLine : ' 到文件末尾'}`);
          }
        } catch (error) {
          console.error('查看文件内容失败:', error.message);
          process.exit(1);
        }
        
        // 命令完成后退出程序
        process.exit(0);
      });
  }
}

module.exports = ViewCommand;