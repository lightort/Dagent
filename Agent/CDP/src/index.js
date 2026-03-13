#!/usr/bin/env node

/**
 * CDP 命令行工具主入口
 * 提供通过Chrome DevTools Protocol操作浏览器控制台的功能
 */

const { program } = require('commander');
const ConnectionManager = require('./modules/connection-manager');
const FileSystem = require('./modules/file-system');
const FileViewer = require('./modules/file-viewer');
const Debugger = require('./modules/debugger');

// 初始化连接管理器
const connectionManager = new ConnectionManager();
const fileSystem = new FileSystem(connectionManager);
const fileViewer = new FileViewer(connectionManager);
const debuggerModule = new Debugger(connectionManager);

// 将fileViewer传递给debuggerModule，以便访问位置映射信息
debuggerModule.setFileViewer(fileViewer);

// 初始化命令
const dirCommand = new (require('./commands/dir'))(fileSystem);
const viewCommand = new (require('./commands/view'))(fileViewer);
const breakpointCommand = new (require('./commands/breakpoint'))(debuggerModule);
const networkCommand = new (require('./commands/network'))(debuggerModule);

// 设置命令行参数
program
  .version('1.0.0')
  .description('CDP 命令行工具 - 通过 Chrome DevTools Protocol 查看网页文件和调试功能')
  .option('-h, --host <host>', 'Chrome调试主机', 'localhost')
  .option('-p, --port <port>', 'Chrome调试端口', '9222')
  .option('-t, --target <target>', '目标页面的 URL 或标题');

// 处理全局选项
program.on('option:host', (host) => {
  connectionManager.setOptions({ host });
});

program.on('option:port', (port) => {
  connectionManager.setOptions({ port });
});

program.on('option:target', (target) => {
  connectionManager.setOptions({ target });
});

// 注册命令
dirCommand.register(program);
viewCommand.register(program);
breakpointCommand.register(program);
networkCommand.register(program);

// 添加帮助命令
program.command('help-all')
  .description('显示所有命令的详细帮助信息')
  .action(() => {
    console.log('CDP 命令行工具详细帮助:\n');
    program.help();
    console.log('\n' + breakpointCommand.getHelp?.() || '断点命令详细帮助信息');
  });

// 错误处理
program.on('command:*', () => {
  console.error('未知命令: %s\n请使用 --help 查看可用命令。', program.args.join(' '));
  process.exit(1);
});

// 执行命令
async function run() {
  try {
    // 初始化各模块
    await connectionManager.initialize?.();
    await breakpointCommand.initialize?.();
    
    // 执行命令
    program.parse(process.argv);

    // 如果没有提供命令，显示帮助信息
    if (!program.args.length) {
      program.help();
    }
  } catch (error) {
    console.error('初始化失败:', error.message);
    console.error('请确保 Chrome 已启动并开启了远程调试模式');
    console.error('启动 Chrome 命令示例: chrome --remote-debugging-port=9222');
    process.exit(1);
  }
}

// 启动应用
run();

// 导出主要类供其他模块使用
module.exports = {
  ConnectionManager,
  FileSystem,
  FileViewer,
  Debugger
};