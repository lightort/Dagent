/**
 * CDP 工具使用示例
 * 本文件提供了使用CDP命令行工具的常见场景示例
 */

/**
 * 使用流程示例
 * 
 * 注意：在运行这些命令之前，请确保：
 * 1. 已安装CDP工具: npm install -g .
 * 2. 已启动Chrome并开启远程调试: chrome --remote-debugging-port=9222
 * 3. 已在Chrome中打开demo-page.html页面
 */

/**
 * 示例1: 基本文件操作
 * 
 * # 列出页面中加载的所有资源
 * cdp dir
 * 
 * # 只列出JavaScript文件
 * cdp dir --scripts
 * 
 * # 查看特定文件内容
 * cdp view demo-page.html
 * 
 * # 查看文件前20行
 * cdp view demo-page.html --lines 20
 * 
 * # 查看文件的特定行范围
 * cdp view demo-page.html --range 50-70
 */

/**
 * 示例2: 断点调试工作流
 * 
 * # 1. 首先查看文件内容，找到需要设置断点的位置
 * cdp view demo-page.html
 * 
 * # 2. 在点击事件处理函数中设置断点（假设在第58行附近）
 * cdp break demo-page.html 58
 * 
 * # 3. 查看已设置的断点
 * cdp breakpoints
 * 
 * # 4. 在浏览器中点击"增加"按钮，程序会在断点处暂停
 * #    此时命令行会显示断点信息和调用栈
 * 
 * # 5. 计算表达式的值
 * cdp eval count
 * 
 * # 6. 单步执行
 * cdp step
 * 
 * # 7. 继续执行
 * cdp continue
 * 
 * # 8. 设置条件断点
 * cdp breakpoint conditional demo-page.html 63 "count > 10"
 */

/**
 * 示例3: DOM断点和监控
 * 
 * # 设置DOM断点监控元素属性变化
 * cdp breakpoint dom ".container" attribute-modified
 * 
 * # 设置DOM断点监控子树修改
 * cdp breakpoint dom "#toggleContent" subtree-modified
 * 
 * # 在浏览器中操作DOM，观察断点触发
 * 
 * # 移除DOM断点
 * cdp breakpoint remove dom-<nodeId>-subtree-modified  # 替换<nodeId>为实际的节点ID
 */

/**
 * 示例4: 高级调试技巧
 * 
 * # 忽略前5次断点触发
 * cdp breakpoint set demo-page.html 58 --ignore 5
 * 
 * # 在循环中调试（假设在一个循环中）
 * cdp eval "i"  # 查看循环变量
 * cdp eval "array[i]"  # 查看当前元素
 * 
 * # 清除所有断点
 * cdp breakpoint clear
 */

/**
 * 示例5: 多页面目标
 * 
 * # 指定目标页面
 * cdp dir --target "CDP工具演示页面"
 * 
 * # 使用不同的端口
 * cdp dir --port 9223
 */

/**
 * 实际使用建议
 * 
 * 1. 先使用dir命令了解页面加载了哪些资源
 * 2. 使用view命令查看关键文件的内容
 * 3. 根据需要设置断点，可以是普通断点、条件断点或DOM断点
 * 4. 在浏览器中操作，触发断点
 * 5. 使用调试命令（continue、next、step、out）控制执行流程
 * 6. 使用eval命令在断点处检查变量值和执行表达式
 */

/**
 * 常见问题解决
 * 
 * 1. 连接失败
 *    - 确保Chrome已启动并开启了远程调试模式
 *    - 检查端口号是否正确
 *    - 尝试使用--host和--port参数指定正确的地址
 * 
 * 2. 断点不触发
 *    - 确保行号正确
 *    - 检查文件路径或URL是否正确
 *    - 确认断点是否已启用
 * 
 * 3. 命令未找到
 *    - 确保已正确安装工具
 *    - 检查Node.js环境变量配置
 */

module.exports = {
  // 导出示例配置，可用于测试
  exampleConfig: {
    host: 'localhost',
    port: 9222,
    target: 'CDP工具演示页面'
  },
  
  // 列出常用命令
  getCommonCommands() {
    return [
      'cdp dir --scripts',
      'cdp view <file>',
      'cdp break <file> <line>',
      'cdp continue',
      'cdp eval "<expression>"'
    ];
  }
};