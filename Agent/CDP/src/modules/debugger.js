/**
 * 调试器模块
 * 通过CDP的Debugger域设置和管理断点
 */

class Debugger {
  constructor(connectionManager) {
    this.connectionManager = connectionManager;
    this.breakpoints = new Map(); // 存储已设置的断点
    this.client = null;
    this.fileViewer = null;
    this._eventListeners = new Map(); // 存储自定义事件监听器
    this._eventHandlers = {}; // 存储CDP事件处理器引用，用于清理
    this._currentPageUrl = null; // 存储当前页面URL
    this._isPaused = false; // 跟踪当前是否处于暂停状态
    this._callFrames = []; // 存储当前调用栈信息
    this._pauseEvent = null; // 存储原始暂停事件
    this._originalLineNumber = 0; // 存储原始0基行号用于位置映射
    this._networkRequests = new Map(); // 存储网络请求信息
    this._enabledDomains = new Set(); // 跟踪已启用的域
  }
  
  /**
   * 设置文件查看器实例
   * @param {FileViewer} fileViewer - 文件查看器实例
   */
  setFileViewer(fileViewer) {
    this.fileViewer = fileViewer;
  }
  
  /**
   * 注册事件监听器
   * @param {string} eventName - 事件名称
   * @param {Function} listener - 事件处理函数
   */
  on(eventName, listener) {
    if (!this._eventListeners.has(eventName)) {
      this._eventListeners.set(eventName, new Set());
    }
    this._eventListeners.get(eventName).add(listener);
  }
  
  /**
   * 移除事件监听器
   * @param {string} eventName - 事件名称
   * @param {Function} listener - 事件处理函数（可选，如果不提供则移除该事件的所有监听器）
   */
  off(eventName, listener) {
    if (this._eventListeners.has(eventName)) {
      if (listener) {
        this._eventListeners.get(eventName).delete(listener);
      } else {
        this._eventListeners.delete(eventName);
      }
    }
  }
  
  /**
   * 触发自定义事件
   * @param {string} eventName - 事件名称
   * @param {*} data - 事件数据
   */
  _emit(eventName, data) {
    if (this._eventListeners.has(eventName)) {
      const listeners = this._eventListeners.get(eventName);
      for (const listener of listeners) {
        try {
          listener(data);
        } catch (error) {
          console.error(`执行事件监听器时出错 [${eventName}]:`, error.message);
        }
      }
    }
  }

  /**
   * 初始化调试器
   * @returns {Promise<void>}
   */
  async initialize() {
    try {
      this.client = await this.connectionManager.connect();
      
      // 确保所需域已启用
      await this.connectionManager.enableDomains(['Debugger', 'Network']);
      this._enabledDomains.add('Debugger');
      this._enabledDomains.add('Network');
      
      // 获取当前页面URL
      try {
        const targets = await this.connectionManager.getTargets();
        if (targets && targets.length > 0) {
          const mainTarget = targets.find(t => t.type === 'page' && t.attached) || targets[0];
          if (mainTarget && mainTarget.url) {
            this._currentPageUrl = mainTarget.url;
          }
        }
      } catch (err) {
        // 忽略获取页面URL失败的情况
      }
      
      // 初始化断点持久化存储
      await this._initBreakpointStorage();
      
      // 注册断点事件监听器
      this.setupEventListeners();
      
      console.log('调试器已初始化');
    } catch (error) {
      console.error('初始化调试器失败:', error.message);
      throw error;
    }
  }

  /**
   * 初始化断点持久化存储
   * @private
   */
  async _initBreakpointStorage() {
    const fs = require('fs');
    const path = require('path');
    
    // 创建持久化存储目录
    this.breakpointStoragePath = path.join(process.cwd(), '.cdp-breakpoints.json');
    
    try {
      // 尝试读取已保存的断点
      if (fs.existsSync(this.breakpointStoragePath)) {
        const savedBreakpoints = JSON.parse(fs.readFileSync(this.breakpointStoragePath, 'utf8'));
        
        // 恢复所有类型的有效断点
        let restoredCount = 0;
        savedBreakpoints.forEach(bp => {
          if (bp.id) { // 确保是有效的断点
            this.breakpoints.set(bp.id, bp);
            restoredCount++;
          }
        });
        
        // 尝试重新激活所有恢复的断点
        if (restoredCount > 0 && this.client) {
          // 重新设置所有恢复的断点到Chrome中
          for (const bp of this.breakpoints.values()) {
            try {
              // 重新设置断点，使用原始的URL、行号和选项
              const newBpId = await this.setBreakpoint(bp.url, bp.lineNumber, bp.options);
            } catch (error) {
              // 如果重新设置失败，从内存中移除该断点
              this.breakpoints.delete(bp.id);
            }
          }
        }
      }
    } catch (error) {
      // 如果读取失败，创建一个空文件
      try {
        fs.writeFileSync(this.breakpointStoragePath, JSON.stringify([]));
      } catch (writeError) {
        console.warn('创建断点存储文件失败:', writeError.message);
      }
    }
  }

  /**
   * 保存断点到持久化存储
   * @private
   */
  _saveBreakpoints() {
    try {
      const fs = require('fs');
      
      // 只保存活跃的断点
      const activeBreakpoints = Array.from(this.breakpoints.values())
        .filter(bp => bp.active !== false);
      
      // 保存断点到文件
      fs.writeFileSync(this.breakpointStoragePath, JSON.stringify(activeBreakpoints, null, 2));
    } catch (error) {
      console.error('❌ 保存断点持久化存储失败:', error.message);
    }
  }

  /**
   * 设置事件监听器
   * @private
   */
  setupEventListeners() {
    // 使用connectionManager注册事件监听器
    // 这样可以确保即使命令执行完成，我们仍然能够接收断点事件
    
    // 断点命中事件处理函数
    const handlePaused = (event) => {
      try {
        // 提取必要信息构造断点命中事件数据
        let url = 'unknown';
        let lineNumber = 0;
        let callFrames = [];
        
        // 更安全地获取callFrames信息
        if (event.callFrames && Array.isArray(event.callFrames) && event.callFrames.length > 0) {
          // 处理每个调用栈帧，确保functionName和url有默认值
          callFrames = event.callFrames.map(frame => {
            // 提取location信息，优先从location对象获取
            const location = frame.location || {};
            
            // 获取scriptId，尝试多种来源
            const scriptId = location.scriptId || frame.scriptId;
            
            // 确定URL，尝试多种方式
            let url = frame.url || location.url;
            
            // 如果没有URL但有scriptId，尝试获取脚本信息
            if (!url && scriptId) {
              url = `script:${scriptId}`;
              // 对于已知的HTML页面内联脚本，使用更友好的显示
              if (this._currentPageUrl && this._currentPageUrl.includes('demo-page.html')) {
                url = `${this._currentPageUrl} (内联脚本:${scriptId})`;
              }
            }
            
            // 确保有默认值
            if (!url) {
              url = this._currentPageUrl ? `${this._currentPageUrl} (内联脚本)` : 'unknown';
            }
            
            return {
              ...frame,
              functionName: frame.functionName || '(匿名函数)',
              url: url,
              scriptId: scriptId,
              lineNumber: frame.lineNumber !== undefined ? frame.lineNumber : (location.lineNumber !== undefined ? location.lineNumber : 0),
              columnNumber: frame.columnNumber !== undefined ? frame.columnNumber : (location.columnNumber !== undefined ? location.columnNumber : 0)
            };
          });
          
          // 从第一个调用栈帧获取位置信息
          const firstFrame = callFrames[0];
          if (firstFrame) {
            url = firstFrame.url;
            // 保存原始0基行号用于位置映射
            this._originalLineNumber = parseInt(firstFrame.lineNumber);
            // 转换为1基行号用于显示
            lineNumber = this._originalLineNumber + 1;
          }
        }
        
        // 如果callFrames为空，尝试从event.location获取信息
        if (lineNumber === 0 && event.location) {
          console.log('从event.location获取位置信息');
          url = event.location.url || (event.location.scriptId ? `script:${event.location.scriptId}` : url);
          // 保存原始0基行号用于位置映射
          this._originalLineNumber = event.location.lineNumber !== undefined ? parseInt(event.location.lineNumber) : 0;
          // 转换为1基行号用于显示
          lineNumber = this._originalLineNumber + 1;
        }
        
        // 改进URL处理，对于HTML内联脚本尝试提供更有用的信息
        if (url === 'unknown' && this._currentPageUrl) {
          url = `${this._currentPageUrl} (内联脚本)`;
        }
        
        // 确保lineNumber是有效的数字
        if (isNaN(lineNumber) || lineNumber <= 0) {
          lineNumber = 0;
        }
        
        const pauseInfo = {
          reason: event.reason || 'unknown',
          hitBreakpoints: event.hitBreakpoints || [],
          callFrames: callFrames,
          url: url,
          lineNumber: lineNumber,
          originalEvent: { 
            reason: event.reason,
            hitBreakpoints: event.hitBreakpoints,
            hasCallFrames: !!callFrames.length
          }
        };
        
        // 更新暂停状态和调用栈信息
        this._isPaused = true;
        this._callFrames = event.callFrames || [];
        this._pauseEvent = event;
        
        // 查找断点在格式化代码中的位置
        let formattedPosition = null;
        let matchingBreakpoint = null;
        let mappedVirtualLine = lineNumber;
        
        // 检查是否有位置映射信息
        if (this.fileViewer) {
          // 首先尝试使用精确匹配的URL
          let positionMap = this.fileViewer.getCurrentPositionMap(url);
          let matchedUrl = url;
          
          // 如果没有找到精确匹配，尝试找到最匹配的URL
          if (!positionMap || !positionMap.reverseMap) {
            const allPositionMaps = this.fileViewer.getCurrentPositionMap();
            // 尝试多种匹配策略
            const urlVariants = [url, url.split('?')[0], url.split('#')[0]];
            
            for (const variant of urlVariants) {
              for (const [mapUrl, map] of Object.entries(allPositionMaps)) {
                const mapUrlClean = mapUrl.split('?')[0].split('#')[0];
                if (variant.includes(mapUrlClean) || mapUrlClean.includes(variant)) {
                  positionMap = map;
                  matchedUrl = mapUrl;
                  break;
                }
              }
              if (positionMap) break;
            }
          }
          
          // 如果有反向映射，使用它来查找格式化位置
  if (positionMap.reverseMap) {
    const reverseMap = positionMap.reverseMap;
    
    // 使用原始0基行号进行位置映射
    const originalLine = this._originalLineNumber;
    const originalColumn = pauseInfo.originalEvent.hasCallFrames ? callFrames[0].columnNumber : 0;
    
    // 首先尝试精确匹配（行号和列号）
    let mappedEntry = null;
    const lineColumnKey = `${originalLine}-${originalColumn}`;
    
    if (reverseMap[lineColumnKey]) {
      mappedEntry = reverseMap[lineColumnKey];
      console.log(`找到精确行列映射: 原始 ${lineColumnKey} -> 格式化 ${mappedEntry.formattedLine}:${mappedEntry.formattedColumn}`);
    } else if (reverseMap[originalLine]) {
      // 如果没有精确行列匹配，尝试仅匹配行号
      mappedEntry = reverseMap[originalLine];
      console.log(`找到行号映射: 原始 ${originalLine} -> 格式化 ${mappedEntry.formattedLine}`);
    } else {
      // 如果没有行号匹配，尝试找到最接近的行号（用于压缩代码）
      const reverseMapEntries = Object.entries(reverseMap);
      let closestEntry = null;
      let closestLine = -1;
      
      for (const [key, entry] of reverseMapEntries) {
        // 跳过基于行列的映射键
        if (key.includes('-')) continue;
        
        const mapLine = parseInt(key);
        if (mapLine <= originalLine && mapLine > closestLine) {
          closestLine = mapLine;
          closestEntry = entry;
        }
      }
      
      if (closestEntry) {
        mappedEntry = closestEntry;
        console.log(`找到最接近的映射: 原始 ${originalLine} -> 格式化 ${mappedEntry.formattedLine} (基于最接近行 ${closestLine})`);
      }
    }
    
    if (mappedEntry) {
      formattedPosition = {
        formattedLine: mappedEntry.formattedLine,
        formattedColumn: mappedEntry.formattedColumn
      };
      mappedVirtualLine = formattedPosition.formattedLine;
    } else {
      console.log(`未找到位置映射，使用原始位置`);
    }
    
    console.log(`原始位置 (${originalLine}:${originalColumn}) 映射到虚拟位置 (${mappedVirtualLine}:${formattedPosition?.formattedColumn || 0})，使用URL: ${matchedUrl}`);
  } else {
    console.log(`未找到位置映射信息，使用原始位置 (${lineNumber}:${pauseInfo.originalEvent.hasCallFrames ? callFrames[0].columnNumber : 0})`);
  }
          
          // 检查是否有设置在虚拟行号的断点
          for (const [breakpointId, breakpoint] of this.breakpoints.entries()) {
            if (breakpoint.url.includes(matchedUrl) || matchedUrl.includes(breakpoint.url)) {
              if (breakpoint.lineNumber === mappedVirtualLine) {
                matchingBreakpoint = breakpoint;
                console.log(`找到匹配的断点: ${breakpointId} (虚拟行 ${mappedVirtualLine})`);
                break;
              }
            }
          }
        }
        
        // 更新pauseInfo，包含格式化位置信息
        pauseInfo.formattedPosition = formattedPosition || {
          formattedLine: lineNumber,
          formattedColumn: 0
        };
        
        // 触发自定义断点命中事件
        this._emit('breakpointHit', pauseInfo);
      } catch (error) {
        console.error('处理断点命中事件时出错:', error.message);
        // 即使出错也触发事件，提供基本信息
        this._emit('breakpointHit', {
          reason: 'error',
          hitBreakpoints: event.hitBreakpoints || [],
          callFrames: [],
          url: 'unknown',
          lineNumber: 0,
          error: error.message
        });
      }
    };
    
    // 存储处理器引用，用于后续清理
    this._eventHandlers['Debugger.paused'] = handlePaused;
    
    // 使用connectionManager注册事件监听器
    this.connectionManager.on('Debugger.paused', handlePaused);

    // 断点解析事件
    this.connectionManager.on('Debugger.breakpointResolved', (event) => {
      console.log(`✅ 断点已解析: ${event.location.url || 'unknown'} 第 ${event.location.lineNumber + 1} 行`);
    });
    
    // 程序恢复执行事件
    this.connectionManager.on('Debugger.resumed', () => {
      // 清除暂停状态和调用栈信息
      this._isPaused = false;
      this._callFrames = [];
      this._pauseEvent = null;
    });

    // 程序恢复执行事件处理函数
    const handleResumed = () => {
      // 触发自定义恢复执行事件
      this._emit('resumed', {});
    };
    
    // 存储处理器引用，用于后续清理
    this._eventHandlers['Debugger.resumed'] = handleResumed;
    
    // 使用connectionManager注册事件监听器
    this.connectionManager.on('Debugger.resumed', handleResumed);
    
    // 添加调试状态事件
    this.connectionManager.on('Debugger.scriptParsed', (event) => {
      // 仅在调试模式下打印，避免过多日志
      if (process.env.DEBUG) {
        console.debug(`📄 脚本已加载: ${event.url || 'unknown'}`);
      }
    });

    // 网络请求事件监听器
    this.connectionManager.on('Network.requestWillBeSent', (event) => {
      // 存储请求发送事件
      let requestData = {
        requestId: event.requestId,
        url: event.request.url,
        type: event.type || 'other',
        method: event.request.method,
        timestamp: event.timestamp,
        status: 'pending',
        initiator: event.initiator,
        callStack: event.stack?.callFrames || []
      };
      
      this._networkRequests.set(event.requestId, requestData);
      
      // 触发自定义事件
      this._emit('networkRequestSent', requestData);
      this._emit('networkRequestReceived', requestData);
      
      // 在调试模式下打印请求信息
      if (process.env.DEBUG) {
        console.debug(`📤 网络请求发送: ${event.type || 'unknown'} ${event.request.method} ${event.request.url}`);
      }
    });

    // 网络响应事件监听器
    this.connectionManager.on('Network.responseReceived', (event) => {
      // 更新请求状态为已完成
      const requestData = this._networkRequests.get(event.requestId);
      if (requestData) {
        requestData.status = 'completed';
        requestData.response = {
          status: event.response.status,
          statusText: event.response.statusText,
          headers: event.response.headers
        };
        this._networkRequests.set(event.requestId, requestData);
        
        // 触发自定义事件
        this._emit('networkResponseReceived', requestData);
        this._emit('networkRequestReceived', requestData);
        
        // 在调试模式下打印响应信息
        if (process.env.DEBUG) {
          console.debug(`📥 网络响应接收: ${event.type || 'unknown'} ${event.response.status} ${event.requestId}`);
        }
      }
    });
  }

  /**
   * 获取脚本ID
   * @param {string} url - 脚本URL
   * @returns {Promise<string>} 脚本ID
   */
  /**
   * 在指定文件的指定行设置断点
   * 使用setBreakpointByUrl方法，不需要先获取scriptId
   * @param {string} url - 脚本URL
   * @param {number} lineNumber - 行号（从1开始）
   * @param {Object} options - 断点选项
   * @returns {Promise<string>} 断点ID
   */
  async setBreakpoint(url, lineNumber, options = {}) {
    try {
      if (!this.client) {
        await this.initialize();
      }
      
      // 首先使用connectionManager的方法查找最匹配的脚本URL
      let targetUrl = await this.connectionManager.findMatchingScriptUrl(url);
      
      // 尝试获取位置映射信息（用于格式化代码的断点）
      let originalPosition = { line: lineNumber, column: options.columnNumber || 0 };
      
      // 检查是否需要获取位置映射信息
      let positionMap = options.positionMap || {};
      let matchedUrl = url;
      
      // 如果没有提供位置映射，但有fileViewer实例，则尝试从fileViewer获取
      if (Object.keys(positionMap).length === 0 && this.fileViewer) {
        // 首先尝试使用精确匹配的URL
        positionMap = this.fileViewer.getCurrentPositionMap(targetUrl) || this.fileViewer.getCurrentPositionMap(url);
        
        // 如果没有找到精确匹配，尝试找到最匹配的URL
        if (!positionMap || Object.keys(positionMap).length === 0) {
          const allPositionMaps = this.fileViewer.getCurrentPositionMap();
          for (const [mapUrl, map] of Object.entries(allPositionMaps)) {
            if (url.includes(mapUrl) || mapUrl.includes(url) || targetUrl.includes(mapUrl) || mapUrl.includes(targetUrl)) {
              positionMap = map;
              matchedUrl = mapUrl;
              break;
            }
          }
        }
      }
      
      // 如果找到位置映射，则将格式化后的行号映射回原始代码
      if (positionMap && positionMap[lineNumber]) {
        originalPosition.line = positionMap[lineNumber].originalLine;
        originalPosition.column = positionMap[lineNumber].originalColumn;
      } else if (options.formatted && this.fileViewer) {
          // 如果没有找到位置映射但指定了formatted选项，尝试重新获取文件内容以生成位置映射
          try {
            // 尝试获取文件内容并生成位置映射，同时保存到targetUrl和原始url
            await this.fileViewer.getFileContent(url, 1, null, 'js', true, true);
            // 先尝试使用targetUrl获取映射，如果没有再尝试使用原始url
            positionMap = this.fileViewer.getCurrentPositionMap(targetUrl) || this.fileViewer.getCurrentPositionMap(url);
            if (positionMap && positionMap[lineNumber]) {
              originalPosition.line = positionMap[lineNumber].originalLine;
              originalPosition.column = positionMap[lineNumber].originalColumn;
            }
          } catch (error) {
            // 忽略错误，继续使用原始位置
          }
        }
      
      // 检查是否已经存在相同的断点
      let existingBreakpoint = null;
      for (const bp of this.breakpoints.values()) {
        if (bp.url === targetUrl && bp.lineNumber === lineNumber) {
          existingBreakpoint = bp;
          break;
        }
      }
      
      // 如果存在相同的断点，返回null表示重复断点
      if (existingBreakpoint) {
        return null;
      }
      
      // 尝试使用setBreakpointByUrl方法设置断点
      try {
        const result = await this.connectionManager.execute('Debugger', 'setBreakpointByUrl', {
          url: targetUrl,
          lineNumber: originalPosition.line - 1, // CDP使用0基行号
          columnNumber: originalPosition.column,
          condition: options.condition,
          ignoreCount: options.ignoreCount || 0,
          enabled: options.enabled !== false
        });
        
        // 保存断点信息
        const breakpointId = result.breakpointId;
        const breakpointInfo = {
          id: breakpointId,
          url: targetUrl,
          lineNumber,
          options,
          type: 'script',
          active: true
        };
        
        this.breakpoints.set(breakpointId, breakpointInfo);
        
        // 保存到持久化存储
        this._saveBreakpoints();
        
        return breakpointId;
      } catch (setBreakpointError) {
        // 检查是否是因为Debugger域不支持导致的错误
        if (setBreakpointError.message.includes('unsupported command') || 
            setBreakpointError.message.includes('不支持的CDP命令') ||
            setBreakpointError.message.includes('Debugger')) {
          console.log(`⚠️  Debugger.setBreakpointByUrl命令可能不被支持，尝试使用替代方法...`);
          
          // 尝试使用Runtime.evaluate来设置断点（适用于某些受限环境）
          try {
            // 构造一个简单的断点函数，通过eval注入到页面
            const breakpointCode = `
              (function() {
                // 查找目标脚本元素
                const scripts = document.querySelectorAll('script[src*="${url}"]');
                if (scripts.length > 0) {
                  console.log('[CDP Debugger] 找到目标脚本，尝试设置断点...');
                  // 这里我们无法直接设置真正的调试断点，但可以添加日志输出
                  console.log('[CDP Debugger] 断点位置：${url} 第 ${lineNumber} 行');
                  return true;
                }
                return false;
              })();
            `;
            
            await this.connectionManager.execute('Runtime', 'evaluate', {
              expression: breakpointCode,
              returnByValue: true
            });
            
            console.log(`ℹ️  已尝试使用替代方法设置断点，建议检查页面控制台输出`);
            console.log(`   注意：此替代方法可能无法提供完整的调试功能`);
            
            // 由于无法获取真正的断点ID，我们生成一个临时ID
            const tempBreakpointId = `temp-${Date.now()}`;
            
            // 保存断点信息（标记为临时断点）
            const breakpointInfo = {
              id: tempBreakpointId,
              url: targetUrl,
              lineNumber,
              options,
              type: 'script',
              active: true,
              isTemporary: true
            };
            
            this.breakpoints.set(tempBreakpointId, breakpointInfo);
            
            // 保存到持久化存储
            this._saveBreakpoints();
            
            return tempBreakpointId;
          } catch (evalError) {
            throw setBreakpointError; // 抛出原始错误
          }
        } else {
          // 其他类型的错误，直接抛出
          throw setBreakpointError;
        }
      }
    } catch (error) {
      // 检查是否是重复断点错误
      if (error.message.includes('duplicate') || error.message.includes('already exists')) {
        return null;
      }
      
      console.error('设置断点失败:', error.message);
      
      throw error;
    }
  }

  /**
   * 移除断点
   * @param {string} breakpointId - 断点ID
   * @returns {Promise<void>}
   */
  async removeBreakpoint(breakpointId) {
    try {
      if (!this.client) {
        await this.initialize();
      }
      
      // 使用connectionManager.execute来移除断点
      await this.connectionManager.execute('Debugger', 'removeBreakpoint', { breakpointId });
      this.breakpoints.delete(breakpointId);
      
      // 更新持久化存储
      this._saveBreakpoints();
      
      console.log(`已移除断点: ${breakpointId}`);
    } catch (error) {
      console.error('移除断点失败:', error.message);
      throw error;
    }
  }

  /**
   * 清除所有断点
   * @returns {Promise<void>}
   */
  async clearAllBreakpoints() {
    try {
      for (const breakpointId of this.breakpoints.keys()) {
        try {
          await this.connectionManager.execute('Debugger', 'removeBreakpoint', { breakpointId });
        } catch (e) {
          // 忽略单个断点移除失败，继续移除其他断点
          console.debug(`移除断点 ${breakpointId} 失败: ${e.message}`);
        }
      }
      
      // 清除内存中的断点记录
      this.breakpoints.clear();
      
      // 更新持久化存储
      this._saveBreakpoints();
      
      console.log('已清除所有断点');
    } catch (error) {
      console.error('清除所有断点失败:', error.message);
      throw error;
    }
  }

  /**
   * 获取所有断点
   * @returns {Array} 断点列表
   */
  async getAllBreakpoints() {
    // 由于我们使用文件持久化，这里直接返回内存中的断点列表
    // 如果需要，也可以尝试从Chrome重新设置所有保存的断点
    return Array.from(this.breakpoints.values());
  }

  /**
   * 获取当前断点命中位置的代码上下文
   * @param {number} contextLines - 上下文行数，默认显示前后3行
   * @param {number} frameIndex - 调用栈帧索引，默认为0（当前帧）
   * @returns {Promise<Object>} 代码上下文信息
   */
  async getCurrentCodeContext(contextLines = 3, frameIndex = 0) {
    try {
      // 检查是否处于暂停状态
      if (!this._isPaused || !this._callFrames || this._callFrames.length === 0) {
        throw new Error('当前未处于断点暂停状态');
      }

      // 检查调用栈帧索引是否有效
      if (frameIndex < 0 || frameIndex >= this._callFrames.length) {
        throw new Error('无效的调用栈帧索引');
      }

      const currentFrame = this._callFrames[frameIndex];
      const scriptId = currentFrame.location.scriptId;
      const lineNumber = currentFrame.location.lineNumber; // CDP使用0基行号
      const columnNumber = currentFrame.location.columnNumber || 0; // 0基列号
      const url = currentFrame.url;

      // 获取脚本源代码
      const result = await this.connectionManager.execute('Debugger', 'getScriptSource', {
        scriptId
      });

      const sourceCode = result.scriptSource;
      const lines = sourceCode.split('\n');

      // 提取上下文代码
      const context = [];

      // 处理单行文件的情况
      if (lines.length === 1) {
        const lineContent = lines[0];
        const lineLength = lineContent.length;
        const singleLine = true;

        // 如果列号超过了行长度，设置为行末尾
        const adjustedColumnNumber = Math.min(columnNumber, lineLength - 1);

        // 计算上下文范围（字符数）
        const charsPerLine = 80; // 每行显示的字符数
        const contextChars = contextLines * charsPerLine;

        // 计算上下文的起始和结束位置
        let startPos = Math.max(0, adjustedColumnNumber - contextChars);
        let endPos = Math.min(lineLength - 1, adjustedColumnNumber + contextChars);

        // 如果内容较短，显示全部
        if (lineLength <= contextChars * 2) {
          startPos = 0;
          endPos = lineLength - 1;
        }

        // 提取上下文内容
        const contextContent = lineContent.substring(startPos, endPos + 1);

        // 添加到上下文列表
        context.push({
          line: lineNumber + 1, // 转换为1基行号
          content: contextContent,
          isCurrent: true,
          columnNumber: adjustedColumnNumber - startPos, // 相对于上下文起始位置的列号
          startPos, // 上下文在原始行中的起始位置
          endPos // 上下文在原始行中的结束位置
        });
      } else {
        // 处理多行文件的情况
        const startLine = Math.max(0, lineNumber - contextLines);
        const endLine = Math.min(lines.length - 1, lineNumber + contextLines);

        for (let i = startLine; i <= endLine; i++) {
          const lineItem = {
            line: i + 1, // 转换为1基行号
            content: lines[i] || '',
            isCurrent: i === lineNumber
          };
          
          // 为当前行添加列号信息
          if (i === lineNumber) {
            lineItem.columnNumber = columnNumber;
          }
          
          context.push(lineItem);
        }
      }

      return {
        url,
        lineNumber: lineNumber + 1, // 转换为1基行号
        columnNumber: columnNumber + 1, // 转换为1基列号
        contextLines: context,
        totalLines: lines.length
      };
    } catch (error) {
      console.error('获取代码上下文失败:', error.message);
      throw error;
    }
  }

  /**
   * 继续执行
   * @returns {Promise<void>}
   */
  async resume() {
    try {
      if (!this.client) {
        await this.initialize();
      }
      
      await this.connectionManager.execute('Debugger', 'resume', {});
    } catch (error) {
      console.error('继续执行失败:', error.message);
      throw error;
    }
  }

  /**
   * 单步执行
   * @returns {Promise<void>}
   */
  async stepOver() {
    try {
      if (!this.client) {
        await this.initialize();
      }
      
      await this.connectionManager.execute('Debugger', 'stepOver', {});
    } catch (error) {
      console.error('单步执行失败:', error.message);
      throw error;
    }
  }

  /**
   * 步入函数
   * @returns {Promise<void>}
   */
  async stepInto() {
    try {
      if (!this.client) {
        await this.initialize();
      }
      
      await this.connectionManager.execute('Debugger', 'stepInto', {});
    } catch (error) {
      console.error('步入函数失败:', error.message);
      throw error;
    }
  }

  /**
   * 步出函数
   * @returns {Promise<void>}
   */
  async stepOut() {
    try {
      if (!this.client) {
        await this.initialize();
      }
      
      await this.connectionManager.execute('Debugger', 'stepOut', {});
    } catch (error) {
      console.error('步出函数失败:', error.message);
      throw error;
    }
  }

  /**
   * 计算表达式的值
   * @param {string} expression - 要计算的表达式
   * @param {number} frameIndex - 调用栈帧索引，默认为0（当前帧）
   * @returns {Promise<any>} 表达式计算结果
   */
  async evaluate(expression, frameIndex = 0) {
    try {
      if (!this.client) {
        await this.initialize();
      }
      
      // 根据是否处于暂停状态选择不同的执行方式
      if (this._isPaused && this._callFrames && this._callFrames.length > 0 && frameIndex >= 0 && frameIndex < this._callFrames.length) {
        // 在暂停状态下，使用Debugger.evaluateOnCallFrame在指定的调用栈帧中执行表达式
        console.log(`在调用栈帧 ${frameIndex} 中执行表达式: ${expression}`);
        const callFrameId = this._callFrames[frameIndex].callFrameId;
        
        const result = await this.connectionManager.execute('Debugger', 'evaluateOnCallFrame', {
          callFrameId,
          expression,
          returnByValue: true,
          generatePreview: true
        });
        
        if (result.exceptionDetails) {
          throw new Error(`表达式执行错误: ${result.exceptionDetails.text}`);
        }
        
        return result.result.value;
      } else {
        // 在非暂停状态下，使用Runtime.evaluate在全局上下文中执行表达式
        console.log(`在全局上下文中执行表达式: ${expression}`);
        const result = await this.connectionManager.execute('Runtime', 'evaluate', {
          expression,
          contextId: 1, // 默认上下文
          returnByValue: true,
          awaitPromise: true,
          generatePreview: true
        });
        
        if (result.exceptionDetails) {
          throw new Error(`表达式执行错误: ${result.exceptionDetails.text}`);
        }
        
        return result.result.value;
      }
    } catch (error) {
      console.error('计算表达式失败:', error.message);
      throw error;
    }
  }

  /**
   * 启用或禁用断点
   * @param {string} breakpointId - 断点ID
   * @param {boolean} enabled - 是否启用
   * @returns {Promise<void>}
   */
  async setBreakpointEnabled(breakpointId, enabled) {
    try {
      if (!this.client) {
        await this.initialize();
      }
      
      const breakpoint = this.breakpoints.get(breakpointId);
      if (!breakpoint) {
        throw new Error(`未找到断点: ${breakpointId}`);
      }
      
      // 先移除旧断点
      await this.removeBreakpoint(breakpointId);
      
      // 创建新断点，使用更新后的enabled状态
      const newOptions = { ...breakpoint.options, enabled };
      await this.setBreakpoint(breakpoint.url, breakpoint.lineNumber, newOptions);
      
      console.log(`断点 ${breakpointId} 已${enabled ? '启用' : '禁用'}`);
    } catch (error) {
      console.error('更新断点状态失败:', error.message);
      throw error;
    }
  }

  /**
   * 设置条件断点
   * @param {string} url - 脚本URL
   * @param {number} lineNumber - 行号
   * @param {string} condition - 条件表达式
   * @returns {Promise<string>} 断点ID
   */
  async setConditionalBreakpoint(url, lineNumber, condition) {
    return this.setBreakpoint(url, lineNumber, { condition });
  }

  /**
   * 启用DOM断点
   * @param {string} selector - DOM元素选择器
   * @param {string} type - 断点类型 ('subtree-modified', 'attribute-modified', 'node-removed')
   * @returns {Promise<string>} 断点ID
   */
  async setDOMBreakpoint(selector, type) {
    try {
      if (!this.client) {
        await this.initialize();
      }
      
      // 确保DOM域已启用
      if (!this.client.DOM) {
        await this.connectionManager.enableDomains(['DOM']);
      }
      
      // 查找DOM节点
      const { nodeId } = await this.client.DOM.querySelector({
        nodeId: 1, // document节点
        selector
      });
      
      // 设置DOM断点
      await this.client.DOM.setDOMBreakpoint({
        nodeId,
        type
      });
      
      const breakpointId = `dom-${nodeId}-${type}`;
      this.breakpoints.set(breakpointId, {
        id: breakpointId,
        type: 'dom',
        selector,
        domType: type,
        nodeId,
        active: true
      });
      
      // 保存到持久化存储
      this._saveBreakpoints();
      
      console.log(`已在元素 ${selector} 设置${type}类型的DOM断点`);
      return breakpointId;
    } catch (error) {
      console.error('设置DOM断点失败:', error.message);
      throw error;
    }
  }

  /**
   * 获取当前作用域的所有变量
   * @param {number} frameIndex - 调用栈帧索引
   * @param {number} maxDepth - 最大递归深度
   * @returns {Promise<object>} 包含所有作用域变量的对象
   */
  async getAllScopeVariables(frameIndex = 0, maxDepth = 3) {
    try {
      if (!this._isPaused || !this._callFrames || this._callFrames.length === 0) {
        throw new Error('当前未处于暂停状态，无法获取变量信息');
      }

      if (frameIndex < 0 || frameIndex >= this._callFrames.length) {
        throw new Error(`无效的调用栈帧索引: ${frameIndex}`);
      }

      const callFrame = this._callFrames[frameIndex];
      const variables = {};

      // 获取this值（带深度限制和错误处理）
      await this._getThisValue(variables, maxDepth);

      // 获取作用域链变量
      await this._getScopeChainVariables(variables, callFrame, maxDepth);

      // 获取函数参数
      await this._getFunctionArguments(variables, callFrame, maxDepth);

      // 获取调用栈信息
      await this._getCallStackInfo(variables, callFrame);

      return variables;
    } catch (error) {
      console.error('获取作用域变量失败:', error.message);
      throw error;
    }
  }

  /**
   * 获取this值
   * @private
   */
  async _getThisValue(variables, maxDepth) {
    try {
      // 限制深度，避免引用链过长
      const thisExpression = maxDepth > 0 ? 'this' : '"[Object]"';
      const thisResult = await this.connectionManager.execute('Runtime', 'evaluate', {
        expression: thisExpression,
        returnByValue: true,
        generatePreview: true
      });
      
      if (thisResult.result) {
        if (thisResult.result.value && typeof thisResult.result.value === 'object' && maxDepth > 0) {
          // 对于复杂对象，限制显示深度
          variables.this = this._formatComplexObject(thisResult.result.value, maxDepth - 1);
        } else {
          variables.this = thisResult.result.value;
        }
      } else {
        variables.this = 'undefined';
      }
    } catch (error) {
      variables.this = '无法获取: ' + this._getErrorDescription(error.message);
    }
  }

  /**
   * 获取作用域链变量
   * @private
   */
  async _getScopeChainVariables(variables, callFrame, maxDepth) {
    if (!callFrame.scopeChain || callFrame.scopeChain.length === 0) {
      variables.局部变量 = { note: '无作用域链信息' };
      variables.脚本作用域 = { note: '无作用域链信息' };
      variables.全局变量 = { note: '无作用域链信息' };
      return;
    }

    for (let scopeIndex = 0; scopeIndex < callFrame.scopeChain.length; scopeIndex++) {
      const scope = callFrame.scopeChain[scopeIndex];
      const scopeType = scope.type;
      const scopeName = this._getScopeTypeName(scopeType);
      
      if (scope.object && scope.object.objectId) {
        try {
          // 使用更兼容的方法获取作用域变量
          const scopeVariables = await this._getObjectPropertiesCompat(scope.object.objectId, maxDepth - 1);
          variables[scopeName] = scopeVariables;
        } catch (error) {
          variables[scopeName] = { error: '无法获取作用域变量: ' + this._getErrorDescription(error.message) };
        }
      } else {
        variables[scopeName] = { note: '作用域对象不可用' };
      }
    }
  }

  /**
   * 兼容方式获取对象属性
   * @private
   */
  async _getObjectPropertiesCompat(objectId, maxDepth) {
    try {
      // 尝试使用 Runtime.getObjectProperties
      if (await this._isCommandSupported('Runtime', 'getObjectProperties')) {
        const properties = await this.connectionManager.execute('Runtime', 'getObjectProperties', {
          objectId: objectId,
          ownProperties: true,
          generatePreview: true
        });
        
        if (properties && properties.result) {
          const result = {};
          for (const prop of properties.result) {
            if (prop.name) {
              result[prop.name] = await this._resolveVariableValue(prop, maxDepth);
            }
          }
          return result;
        }
      }
      
      // 回退方案：使用 Runtime.evaluate 获取对象属性
      return await this._getObjectPropertiesByEvaluate(objectId, maxDepth);
      
    } catch (error) {
      // 如果getObjectProperties失败，使用evaluate回退
      return await this._getObjectPropertiesByEvaluate(objectId, maxDepth);
    }
  }

  /**
   * 使用evaluate方式获取对象属性（兼容性方案）
   * @private
   */
  async _getObjectPropertiesByEvaluate(objectId, maxDepth) {
    try {
      // 获取对象描述和基本属性
      const descResult = await this.connectionManager.execute('Runtime', 'callFunctionOn', {
        objectId: objectId,
        functionDeclaration: `function() { 
          const result = {};
          result.__type = typeof this;
          result.__constructor = this.constructor ? this.constructor.name : 'Unknown';
          
          try {
            const keys = Object.keys(this).slice(0, 20);
            result.__keys = keys;
            result.__keyCount = keys.length;
          } catch (e) {
            result.__keys = [];
            result.__keyCount = 0;
            result.__error = "无法获取对象键: " + (e.message || "未知错误");
          }
          
          return result;
        }`,
        returnByValue: true
      });
      
      if (descResult.result && descResult.result.value) {
        const desc = descResult.result.value;
        const keys = desc.__keys || [];
        const result = {};
        
        if (desc.__type === 'object' && (desc.__constructor.includes('HTML') || desc.__constructor.includes('Element'))) {
          result.__note = `[DOM ${desc.__constructor}]`;
        }
        
        // 如果获取对象键时发生错误，添加错误信息
        if (desc.__error) {
          result.__error = desc.__error;
        }
        
        // 为每个属性单独处理，确保即使一个属性访问失败，其他属性仍然能被处理
        for (const key of keys) {
          try {
            if (key.startsWith('__') || key === 'constructor' || key === 'prototype') {
              continue;
            }
            
            const valueResult = await this.connectionManager.execute('Runtime', 'callFunctionOn', {
              objectId: objectId,
              functionDeclaration: `function() { 
                try {
                  const value = this["${key}"];
                  if (typeof value === "function") {
                    return {
                      type: "function",
                      name: value.name || "(匿名函数)",
                      length: value.length
                    };
                  }
                  if (value && typeof value === "object") {
                    if (value.constructor && value.constructor.name === "Object" && !Array.isArray(value)) {
                      const nestedKeys = Object.keys(value).slice(0, 10);
                      const nestedPreview = {};
                      
                      // 对每个嵌套属性进行错误处理
                      nestedKeys.forEach(nk => {
                        try {
                          const nestedValue = value[nk];
                          if (typeof nestedValue === "function") {
                            nestedPreview[nk] = "[Function]";
                          } else if (typeof nestedValue === "object" && nestedValue !== null) {
                            if (Array.isArray(nestedValue)) {
                              nestedPreview[nk] = "[Array(" + nestedValue.length + ")]";
                            } else {
                              nestedPreview[nk] = nestedValue;
                            }
                          } else {
                            nestedPreview[nk] = nestedValue;
                          }
                        } catch (e) {
                          nestedPreview[nk] = "[无法访问]";
                        }
                      });
                      
                      return {
                        type: typeof value,
                        constructor: value.constructor ? value.constructor.name : "Object",
                        isArray: Array.isArray(value),
                        length: value.length,
                        properties: nestedPreview
                      };
                    }
                    return {
                      type: typeof value,
                      constructor: value.constructor ? value.constructor.name : "Object",
                      isArray: Array.isArray(value),
                      length: value.length
                    };
                  }
                  return value;
                } catch (e) {
                  return "[无法访问]";
                }
              }`,
              returnByValue: true
            });
            
            if (valueResult.result && valueResult.result.value) {
              result[key] = valueResult.result.value;
            } else {
              result[key] = '[无法访问]';
            }
          } catch (e) {
            result[key] = '[获取失败]';
          }
        }
        
        if (desc.__keyCount > keys.length) {
          result[`...还有${desc.__keyCount - keys.length}个属性`] = '';
        }
        
        return result;
      }
      
      return { note: '无法获取对象属性列表' };
      
    } catch (error) {
      return { error: '无法获取作用域变量: ' + this._getErrorDescription(error.message) };
    }
  }

  /**
   * 获取函数参数
   * @private
   */
  async _getFunctionArguments(variables, callFrame, maxDepth) {
    try {
      // 首先尝试使用Debugger.getScopeVariables
      if (await this._isCommandSupported('Debugger', 'getScopeVariables')) {
        const callFrameId = callFrame.callFrameId;
        const scopeResult = await this.connectionManager.execute('Debugger', 'getScopeVariables', {
          callFrameId
        });
        
        if (scopeResult && scopeResult.variables) {
          const functionArgs = {};
          for (const arg of scopeResult.variables) {
            if (arg.name) {
              functionArgs[arg.name] = await this._resolveVariableValue(arg, maxDepth - 1);
            }
          }
          variables.函数参数 = functionArgs;
          return;
        }
      }
      
      // 回退方案：通过函数名和参数列表获取
      variables.函数参数 = { note: 'CDP版本不支持直接获取函数参数' };
      
    } catch (error) {
      variables.函数参数 = { note: 'CDP版本不支持直接获取函数参数' };
    }
  }

  /**
   * 获取调用栈信息
   * @private
   */
  async _getCallStackInfo(variables, callFrame) {
    try {
      // 使用与handlePaused相同的逻辑来处理callFrame
      // 提取location信息，优先从location对象获取
      const location = callFrame.location || {};
      
      // 获取scriptId，尝试多种来源
      const scriptId = location.scriptId || callFrame.scriptId;
      
      // 确定URL，尝试多种方式（与handlePaused相同的逻辑）
      let url = callFrame.url || location.url;
      
      // 如果没有URL但有scriptId，尝试获取脚本信息
      if (!url && scriptId) {
        url = `script:${scriptId}`;
        // 对于已知的HTML页面内联脚本，使用更友好的显示
        if (this._currentPageUrl && this._currentPageUrl.includes('demo-page.html')) {
          url = `${this._currentPageUrl} (内联脚本:${scriptId})`;
        }
      }
      
      // 确保有默认值
      if (!url) {
        url = this._currentPageUrl ? `${this._currentPageUrl} (内联脚本)` : 'unknown';
      }
      
      // 获取位置信息（与handlePaused相同的逻辑）
      const lineNumber = callFrame.lineNumber !== undefined ? callFrame.lineNumber : (location.lineNumber !== undefined ? location.lineNumber : 0);
      const columnNumber = callFrame.columnNumber !== undefined ? callFrame.columnNumber : (location.columnNumber !== undefined ? location.columnNumber : 0);
      
      // 确保functionName有默认值
      const functionName = callFrame.functionName || '(匿名函数)';
      
      const callInfo = {
        文件: url,
        行号: this._getSafeLineNumber(lineNumber),
        列号: this._getSafeLineNumber(columnNumber),
        函数名: functionName
      };
      
      variables.调用信息 = callInfo;
    } catch (error) {
      variables.调用信息 = { error: '无法获取调用信息: ' + this._getErrorDescription(error.message) };
    }
  }

  /**
   * 安全获取值，处理各种异常情况
   * @private
   */
  _getSafeValue(value, defaultValue) {
    if (value === null || value === undefined) {
      return defaultValue;
    }
    if (typeof value === 'string' && value.trim() === '') {
      return defaultValue;
    }
    return value;
  }

  /**
   * 安全获取行号，处理各种异常情况
   * @private
   */
  _getSafeLineNumber(lineNumber) {
    if (lineNumber === null || lineNumber === undefined || isNaN(lineNumber)) {
      return 'unknown';
    }
    
    // 确保是数字并转换为1基索引
    const numLine = parseInt(lineNumber, 10);
    if (isNaN(numLine)) {
      return 'unknown';
    }
    
    // 对于lineNumber，确保不为负数
    return Math.max(1, numLine + 1).toString();
  }

  /**
   * 检查CDP命令是否支持
   * @private
   */
  async _isCommandSupported(domain, method) {
    try {
      const client = this.connectionManager.getClient();
      return client && client[domain] && typeof client[domain][method] === 'function';
    } catch (error) {
      return false;
    }
  }

  /**
   * 获取错误描述
   * @private
   */
  _getErrorDescription(errorMessage) {
    if (errorMessage.includes('Object reference chain is too long')) {
      return '对象引用链过长';
    }
    if (errorMessage.includes('unsupported CDP command')) {
      return '不支持的CDP命令';
    }
    return errorMessage;
  }

  /**
   * 格式化复杂对象
   * @private
   */
  _formatComplexObject(obj, depth) {
    if (depth <= 0 || !obj || typeof obj !== 'object') {
      return '[Object]';
    }
    
    try {
      const keys = Object.keys(obj);
      if (keys.length === 0) {
        return '{}';
      }
      
      const preview = {};
      const maxKeys = Math.min(keys.length, 15); // 增加显示属性数量
      
      for (let i = 0; i < maxKeys; i++) {
        const key = keys[i];
        const value = obj[key];
        
        if (typeof value === 'object' && value !== null) {
          if (depth > 1) {
            preview[key] = this._formatComplexObject(value, depth - 1);
          } else {
            preview[key] = `[Object: ${value.constructor ? value.constructor.name : 'Unknown'}]`;
          }
        } else {
          preview[key] = value;
        }
      }
      
      if (keys.length > maxKeys) {
        preview[`...还有${keys.length - maxKeys}个属性`] = '';
      }
      
      return preview;
    } catch (error) {
      return '[Object: 格式化失败]';
    }
  }

  /**
   * 将变量信息导出到文本文件
   * @param {object} variables - 变量对象
   * @param {string} outputPath - 输出文件路径
   * @returns {Promise<string>} 实际输出的文件路径
   */
  async exportVariablesToFile(variables, outputPath = null) {
    const fs = require('fs');
    const path = require('path');
    
    // 确保variables文件夹存在
    const variablesDir = path.join(process.cwd(), 'variables');
    if (!fs.existsSync(variablesDir)) {
      fs.mkdirSync(variablesDir);
    }
    
    if (!outputPath) {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      outputPath = path.join(variablesDir, `variables-${timestamp}.txt`);
    }
    
    let content = `调试变量导出报告\n`;
    content += `==================\n`;
    content += `导出时间: ${new Date().toLocaleString()}\n`;
    content += `==================\n\n`;
    
    for (const [scopeName, scopeVars] of Object.entries(variables)) {
      content += `${scopeName}\n`;
      content += `${'='.repeat(scopeName.length)}\n`;
      
      if (scopeName === '调用信息') {
        for (const [key, value] of Object.entries(scopeVars)) {
          content += `${key}: ${value}\n`;
        }
      } else if (typeof scopeVars === 'object' && scopeVars !== null) {
        for (const [varName, varValue] of Object.entries(scopeVars)) {
          content += `${varName}: ${this._formatVariableDisplay(varValue, 0)}\n`;
        }
      } else {
        content += `${scopeVars}\n`;
      }
      
      content += '\n';
    }
    
    fs.writeFileSync(outputPath, content, 'utf8');
    console.log(`✅ 变量信息已导出到: ${outputPath}`);
    return outputPath;
  }

  /**
   * 格式化变量显示
   * @private
   * @param {*} value - 变量值
   * @param {number} indent - 缩进级别
   * @param {number} maxDepth - 最大递归深度
   * @returns {string} 格式化的字符串
   */
  _formatVariableDisplay(value, indent = 0, maxDepth = 4) {
    const indentStr = '  '.repeat(indent);
    const nextIndentStr = '  '.repeat(indent + 1);
    
    // 基本类型处理
    if (value === null) return 'null';
    if (value === undefined) return 'undefined';
    if (typeof value === 'string') {
      // 检查是否是字符串形式的对象引用
      if (value === '[Object]' || value.startsWith('[Object ') || value.startsWith('[Array(') || value.match(/^\[\w+\]$/)) {
        // 对于字符串形式的对象引用，直接返回，不添加额外的引号
        // 特别处理'[Object]'这种情况，尝试进一步展开
        return value;
      }
      return `"${value}"`;
    }
    if (typeof value === 'number' || typeof value === 'boolean') {
      return String(value);
    }
    if (typeof value === 'function') {
      return '[Function]';
    }
    
    // 对象类型处理
    if (typeof value === 'object') {
      // 检查递归深度
      if (maxDepth <= 0) {
        if (Array.isArray(value)) {
          return `[Array(${value.length})]`;
        } else {
          return `[${value.constructor ? value.constructor.name : 'Object'}]`;
        }
      }
      
      // 处理数组
      if (Array.isArray(value)) {
        if (value.length === 0) return '[]';
        
        let result = '[';
        const maxItems = 10; // 限制显示的数组项数量
        
        for (let i = 0; i < Math.min(value.length, maxItems); i++) {
          if (i === 0) result += '\n';
          result += `${nextIndentStr}${this._formatVariableDisplay(value[i], indent + 1, maxDepth - 1)}`;
          if (i < Math.min(value.length, maxItems) - 1) result += ',';
          result += '\n';
        }
        
        if (value.length > maxItems) {
          result += `${nextIndentStr}...还有${value.length - maxItems}个项\n`;
        }
        
        result += `${indentStr}]`;
        return result;
      }
      
      // 处理带有properties字段的特殊对象格式（通常来自CDP API）
      if (value.properties) {
        let result = `${value.constructor || value.type || 'Object'} {`;
        const keys = Object.keys(value.properties);
        
        for (let i = 0; i < Math.min(keys.length, 10); i++) {
          const key = keys[i];
          const propValue = value.properties[key];
          if (i === 0) result += '\n';
          
          // 递归格式化属性值，确保嵌套对象能够被正确展开
          let formattedValue;
          if (typeof propValue === 'object' && propValue !== null) {
            // 对于对象类型，继续递归格式化
            formattedValue = this._formatVariableDisplay(propValue, indent + 1, maxDepth - 1);
          } else if (typeof propValue === 'string') {
            // 对于字符串，检查是否是对象引用
            if (propValue.startsWith('[Object') || propValue.startsWith('[Array(') || propValue.match(/^\[\w+\]$/)) {
              formattedValue = propValue;
            } else {
              formattedValue = `"${propValue}"`;
            }
          } else {
            formattedValue = String(propValue);
          }
          
          result += `${nextIndentStr}${key}: ${formattedValue}`;
          if (i < Math.min(keys.length, 10) - 1) result += ',';
          result += '\n';
        }
        
        if (keys.length > 10) {
          result += `${nextIndentStr}...还有${keys.length - 10}个属性\n`;
        }
        
        result += `${indentStr}}`;
        return result;
      }
      
      // 处理带有type字段的特殊对象格式（通常来自CDP API）
      if (value.type) {
        // 如果有properties字段，优先使用properties字段进行详细展开
        if (value.properties) {
          // 已经在上面的代码中处理过，这里不再重复
        } else if (value.type === 'object') {
          if (value.description) {
            // 如果有preview，尝试展开preview内容
            if (value.preview && value.preview.properties) {
              let result = `Object {`;
              const maxProps = 10;
              for (let i = 0; i < Math.min(value.preview.properties.length, maxProps); i++) {
                const prop = value.preview.properties[i];
                if (i === 0) result += '\n';
                const formattedValue = this._formatVariableDisplay(prop.value, indent + 1, maxDepth - 1);
                result += `${nextIndentStr}${prop.name}: ${formattedValue}`;
                if (i < Math.min(value.preview.properties.length, maxProps) - 1) result += ',';
                result += '\n';
              }
              if (value.preview.properties.length > maxProps) {
                result += `${nextIndentStr}...还有${value.preview.properties.length - maxProps}个属性\n`;
              }
              result += `${indentStr}}`;
              return result;
            } else if (value.preview && value.preview.value) {
              return `[Object: ${value.description}] ${JSON.stringify(value.preview.value)}`;
            } else if (value.value) {
              // 如果有直接的value字段，使用它
              return this._formatVariableDisplay(value.value, indent, maxDepth);
            }
            // 对于没有preview的对象，尝试将其作为普通对象处理
            const objKeys = Object.keys(value);
            if (objKeys.length > 0 && objKeys.filter(key => !['type', 'description', 'constructor'].includes(key)).length > 0) {
              // 如果对象包含其他属性，将其作为普通对象处理
              const keys = objKeys.filter(key => !['type', 'description', 'constructor'].includes(key));
              let result = 'Object {';
              const maxProps = 10;
              for (let i = 0; i < Math.min(keys.length, maxProps); i++) {
                const key = keys[i];
                const val = value[key];
                if (i === 0) result += '\n';
                const formattedValue = this._formatVariableDisplay(val, indent + 1, maxDepth - 1);
                result += `${nextIndentStr}${key}: ${formattedValue}`;
                if (i < Math.min(keys.length, maxProps) - 1) result += ',';
                result += '\n';
              }
              if (keys.length > maxProps) {
                result += `${nextIndentStr}...还有${keys.length - maxProps}个属性\n`;
              }
              result += `${indentStr}}`;
              return result;
            }
            return `[Object: ${value.description}]`;
          }
        } else if (value.type === 'array') {
          if (value.items) {
            // 如果有items字段，展开数组内容
            let result = '[';
            const maxItems = 10;
            for (let i = 0; i < Math.min(value.items.length, maxItems); i++) {
              if (i === 0) result += '\n';
              result += `${nextIndentStr}${this._formatVariableDisplay(value.items[i], indent + 1, maxDepth - 1)}`;
              if (i < Math.min(value.items.length, maxItems) - 1) result += ',';
              result += '\n';
            }
            if (value.items.length > maxItems) {
              result += `${nextIndentStr}...还有${value.items.length - maxItems}个项\n`;
            }
            result += `${indentStr}]`;
            return result;
          }
          return `[Array(${value.preview || value.description || 'length unknown'})]`;
        } else if (value.type === 'string') {
          return `"${value.value}"`;
        } else if (value.type === 'number') {
          return String(value.value);
        } else if (value.type === 'boolean') {
          return String(value.value);
        }
      }
      
      // 处理带有__objectReference标记的对象
      if (value.__objectReference) {
        // 如果有value字段，使用它
        if (value.value && typeof value.value === 'object') {
          return this._formatVariableDisplay(value.value, indent, maxDepth);
        }
        return `[Object: ${value.constructor || 'Unknown'}]`;
      }
      
      // 处理普通对象
      // 首先检查是否有直接的properties字段
      if (value.properties) {
        let result = 'Object {';
        const maxProps = 10;
        const keys = Object.keys(value.properties);
        
        for (let i = 0; i < Math.min(keys.length, maxProps); i++) {
          const key = keys[i];
          const val = value.properties[key];
          if (i === 0) result += '\n';
          
          // 递归格式化属性值
          const formattedValue = this._formatVariableDisplay(val, indent + 1, maxDepth - 1);
          result += `${nextIndentStr}${key}: ${formattedValue}`;
          if (i < Math.min(keys.length, maxProps) - 1) result += ',';
          result += '\n';
        }
        
        if (keys.length > maxProps) {
          result += `${nextIndentStr}...还有${keys.length - maxProps}个属性\n`;
        }
        
        result += `${indentStr}}`;
        return result;
      }
      
      // 处理普通对象
      const keys = Object.keys(value);
      if (keys.length === 0) return '{}';
      
      let result = 'Object {';
      const maxProps = 10; // 限制显示的属性数量
      
      for (let i = 0; i < Math.min(keys.length, maxProps); i++) {
        const key = keys[i];
        const val = value[key];
        if (i === 0) result += '\n';
        
        // 递归格式化属性值
        const formattedValue = this._formatVariableDisplay(val, indent + 1, maxDepth - 1);
        result += `${nextIndentStr}${key}: ${formattedValue}`;
        if (i < Math.min(keys.length, maxProps) - 1) result += ',';
        result += '\n';
      }
      
      if (keys.length > maxProps) {
        result += `${nextIndentStr}...还有${keys.length - maxProps}个属性\n`;
      }
      
      result += `${indentStr}}`;
      return result;
    }
    
    // 其他类型直接转换为字符串
    return String(value);
  }

  /**
   * 解析变量值
   * @private
   * @param {object} property - 属性对象
   * @param {number} maxDepth - 最大递归深度
   * @returns {Promise<*>} 解析后的值
   */
  async _resolveVariableValue(property, maxDepth = 4) {
    if (maxDepth <= 0) {
      // 当深度达到限制时，返回对象引用而不是格式化字符串
      // 这样_formatVariableDisplay可以统一处理所有格式化
      if (property.objectId) {
        return { __objectReference: true, constructor: property.description || 'Object' };
      }
      // 检查property本身是否包含properties字段
      if (property && typeof property === 'object' && property.properties) {
        return property.properties;
      }
      return property.value || property.description || '[Object]';
    }
    
    try {
      // 检查property本身是否包含properties字段（直接从_getObjectPropertiesByEvaluate返回的对象）
      if (property && typeof property === 'object' && property.properties) {
        return property.properties;
      }
      
      if (property.value) {
        // 如果有直接的值，检查它是否包含properties字段
        const value = property.value;
        if (value && typeof value === 'object' && value.properties) {
          // 如果是带有properties字段的特殊对象格式，返回properties内容
          return value.properties;
        }
        // 如果没有properties字段，返回值本身
        return value;
      }
      
      if (property.objectId) {
        try {
          // 尝试使用 Runtime.getObjectProperties
          if (await this._isCommandSupported('Runtime', 'getObjectProperties')) {
            const properties = await this.connectionManager.execute('Runtime', 'getObjectProperties', {
              objectId: property.objectId,
              ownProperties: true,
              generatePreview: true
            });
            
            if (properties && properties.result && properties.result.length > 0) {
              const nestedProps = {};
              for (const prop of properties.result.slice(0, 10)) { // 限制嵌套属性数量
                if (prop.name) {
                  // 递归解析属性值，但不进行格式化
                  nestedProps[prop.name] = await this._resolveVariableValue(prop, maxDepth - 1);
                }
              }
              return nestedProps;
            }
          }
        } catch (error) {
          // Runtime.getObjectProperties 失败，回退到使用 callFunctionOn
          console.debug(`[DEBUG] Runtime.getObjectProperties 失败，回退到使用 callFunctionOn: ${error.message}`);
        }
        
        // 使用 callFunctionOn 作为回退方案 - 返回完整的对象结构以便_formatVariableDisplay可以递归展开
        try {
          const result = await this.connectionManager.execute('Runtime', 'callFunctionOn', {
            objectId: property.objectId,
            functionDeclaration: 'function() {\n' +
              '  // 直接返回对象的属性，不进行深度限制的字符串转换\n' +
              '  const result = {};\n' +
              '  const keys = Object.keys(this).slice(0, 10);\n' +
              '  keys.forEach(key => {\n' +
              '    try {\n' +
              '      const value = this[key];\n' +
              '      // 对于基本类型，直接返回值\n' +
              '      if (value === null || typeof value !== "object" || typeof value === "function") {\n' +
              '        result[key] = value;\n' +
              '      } else if (Array.isArray(value)) {\n' +
              '        // 对于数组，返回其元素的基本类型或对象引用\n' +
              '        result[key] = value.slice(0, 10).map(item => {\n' +
              '          if (item === null || typeof item !== "object" || typeof item === "function") {\n' +
              '            return item;\n' +
              '          } else {\n' +
              '            // 返回对象的引用信息，由_formatVariableDisplay处理展开\n' +
              '            return { __objectReference: true, constructor: item.constructor ? item.constructor.name : "Object", value: item };\n' +
              '          }\n' +
              '        });\n' +
              '      } else {\n' +
              '        // 对于普通对象，返回其属性\n' +
              '        const nestedProps = {};\n' +
              '        const nestedKeys = Object.keys(value).slice(0, 10);\n' +
              '        nestedKeys.forEach(nk => {\n' +
              '          try {\n' +
              '            const nestedValue = value[nk];\n' +
              '            if (nestedValue === null || typeof nestedValue !== "object" || typeof nestedValue === "function") {\n' +
              '              nestedProps[nk] = nestedValue;\n' +
              '            } else {\n' +
              '              // 返回对象的引用信息，由_formatVariableDisplay处理展开\n' +
              '              nestedProps[nk] = { __objectReference: true, constructor: nestedValue.constructor ? nestedValue.constructor.name : "Object" };\n' +
              '            }\n' +
              '          } catch (e) {\n' +
              '            nestedProps[nk] = "[无法访问]";\n' +
              '          }\n' +
              '        });\n' +
              '        if (Object.keys(value).length > 10) {\n' +
              '          nestedProps[`...还有${Object.keys(value).length - 10}个属性`] = "";\n' +
              '        }\n' +
              '        result[key] = nestedProps;\n' +
              '      }\n' +
              '    } catch (e) {\n' +
              '      result[key] = "[无法访问]";\n' +
              '    }\n' +
              '  });\n' +
              '  if (Object.keys(this).length > 10) {\n' +
              '    result[`...还有${Object.keys(this).length - 10}个属性`] = "";\n' +
              '  }\n' +
              '  return result;\n' +
              '}',
            returnByValue: true
          });
          
          if (result.result && result.result.value) {
            return result.result.value;
          }
        } catch (error) {
          console.debug(`[DEBUG] callFunctionOn 回退也失败: ${error.message}`);
        }
      }
      
      // 如果没有objectId和value，返回描述信息
      return property.description || '[值不可访问]';
    } catch (error) {
      return `[解析错误: ${error.message}]`;
    }
  }

  /**
   * 获取作用域类型名称
   * @private
   * @param {string} scopeType - 作用域类型
   * @returns {string} 作用域名称
   */
  _getScopeTypeName(scopeType) {
    const typeNames = {
      'local': '局部变量',
      'closure': '闭包变量',
      'script': '脚本作用域',
      'global': '全局变量',
      'with': 'with作用域',
      'catch': 'catch作用域'
    };
    
    return typeNames[scopeType] || `作用域(${scopeType})`;
  }

  /**
   * 获取所有网络请求
   * @returns {Promise<Array>} 网络请求列表
   */
  async getAllNetworkRequests() {
    return Array.from(this._networkRequests.values());
  }

  /**
   * 获取指定ID的网络请求详情
   * @param {string} requestId - 请求ID
   * @returns {Promise<Object|null>} 网络请求详情或null
   */
  async getNetworkRequestDetails(requestId) {
    return this._networkRequests.get(requestId) || null;
  }
}

module.exports = Debugger;