/**
 * CDP连接管理模块
 * 负责与Chrome浏览器建立和维护WebSocket连接
 */

const CDP = require('chrome-remote-interface');

class ConnectionManager {
  constructor() {
    this.client = null;
    this.target = null;
    this.options = {
      port: 9222,
      host: 'localhost'
    };
    // 事件监听器存储
    this._eventListeners = new Map();
  }

  /**
   * 设置连接选项
   * @param {Object} options - 连接选项
   * @param {string} options.port - Chrome调试端口
   * @param {string} options.host - Chrome调试主机
   */
  setOptions(options) {
    this.options = { ...this.options, ...options };
  }

  /**
   * 连接到Chrome浏览器
   * @returns {Promise<Object>} CDP客户端实例
   */
  async connect() {
    try {
      if (this.client) {
        return this.client;
      }

      console.log(`连接到Chrome浏览器: ${this.options.host}:${this.options.port}`);
      
      // 获取所有目标页面列表
      const allTargets = await this.getTargets();
      
      // 选择目标页面
      let targetToConnect = null;
      if (this.options.target) {
        // 查找匹配的目标（使用更宽松的匹配规则）
        targetToConnect = allTargets.find(t => 
          (t.url && t.url.includes(this.options.target)) || 
          (t.title && t.title.toLowerCase().includes(this.options.target.toLowerCase()))
        );
        
        if (targetToConnect) {
          this.client = await CDP({
            ...this.options,
            target: targetToConnect.id
          });
          this.target = targetToConnect.id;
        } else {
          console.warn(`未找到匹配 '${this.options.target}' 的页面，将连接到默认页面`);
          // 仍然尝试连接默认目标
          this.client = await CDP(this.options);
        }
      } else if (allTargets.length > 0) {
        // 没有指定target参数但有可用页面，自动连接到第一个页面
        targetToConnect = allTargets[0];
        this.client = await CDP({
          ...this.options,
          target: targetToConnect.id
        });
        this.target = targetToConnect.id;
      } else {
        // 没有可用页面，尝试连接默认目标
        this.client = await CDP(this.options);
      }
      
      console.log('已连接到Chrome浏览器');
      
      // 启用必要的域
      await this.enableDomains(['Page', 'Runtime', 'Debugger', 'Network']);
      
      return this.client;
    } catch (error) {
      console.error('连接Chrome浏览器失败:', error.message);
      console.error('请确保Chrome已使用以下命令启动:');
      console.error('chrome --remote-debugging-port=9222');
      console.error('如果Chrome中有多个标签页，请使用 -t 参数指定目标页面');
      throw error;
    }
  }

  /**
   * 启用CDP域
   * @param {string[]} domains - 要启用的域列表
   */
  async enableDomains(domains) {
    if (!this.client) {
      throw new Error('未连接到Chrome浏览器');
    }

    for (const domain of domains) {
      if (this.client[domain] && typeof this.client[domain].enable === 'function') {
        try {
          await this.client[domain].enable();
          
          // 为启用的域注册已有的事件监听器
          this._registerExistingListenersForDomain(domain);
        } catch (error) {
          console.warn(`启用${domain}域时出错:`, error.message);
        }
      }
    }
  }

  /**
   * 断开与Chrome浏览器的连接
   */
  async disconnect() {
    if (this.client) {
      try {
        await this.client.close();
        console.log('已断开与Chrome浏览器的连接');
      } catch (error) {
      console.error('断开连接时出错:', error.message);
    } finally {
      this.client = null;
      this.target = null;
      // 保留事件监听器，以便重新连接后可以恢复
    }
    }
  }

  /**
   * 获取CDP客户端实例
   * @returns {Object|null} CDP客户端实例或null
   */
  getClient() {
    return this.client;
  }

  /**
   * 检查是否已连接
   * @returns {boolean} 是否已连接
   */
  isConnected() {
    return !!this.client;
  }

  /**
   * 注册事件监听器
   * @param {string} eventName - 事件名称，格式为"Domain.event"
   * @param {Function} listener - 事件处理函数
   */
  on(eventName, listener) {
    // 解析域和事件名
    const [domain, event] = eventName.split('.');
    
    if (!domain || !event) {
      console.error('事件名称格式错误，应为"Domain.event"');
      return;
    }
    
    // 存储监听器
    if (!this._eventListeners.has(eventName)) {
      this._eventListeners.set(eventName, []);
    }
    this._eventListeners.get(eventName).push(listener);
    
    // 如果客户端已连接且域已启用，立即注册监听器
    if (this.client && this.client[domain]) {
      // CDP客户端库使用on方法注册事件监听器
      this.client[domain].on(event, listener);
    } else {
      // 客户端未连接或域未启用，延迟注册事件监听器
    }
  }
  
  /**
   * 移除事件监听器
   * @param {string} eventName - 事件名称
   * @param {Function} listener - 要移除的监听器（可选），如果不提供则移除所有该事件的监听器
   */
  off(eventName, listener) {
    if (!this._eventListeners.has(eventName)) {
      return;
    }
    
    // 解析域和事件名
    const [domain, event] = eventName.split('.');
    
    if (listener) {
      // 移除特定监听器
      const listeners = this._eventListeners.get(eventName);
      const index = listeners.indexOf(listener);
      if (index > -1) {
        listeners.splice(index, 1);
        
        // 如果客户端已连接，也需要从客户端移除
        if (this.client && this.client[domain] && this.client[domain][event]) {
          // 注意：CDP库可能不支持直接移除特定监听器
          // 这里简化处理，实际可能需要重新注册所有剩余监听器
        }
      }
      
      // 如果没有更多监听器，删除该事件的条目
      if (listeners.length === 0) {
        this._eventListeners.delete(eventName);
      }
    } else {
      // 移除所有监听器
      this._eventListeners.delete(eventName);
    }
  }
  
  /**
   * 为指定域注册现有的事件监听器
   * @private
   * @param {string} domain - 域名称
   */
  _registerExistingListenersForDomain(domain) {
    if (!this.client || !this.client[domain]) {
      return;
    }
    
    // 遍历所有事件监听器，查找与该域相关的
    for (const [eventName, listeners] of this._eventListeners.entries()) {
      const [eventDomain, event] = eventName.split('.');
      
      if (eventDomain === domain) {
        // 为每个监听器注册事件，使用on方法
        listeners.forEach(listener => {
          this.client[domain].on(event, listener);
        });
      }
    }
  }
  
  /**
   * 获取所有已加载的脚本信息
   * @returns {Promise<Array>} 脚本信息数组
   */
  async getScripts() {
    try {
      await this.connect();
      
      // 确保Debugger域已启用
      if (!this._enabledDomains || !this._enabledDomains.includes('Debugger')) {
        await this.execute('Debugger', 'enable');
        if (!this._enabledDomains) this._enabledDomains = [];
        this._enabledDomains.push('Debugger');
      }

      // 尝试使用 Debugger.getScriptSources 命令（推荐）
      console.log('尝试使用 Debugger.getScriptSources 获取脚本...');
      const result = await this.execute('Debugger', 'getScriptSources');
      
      let scripts = [];
      if (result && result.scriptSources) {
        console.log(`成功获取到 ${result.scriptSources.length} 个脚本源`);
        scripts = result.scriptSources.map(source => ({
          scriptId: source.scriptId,
          url: source.url || '',
          sourceMapURL: source.sourceMapURL || '',
          length: source.length || 0,
          startLine: source.startLine || 0,
          startColumn: source.startColumn || 0,
          endLine: source.endLine || 0,
          endColumn: source.endColumn || 0
        }));
        return scripts;
      } else if (result && result.scripts) {
        console.log(`成功获取到 ${result.scripts.length} 个脚本`);
        return result.scripts;
      }
    } catch (error) {
      console.log(`Debugger.getScriptSources 失败: ${error.message}`);
      
      // 如果 Debugger.getScriptSources 失败，尝试使用 Debugger.getScripts
      try {
        console.log('尝试使用 Debugger.getScripts 获取脚本...');
        const result = await this.execute('Debugger', 'getScripts');
        
        if (result && result.scripts) {
          console.log(`成功获取到 ${result.scripts.length} 个脚本`);
          return result.scripts;
        }
      } catch (error2) {
        console.error('获取脚本信息失败:', error2.message);
        
        // 尝试Debugger.enable后再重试一次
        try {
          console.log('尝试重新启用Debugger域...');
          await this.execute('Debugger', 'enable');
          
          console.log('再次尝试使用 Debugger.getScripts 获取脚本...');
          const result = await this.execute('Debugger', 'getScripts');
          
          if (result && result.scripts) {
            console.log(`成功获取到 ${result.scripts.length} 个脚本`);
            return result.scripts;
          }
        } catch (error3) {
          console.error('所有获取脚本的尝试都失败了:', error3.message);
        }
      }
    }
    
    return [];
  }
  
  /**
   * Find a matching script URL based on the provided filename or URL.
   * @param {string} filename - The filename or partial URL to find a match for.
   * @returns {Promise<string>} The matching script URL.
   */
  async findMatchingScriptUrl(filename) {
    try {
      // 确保连接到Chrome
      await this.connect();
      
      // 清理文件名，移除可能的前后空格和引号
      filename = filename.trim().replace(/^['`"](.*)['`"]$/, '$1');
      
      // 如果已经是完整URL，直接返回
      if (filename.startsWith('http://') || filename.startsWith('https://') || filename.startsWith('file://')) {
        console.log(`检测到完整URL: ${filename}`);
        
        // 尝试检查这个URL是否存在于已加载的脚本中
        try {
          const scripts = await this.getScripts();
          
          if (scripts.length > 0) {
            const matchingScript = scripts.find(script => script.url === filename);
            if (matchingScript) {
              console.log(`找到完全匹配的URL: ${filename}`);
              return filename;
            } else {
              console.log(`提供的完整URL ${filename} 未在已加载脚本中找到`);
              console.log(`可能的原因：脚本尚未加载或Debugger命令受限`);
              
              // 尝试部分匹配
              const partialMatch = scripts.find(script => script.url && script.url.includes(filename.split('?')[0]));
              if (partialMatch) {
                console.log(`找到部分匹配的URL: ${partialMatch.url}`);
                return partialMatch.url;
              }
            }
          } else {
            console.log(`无法获取已加载脚本列表，可能是Debugger域不支持`);
          }
        } catch (e) {
          console.debug('获取脚本列表失败:', e.message);
          // 如果获取脚本列表失败，尝试其他方法确认URL
        }
        
        // 尝试通过Runtime.evaluate检查页面中是否存在该脚本元素
        try {
          const scriptUrl = JSON.stringify(filename);
          const { result } = await this.execute('Runtime', 'evaluate', {
            expression: `document.querySelector('script[src=${scriptUrl}]') !== null`,
            returnByValue: true
          });
          
          if (result && result.value) {
            console.log(`确认页面中存在该脚本元素，将直接使用提供的URL`);
            return filename;
          } else {
            console.log(`页面中未找到该脚本元素，将尝试使用部分URL匹配`);
          }
        } catch (e) {
          console.debug('检查脚本元素失败:', e.message);
        }
        
        // 如果所有检查都失败，仍然返回提供的完整URL
        // 因为在某些受限环境中，即使无法验证，setBreakpointByUrl仍可能工作
        console.log(`将直接使用提供的完整URL进行断点设置`);
        return filename;
      }
      
      // 对于HTML文件的特殊处理
      if (filename.endsWith('.html') || filename.endsWith('.htm')) {
        // 尝试获取当前页面URL
        try {
          const { result } = await this.execute('Runtime', 'evaluate', {
            expression: 'window.location.href',
            returnByValue: true
          });
          
          if (result && result.value) {
            const currentUrl = result.value;
            // 检查当前页面是否匹配目标HTML文件
            if (currentUrl.includes(filename)) {
              console.log(`找到匹配的HTML页面: ${currentUrl}`);
              return currentUrl;
            }
          }
        } catch (e) {
          console.debug('获取当前页面URL失败:', e.message);
        }
      }
      
      // 获取已加载的脚本列表
      let scripts = [];
      try {
        scripts = await this.getScripts();
      } catch (e) {
        console.debug('获取脚本列表失败:', e.message);
      }
      
      console.log(`正在为 '${filename}' 查找匹配的脚本URL...`);
      console.log(`已加载脚本数量: ${scripts.length}`);
      
      // 如果有脚本，记录前5个脚本的URL用于调试
      if (scripts.length > 0) {
        console.log('部分已加载脚本URL:');
        scripts.slice(0, Math.min(5, scripts.length)).forEach((script, index) => {
          console.log(`[${index + 1}] ${script.url || '无URL'}`);
        });
        if (scripts.length > 5) {
          console.log(`... 还有 ${scripts.length - 5} 个脚本`);
        }
      }
      
      // 如果没有获取到脚本列表，尝试使用其他方法
      if (scripts.length === 0) {
        console.log('无法获取已加载脚本列表，尝试使用替代方法...');
        
        // 尝试获取当前页面URL并检查是否匹配
        try {
          const { result } = await this.execute('Runtime', 'evaluate', {
            expression: 'window.location.href',
            returnByValue: true
          });
          
          if (result && result.value) {
            const currentUrl = result.value;
            console.log(`当前页面URL: ${currentUrl}`);
            
            // 如果当前页面URL包含文件名，直接使用
            if (currentUrl.includes(filename)) {
              console.log(`当前页面URL包含目标文件名: ${filename} -> ${currentUrl}`);
              return currentUrl;
            }
          }
        } catch (e) {
          console.debug('获取当前页面URL失败:', e.message);
        }
        
        // 对于HTML文件的额外处理：尝试使用简单文件名作为URL
        if (filename.endsWith('.html') || filename.endsWith('.htm')) {
          // 尝试获取当前域并构造可能的URL
          try {
            const { result } = await this.execute('Runtime', 'evaluate', {
              expression: 'window.location.origin',
              returnByValue: true
            });
            
            if (result && result.value) {
              const origin = result.value;
              const potentialUrl = `${origin}/${filename}`;
              console.log(`尝试使用潜在URL: ${potentialUrl}`);
              return potentialUrl;
            }
          } catch (e) {
            console.debug('构造潜在URL失败:', e.message);
          }
        }
        
        // 尝试使用Runtime.evaluate执行JavaScript来获取已加载的脚本
        try {
          const { result } = await this.execute('Runtime', 'evaluate', {
            expression: 'Array.from(document.scripts).map(s => s.src).filter(Boolean)',
            returnByValue: true
          });
          
          if (result && result.value && Array.isArray(result.value)) {
            const documentScripts = result.value;
            console.log(`从文档中获取到 ${documentScripts.length} 个脚本`);
            
            // 尝试在文档脚本中找到匹配项
            for (const scriptUrl of documentScripts) {
              if (scriptUrl.includes(filename)) {
                console.log(`从文档中找到匹配的脚本: ${filename} -> ${scriptUrl}`);
                return scriptUrl;
              }
            }
          }
        } catch (e) {
          console.debug('从文档获取脚本失败:', e.message);
        }
        
        // 回退方案：返回原始文件名
        console.warn(`⚠️  未找到匹配的脚本URL: '${filename}'，将直接使用`);
        return filename;
      }
      
      // 尝试找到完全匹配的脚本（基于文件名）
      for (const script of scripts) {
        if (script.url) {
          // 检查URL的最后一部分是否匹配文件名
          const urlParts = script.url.split('/');
          const urlFilename = urlParts[urlParts.length - 1];
          
          if (urlFilename === filename) {
            console.log(`找到完全匹配的文件名: ${filename} -> ${script.url}`);
            return script.url;
          }
        }
      }
      
      // 尝试部分匹配（忽略URL参数）
      const filenameWithoutParams = filename.split('?')[0];
      for (const script of scripts) {
        if (script.url) {
          const scriptUrlWithoutParams = script.url.split('?')[0];
          if (scriptUrlWithoutParams.includes(filenameWithoutParams)) {
            console.log(`找到部分匹配的URL（忽略参数）: ${filename} -> ${script.url}`);
            return script.url;
          }
        }
      }
      
      // 尝试更宽松的部分匹配
      for (const script of scripts) {
        if (script.url && script.url.includes(filename)) {
          console.log(`找到部分匹配的URL: ${filename} -> ${script.url}`);
          return script.url;
        }
      }
      
      // 回退方案：返回原始文件名
      console.warn(`⚠️  未找到匹配的脚本URL: '${filename}'，将直接使用`);
      return filename;
    } catch (error) {
      console.error(`查找匹配脚本URL失败: ${error.message}`);
      return filename;
    }
  }
  
  /**
   * 执行CDP命令
   * @param {string} domain - 命令所属域
   * @param {string} method - 命令方法名
   * @param {Object} params - 命令参数
   * @returns {Promise<any>} 命令执行结果
   */
  async execute(domain, method, params = {}) {
    if (!this.client) {
      await this.connect();
    }

    if (!this.client[domain] || typeof this.client[domain][method] !== 'function') {
      throw new Error(`不支持的CDP命令: ${domain}.${method}`);
    }

    try {
      return await this.client[domain][method](params);
    } catch (error) {
      console.error(`执行CDP命令失败 ${domain}.${method}:`, error.message);
      throw error;
    }
  }

  /**
   * 获取所有可用的目标页面
   * @returns {Promise<Array>} 目标页面列表
   */
  async getTargets() {
    try {
      // 使用完整的选项对象
      const listOptions = {
        host: this.options.host,
        port: this.options.port,
        secure: false
      };
      
      const result = await CDP.List(listOptions);
      
      // 兼容性处理，支持不同版本的返回格式
      let targets = [];
      if (Array.isArray(result)) {
        targets = result;
      } else if (Array.isArray(result.targets)) {
        targets = result.targets;
      }
      
      return targets;
    } catch (error) {
      console.error('获取目标页面列表失败:', error.message);
      
      // 尝试直接访问调试接口
      try {
        const http = require('http');
        console.log('尝试通过HTTP直接访问调试接口...');
        
        return new Promise((resolve) => {
          const req = http.get(`http://${this.options.host}:${this.options.port}/json/list`, (res) => {
            let data = '';
            res.on('data', (chunk) => {
              data += chunk;
            });
            res.on('end', () => {
              try {
                const targets = JSON.parse(data);
                console.log(`通过HTTP直接获取到 ${targets.length} 个目标页面`);
                resolve(targets);
              } catch (parseError) {
                console.error('解析HTTP响应失败:', parseError.message);
                resolve([]);
              }
            });
          }).on('error', (httpError) => {
            console.error('HTTP请求失败:', httpError.message);
            resolve([]);
          });
        });
      } catch (fallbackError) {
        console.error('备用方法也失败:', fallbackError.message);
        return [];
      }
    }
  }

  /**
   * 连接到指定的目标页面
   * @param {number} targetId - 目标页面ID
   * @returns {Promise<Object>} CDP客户端实例
   */
  async connectToTarget(targetId) {
    try {
      // 先断开现有连接
      await this.disconnect();
      
      // 连接到指定目标
      this.client = await CDP({
        ...this.options,
        target: targetId
      });
      
      // 启用必要的域
      await this.enableDomains(['Page', 'Runtime', 'Debugger', 'Network']);
      
      this.target = targetId;
      console.log(`已连接到目标页面: ${targetId}`);
      
      return this.client;
    } catch (error) {
      console.error('连接到指定目标页面失败:', error.message);
      throw error;
    }
  }
}

module.exports = ConnectionManager;