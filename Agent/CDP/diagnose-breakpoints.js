#!/usr/bin/env node

/**
 * 断点诊断脚本
 * 检查断点存储、恢复和识别问题
 */

const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');

console.log('🔍 断点诊断工具');
console.log('===================\n');

// 检查1: 检查断点存储文件
console.log('📁 检查1: 断点存储文件状态');
console.log('----------------------------');

const storagePath = path.join(process.cwd(), '.cdp-breakpoints.json');
console.log(`存储文件路径: ${storagePath}`);

if (fs.existsSync(storagePath)) {
  try {
    const content = fs.readFileSync(storagePath, 'utf8');
    const breakpoints = JSON.parse(content);
    
    console.log(`✅ 存储文件存在`);
    console.log(`📊 断点数量: ${breakpoints.length}`);
    
    if (breakpoints.length > 0) {
      console.log('\n📋 存储的断点详情:');
      breakpoints.forEach((bp, index) => {
        console.log(`  ${index + 1}. ID: ${bp.id}`);
        console.log(`     URL: ${bp.url}`);
        console.log(`     行号: ${bp.lineNumber}`);
        console.log(`     类型: ${bp.type}`);
        console.log(`     活跃: ${bp.active}`);
        if (bp.options) {
          console.log(`     选项: ${JSON.stringify(bp.options)}`);
        }
        console.log('');
      });
    } else {
      console.log('⚠️  存储文件中没有断点');
    }
  } catch (error) {
    console.log(`❌ 读取断点存储文件失败: ${error.message}`);
  }
} else {
  console.log('⚠️  断点存储文件不存在');
}

console.log('\n' + '-'.repeat(50) + '\n');

// 检查2: 测试断点列表命令
console.log('🧪 检查2: 测试断点列表命令');
console.log('----------------------------');

function runCommand(command) {
  return new Promise((resolve) => {
    exec(command, { cwd: process.cwd(), shell: 'powershell' }, (error, stdout, stderr) => {
      resolve({
        success: !error,
        stdout: stdout || '',
        stderr: stderr || '',
        error: error ? error.message : null
      });
    });
  });
}

async function testBreakpointCommands() {
  try {
    console.log('🔧 执行: node bin/cli.js breakpoint list');
    const result = await runCommand('node bin/cli.js breakpoint list');
    
    if (result.success) {
      console.log('✅ 命令执行成功');
      console.log('📤 输出内容:');
      console.log(result.stdout);
      
      if (result.stdout.includes('demo-script.js')) {
        console.log('✅ 在断点列表中找到了 demo-script.js');
      } else {
        console.log('⚠️  断点列表中没有找到 demo-script.js');
      }
    } else {
      console.log(`❌ 命令执行失败: ${result.error}`);
      if (result.stderr) {
        console.log('📤 错误输出:');
        console.log(result.stderr);
      }
    }
  } catch (error) {
    console.log(`❌ 测试过程中发生错误: ${error.message}`);
  }
}

testBreakpointCommands().then(() => {
  console.log('\n' + '-'.repeat(50) + '\n');
  
  // 检查3: 测试断点设置
  console.log('🧪 检查3: 测试断点重新设置');
  console.log('----------------------------');
  
  return testBreakpointCommands();
}).then(() => {
  console.log('\n📊 诊断总结:');
  console.log('============');
  console.log('1. 检查断点存储文件状态');
  console.log('2. 测试断点列表命令');
  console.log('3. 建议: 如果断点识别有问题，尝试删除 .cdp-breakpoints.json 文件后重新设置断点');
  console.log('\n💡 建议操作:');
  console.log('- 如果问题持续，可以手动删除 .cdp-breakpoints.json 文件');
  console.log('- 然后重新设置断点测试');
  console.log('- 检查是否在正确的目录下运行命令');
  
  process.exit(0);
}).catch(error => {
  console.error('❌ 诊断过程中发生错误:', error.message);
  process.exit(1);
});