/**
 * 目录查看命令
 * 用于查看页面资源的目录结构
 */

class DirCommand {
  /**
   * 构造函数
   * @param {Object} fileSystem - 文件系统模块实例
   */
  constructor(fileSystem) {
    this.fileSystem = fileSystem;
  }
  
  /**
   * 注册命令
   * @param {Object} program - Commander实例
   */
  register(program) {
    program
      .command('dir')
      .description('查看页面资源的目录结构')
      .option('-t, --type <type>', '按类型筛选资源 (script, stylesheet, image等)')
      .option('-s, --scripts', '仅显示脚本资源')
      .option('-f, --flat', '使用扁平化列表显示，而不是树状结构')
      .action(async (options) => {
        try {
          if (options.scripts) {
            // 仅显示脚本资源
            const scripts = await this.fileSystem.getScripts();
            console.log('脚本资源列表:');
            scripts.forEach((script, index) => {
              console.log(`${index + 1}. ${script.url}`);
            });
            console.log(`\n共找到 ${scripts.length} 个脚本资源`);
          } else if (options.type) {
            // 按类型筛选
            const resources = await this.fileSystem.getResourcesByType(options.type);
            console.log(`${options.type} 类型资源列表:`);
            resources.forEach((resource, index) => {
              console.log(`${index + 1}. ${resource.url}`);
            });
            console.log(`\n共找到 ${resources.length} 个${options.type}类型资源`);
          } else if (options.flat) {
            // 扁平化显示所有资源
            const resources = await this.fileSystem.getResources();
            console.log('所有资源列表:');
            resources.forEach((resource, index) => {
              console.log(`${index + 1}. ${resource.url} (${resource.type || 'unknown'})`);
            });
            console.log(`\n共找到 ${resources.length} 个资源`);
          } else {
            // 树状结构显示目录
            console.log('页面资源目录结构:');
            const structure = await this.fileSystem.listDirectoryStructure();
            const formatted = this.fileSystem.formatDirectoryStructure(structure);
            console.log(formatted || '未找到资源');
          }
        } catch (error) {
          console.error('查看目录失败:', error.message);
          process.exit(1);
        }
        
        // 命令完成后退出程序
        process.exit(0);
      });
  }
}

module.exports = DirCommand;