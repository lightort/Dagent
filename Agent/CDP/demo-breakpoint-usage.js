const FileViewer = require('./src/modules/file-viewer');

// 模拟ConnectionManager
class MockConnectionManager {
  connect() {
    return Promise.resolve({
      Runtime: {
        evaluate: () => Promise.resolve({ result: { value: '' } })
      }
    });
  }
}

// 演示完整的断点使用流程
async function demoBreakpointUsage() {
  console.log('=== CDP 断点功能使用演示 ===\n');
  
  // 创建FileViewer实例
  const connectionManager = new MockConnectionManager();
  const fileViewer = new FileViewer(connectionManager);
  
  const exampleUrl = 'http://example.com/app.js';
  
  // 示例JavaScript代码
  const exampleCode = 'function calculateFactorial(n) { let result = 1; for (let i = 2; i <= n; i++) { result *= i; } return result; } function main() { const number = 5; const factorial = calculateFactorial(number); console.log("The factorial of " + number + " is " + factorial); if (factorial > 10) { console.log("Factorial is greater than 10"); } else { console.log("Factorial is less than or equal to 10"); } } main();';
  
  // 步骤1: 查看文件内容，了解代码结构
  console.log('步骤1: 查看文件基本内容');
  console.log('-----------------------------------');
  const basicContent = await fileViewer.getLinesFromContent(exampleCode, 1, null, false);
  console.log(basicContent);
  console.log('\n');
  
  // 步骤2: 使用--breakpoints选项查看断点位置和虚拟行号
  console.log('步骤2: 查看断点位置和虚拟行号 (对应命令: cdp view -b http://example.com/app.js)');
  console.log('-----------------------------------');
  const breakpointContent = await fileViewer.getLinesFromContent(exampleCode, 1, null, true);
  console.log(breakpointContent);
  console.log('\n');
  
  // 步骤3: 展示如何设置断点
  console.log('步骤3: 设置断点示例');
  console.log('-----------------------------------');
  console.log('根据上面的虚拟行号，您可以选择在以下位置设置断点:');
  console.log('1. 在calculateFactorial函数开始处: cdp breakpoint set http://example.com/app.js 1');
  console.log('2. 在for循环处: cdp breakpoint set http://example.com/app.js 2');
  console.log('3. 在return语句处: cdp breakpoint set http://example.com/app.js 3');
  console.log('4. 在main函数开始处: cdp breakpoint set http://example.com/app.js 4');
  console.log('5. 在条件判断处: cdp breakpoint set http://example.com/app.js 7');
  console.log('\n');
  
  // 步骤4: 展示如何查看已设置的断点
  console.log('步骤4: 查看已设置的断点');
  console.log('-----------------------------------');
  console.log('命令: cdp breakpoint list');
  console.log('这将显示所有已设置的断点及其状态');
  console.log('\n');
  
  // 步骤5: 展示如何移除断点
  console.log('步骤5: 移除断点');
  console.log('-----------------------------------');
  console.log('命令示例: cdp breakpoint remove http://example.com/app.js 1');
  console.log('或: cdp breakpoint clear  # 清除所有断点');
  console.log('\n');
  
  // 步骤6: 展示如何使用条件断点
  console.log('步骤6: 使用条件断点');
  console.log('-----------------------------------');
  console.log('命令示例: cdp breakpoint set http://example.com/app.js 2 --condition "i === 3"');
  console.log('这将在i等于3时触发断点');
  console.log('\n');
  
  console.log('=== 演示结束 ===');
  console.log('现在您可以使用这些命令来管理您的断点了！');
}

demoBreakpointUsage();