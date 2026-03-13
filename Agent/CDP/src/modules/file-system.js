/**
 * 文件系统模块
 * 通过CDP获取页面资源信息，实现目录查看功能
 */

class FileSystem {
  constructor(connectionManager) {
    this.connectionManager = connectionManager;
  }

  /**
   * 获取页面所有资源
   * @returns {Promise<Array>} 资源列表
   */
  async getResources() {
    try {
      // 确保已连接
      const client = await this.connectionManager.connect();
      
      // 确保Network域已启用
      if (!client.Network) {
        await this.connectionManager.enableDomains(['Network']);
      }
      
      // 另外，我们也可以通过执行JavaScript来获取页面中加载的脚本
      const { result } = await client.Runtime.evaluate({
        expression: '(function() {\n' +
          'const scripts = [];\n' +
          '// 获取当前页面URL\n' +
          'scripts.push({\n' +
          '  url: window.location.href,\n' +
          '  type: "document",\n' +
          '  inline: false\n' +
          '});\n' +
          '\n' +
          '// 获取所有脚本标签\n' +
          'const scriptElements = document.querySelectorAll("script[src]");\n' +
          'scriptElements.forEach(script => {\n' +
          '  scripts.push({\n' +
          '    url: script.src,\n' +
          '    type: "script",\n' +
          '    inline: false\n' +
          '  });\n' +
          '});\n' +
          '\n' +
          '// 获取内联脚本\n' +
          'const inlineScripts = document.querySelectorAll("script:not([src])");\n' +
          'inlineScripts.forEach((script, index) => {\n' +
          '  scripts.push({\n' +
          '    url: "inline-script-" + index,\n' +
          '    type: "script",\n' +
          '    inline: true\n' +
          '  });\n' +
          '});\n' +
          '\n' +
          '// 获取所有样式表\n' +
          'const styleSheets = Array.from(document.styleSheets);\n' +
          'styleSheets.forEach((sheet, index) => {\n' +
          '  if (sheet.href) {\n' +
          '    scripts.push({\n' +
          '      url: sheet.href,\n' +
          '      type: "stylesheet",\n' +
          '      inline: false\n' +
          '    });\n' +
          '  } else {\n' +
          '    scripts.push({\n' +
          '      url: "inline-stylesheet-" + index,\n' +
          '      type: "stylesheet",\n' +
          '      inline: true\n' +
          '    });\n' +
          '  }\n' +
          '});\n' +
          '\n' +
          '// 获取所有图片\n' +
          'const images = document.querySelectorAll("img");\n' +
          'images.forEach((img, index) => {\n' +
          '  if (img.src) {\n' +
          '    scripts.push({\n' +
          '      url: img.src,\n' +
          '      type: "image",\n' +
          '      inline: false\n' +
          '    });\n' +
          '  }\n' +
          '});\n' +
          '\n' +
          '// 获取所有链接\n' +
          'const links = document.querySelectorAll("link[href]");\n' +
          'links.forEach(link => {\n' +
          '  scripts.push({\n' +
          '    url: link.href,\n' +
          '    type: link.rel || "link",\n' +
          '    inline: false\n' +
          '  });\n' +
          '});\n' +
          '\n' +
          'return scripts;\n' +
          '})()',
        awaitPromise: true,
        returnByValue: true
      });
      
      if (result.value) {
        const jsResources = result.value; // 不需要JSON.parse，因为returnByValue设为了true
        return jsResources;
      } else {
        return [];
      }
    } catch (error) {
      console.error('获取资源列表失败:', error.message);
      
      // 返回一个基本的页面信息作为后备
      return [{
        url: 'fallback-document',
        type: 'document',
        inline: false,
        error: error.message
      }];
    }
  }

  /**
   * 按类型获取资源
   * @param {string} type - 资源类型 (script, stylesheet, image等)
   * @returns {Promise<Array>} 指定类型的资源列表
   */
  async getResourcesByType(type) {
    try {
      const resources = await this.getResources();
      
      if (type === 'script') {
        return resources.filter(resource => 
          resource.type.includes('javascript') || 
          resource.type === 'script'
        );
      } else if (type === 'stylesheet') {
        return resources.filter(resource => 
          resource.type.includes('css') || 
          resource.type === 'stylesheet'
        );
      } else if (type === 'image') {
        return resources.filter(resource => 
          resource.type.includes('image')
        );
      } else {
        return resources.filter(resource => resource.type === type);
      }
    } catch (error) {
      console.error(`获取${type}类型资源失败:`, error.message);
      throw error;
    }
  }

  /**
   * 获取页面脚本资源
   * @returns {Promise<Array>} 脚本资源列表
   */
  async getScripts() {
    return this.getResourcesByType('script');
  }

  /**
   * 获取调试器脚本列表
   * 通过Debugger域获取所有可调试的脚本
   * @returns {Promise<Array>} 调试器脚本列表
   */
  async getDebuggerScripts() {
    try {
      const client = await this.connectionManager.connect();
      
      // 确保Debugger域已启用
      if (!client.Debugger) {
        await this.connectionManager.enableDomains(['Debugger']);
      }
      
      // 正确获取所有脚本
      const result = await client.Debugger.getScriptSources();
      return result.scripts || [];
    } catch (error) {
      // 如果直接调用失败，尝试执行JavaScript来获取脚本信息
      try {
        const client = await this.connectionManager.connect();
        const { result } = await client.Runtime.evaluate({
          expression: '(function() {\n' +
              'const scripts = [];\n' +
              '// 通过performance API获取资源信息\n' +
              'if (performance && performance.getEntriesByType) {\n' +
              '  const entries = performance.getEntriesByType("resource");\n' +
              '  entries.forEach(entry => {\n' +
              '    if (entry.initiatorType === "script") {\n' +
              '      scripts.push({\n' +
              '        url: entry.name,\n' +
              '        type: "script"\n' +
              '      });\n' +
              '    }\n' +
              '  });\n' +
              '}\n' +
              'return scripts;\n' +
              '})()',
          awaitPromise: true
        });
        
        return result.value ? JSON.parse(result.value) : [];
      } catch (jsError) {
        console.error('获取调试器脚本失败:', error.message, jsError.message);
        return [];
      }
    }
  }

  /**
   * 列出资源目录结构
   * 将URL解析为目录结构
   * @returns {Promise<Object>} 目录结构对象
   */
  async listDirectoryStructure() {
    try {
      const resources = await this.getResources();
      const directoryStructure = {};
      
      // 解析URL并构建目录结构
      resources.forEach(resource => {
        try {
          const url = new URL(resource.url);
          const pathParts = url.pathname.split('/').filter(part => part);
          
          let currentLevel = directoryStructure;
          
          // 构建目录路径
          for (let i = 0; i < pathParts.length - 1; i++) {
            const part = pathParts[i];
            if (!currentLevel[part]) {
              currentLevel[part] = { type: 'directory', children: {} };
            }
            currentLevel = currentLevel[part].children;
          }
          
          // 添加文件
          if (pathParts.length > 0) {
            const fileName = pathParts[pathParts.length - 1];
            currentLevel[fileName] = {
              type: 'file',
              url: resource.url,
              mimeType: resource.type
            };
          }
        } catch (e) {
          // 忽略无效的URL
          console.warn(`无效的URL: ${resource.url}`, e.message);
        }
      });
      
      return directoryStructure;
    } catch (error) {
      console.error('构建目录结构失败:', error.message);
      throw error;
    }
  }

  /**
   * 格式化显示目录结构
   * @param {Object} structure - 目录结构对象
   * @param {string} indent - 缩进字符串
   * @returns {string} 格式化的目录结构字符串
   */
  formatDirectoryStructure(structure, indent = '') {
    let result = '';
    
    for (const [key, item] of Object.entries(structure)) {
      if (item.type === 'directory') {
        result += `${indent}📁 ${key}/\n`;
        result += this.formatDirectoryStructure(item.children, indent + '  ');
      } else {
        result += `${indent}📄 ${key} (${item.mimeType || 'unknown'})\n`;
      }
    }
    
    return result;
  }
}

module.exports = FileSystem;