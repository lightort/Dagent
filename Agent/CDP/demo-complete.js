const FileViewer = require('./src/modules/file-viewer');

// 创建测试用的mock connectionManager
const mockConnectionManager = {
  getFileContent: async () => "",
  sendMessage: () => {},
  logError: () => {}
};

const fileViewer = new FileViewer(mockConnectionManager);

console.log("=== 基于AST的代码格式化与位置映射演示 ===\n");

// 测试用例1：压缩的JavaScript代码
const testCase1 = {
  name: "压缩JavaScript代码",
  code: `function add(a,b){return a+b;}const result=add(1,2);console.log(result);`,
  language: "javascript"
};

// 测试用例2：正常格式的JavaScript代码
const testCase2 = {
  name: "正常格式JavaScript代码",
  code: `function add(a, b) {
  return a + b;
}

const result = add(1, 2);
console.log(result);`,
  language: "javascript"
};

// 测试用例3：CSS代码
const testCase3 = {
  name: "CSS代码",
  code: `body{margin:0;padding:0;font-family:Arial,sans-serif;}.container{max-width:1200px;margin:0 auto;padding:20px;}`,
  language: "css"
};

// 测试用例4：HTML代码
const testCase4 = {
  name: "HTML代码",
  code: `<html><head><title>Test</title></head><body><div class="container"><h1>Hello</h1><p>World</p></div></body></html>`,
  language: "html"
};

// 运行所有测试用例
const testCases = [testCase1, testCase2, testCase3, testCase4];

async function runAllTests() {
  for (const testCase of testCases) {
    console.log(`--- ${testCase.name} ---`);
    console.log("原始代码:");
    console.log(testCase.code);
    
    try {
      let result;
      if (testCase.language === "javascript") {
        // 使用AST格式化
        result = fileViewer.formatWithAST(testCase.code);
      } else {
        // 使用Prettier格式化
        result = await fileViewer.formatContent(testCase.code, "test." + testCase.language);
      }
      
      console.log("\n格式化后:");
      console.log(result.content);
      
      console.log("\n位置映射:");
      if (result.map) {
        const mappingEntries = Object.entries(result.map);
        mappingEntries.forEach(([formattedLine, originalPos]) => {
          console.log(`  格式化行 ${formattedLine} → 原始行 ${originalPos.originalLine}:${originalPos.originalColumn}`);
        });
      }
      
      console.log("✓ 格式化成功\n");
    } catch (error) {
      console.log("✗ 格式化失败:", error.message);
    }
  }
}

runAllTests();
