/**
 * 网络请求监控命令
 * 用于查看网页接收到的网络请求和调用栈信息
 */

class NetworkCommand {
  /**
   * 构造函数
   * @param {Object} debuggerModule - 调试器模块实例
   */
  constructor(debuggerModule) {
    this.debugger = debuggerModule;
    this.networkRequests = new Map(); // 存储网络请求信息
  }
  
  /**
   * 注册命令
   * @param {Object} program - Commander实例
   */
  register(program) {
    // 网络命令组
    const network = program.command('network')
      .alias('net')
      .description('网络请求监控命令');

    // 列出所有网络请求
    network.command('list')
      .description('查看所有接收到的网络请求')
      .option('-l, --limit <number>', '限制显示的请求数量', parseInt)
      .option('-f, --filter <type>', '按请求类型过滤 (xhr, fetch, script, image, etc.)')
      .option('-w, --watch', '持续监控网络请求')
      .action(async (options) => {
        try {
          // 确保debugger已初始化，包括Network事件监听器注册
          if (!this.debugger.client || !this.debugger._enabledDomains.has('Network')) {
            await this.debugger.initialize();
          }
          
          if (options.watch) {
            // 持续监控模式
            console.log('🔍 开始持续监控网络请求...');
            console.log('按 Ctrl+C 停止监控');
            
            // 显示初始请求
            let requests = await this.debugger.getAllNetworkRequests();
            if (requests.length > 0) {
              this._displayRequests(requests, options);
            } else {
              console.log('当前没有接收到网络请求，将显示新的请求...');
            }
            
            // 监听新的网络请求事件
            this.debugger.on('networkRequestReceived', (request) => {
              console.log('\n📥 新的网络请求:');
              console.log('--------------------------------------------------');
              console.log('ID'.padEnd(15) + '类型'.padEnd(10) + '状态'.padEnd(10) + 'URL');
              console.log('--------------------------------------------------');
              console.log(
                request.requestId.padEnd(15) + 
                request.type.padEnd(10) + 
                request.status.padEnd(10) + 
                request.url
              );
              console.log('--------------------------------------------------');
            });
            
            // 保持程序运行
            process.stdin.resume();
          } else {
            // 一次性查看模式
            const requests = await this.debugger.getAllNetworkRequests();
            
            if (requests.length === 0) {
              console.log('当前没有接收到网络请求');
              process.exit(0);
            }
            
            this._displayRequests(requests, options);
            process.exit(0);
          }
        } catch (error) {
          console.error('查看网络请求失败:', error.message);
          process.exit(1);
        }
      });

    // 查看单个请求的调用栈
    network.command('trace <requestId>')
      .description('查看指定网络请求的调用栈信息')
      .action(async (requestId) => {
        try {
          // 确保debugger已初始化，包括Network事件监听器注册
          if (!this.debugger.client || !this.debugger._enabledDomains.has('Network')) {
            await this.debugger.initialize();
          }
          
          const requestDetails = await this.debugger.getNetworkRequestDetails(requestId);
          
          if (!requestDetails) {
            console.error(`未找到ID为 ${requestId} 的网络请求`);
            process.exit(1);
          }

          console.log('\n🔍 网络请求详情:');
          console.log('--------------------------------------------------');
          console.log(`ID: ${requestDetails.requestId}`);
          console.log(`URL: ${requestDetails.url}`);
          console.log(`类型: ${requestDetails.type}`);
          console.log(`状态: ${requestDetails.status}`);
          console.log(`方法: ${requestDetails.method}`);
          console.log(`开始时间: ${new Date(requestDetails.timestamp * 1000).toLocaleString()}`);
          
          if (requestDetails.callStack) {
            console.log('\n📋 调用栈:');
            console.log('--------------------------------------------------');

            // 解析调用栈中的scriptId为实际URL
            const resolvedFrames = await this.debugger.resolveCallStackUrls(requestDetails.callStack);

            resolvedFrames.forEach((frame, index) => {
              const functionName = frame.functionName || '(匿名函数)';
              let url = frame.url;

              // 如果URL是script:xxx格式，尝试显示更友好的信息
              if (url && url.startsWith('script:') && frame.scriptId) {
                url = frame.url; // 保持原样，但已经通过resolveCallStackUrls解析过了
              }

              const location = url ? `${url}:${(frame.lineNumber || 0) + 1}:${(frame.columnNumber || 0) + 1}` : 'unknown';
              console.log(`  ${index}. ${functionName} (${location})`);
            });
            console.log('--------------------------------------------------');
          } else {
            console.log('\n⚠️  未找到该请求的调用栈信息');
          }
          
        } catch (error) {
          console.error('查看请求调用栈失败:', error.message);
        }
        
        process.exit(0);
      });
  }
  
  /**
   * 显示网络请求
   * @param {Array} requests - 网络请求数组
   * @param {Object} options - 显示选项
   * @private
   */
  _displayRequests(requests, options) {
    let filteredRequests = requests;
    
    // 应用过滤条件
    if (options.filter) {
      filteredRequests = requests.filter(req => 
        req.type.toLowerCase() === options.filter.toLowerCase()
      );
    }

    // 应用数量限制
    if (options.limit) {
      filteredRequests = filteredRequests.slice(0, options.limit);
    }

    console.log('\n📡 接收到的网络请求:');
    console.log('--------------------------------------------------');
    console.log('ID'.padEnd(15) + '类型'.padEnd(10) + '状态'.padEnd(10) + 'URL');
    console.log('--------------------------------------------------');
    
    filteredRequests.forEach(request => {
      console.log(
        request.requestId.padEnd(15) + 
        request.type.padEnd(10) + 
        request.status.padEnd(10) + 
        request.url
      );
    });
    
    console.log('--------------------------------------------------');
    console.log(`共 ${filteredRequests.length} 个请求${options.limit ? ` (显示前${options.limit}个)` : ''}`);
  }
}

module.exports = NetworkCommand;