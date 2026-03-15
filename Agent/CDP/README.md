# CDP 命令行工具使用文档

## 工具简介

CDP（Chrome DevTools Protocol）命令行工具是一个基于 Chrome DevTools Protocol 的命令行工具，允许开发者通过命令行与浏览器交互，查看网页文件和进行代码调试。

## 安装方法

```bash
# 克隆仓库
cd c:\Users\lenovo\Desktop\项目\CDP

# 安装依赖
npm install

# 启动 Chrome 浏览器并开启远程调试
chrome --remote-debugging-port=9222

& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222

Start-Process -FilePath C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe -ArgumentList '--remote-debugging-port=9222', 'D:\Projects\debug_tool\web_app\test1\demo-page.html' 

Start-Process -FilePath C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe -ArgumentList '--remote-debugging-port=9222', 'C:\Users\lenovo\Desktop\项目\CDP\examples\demo-page.html'

Start-Process -FilePath "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList "--remote-debugging-port=9222", "C:\Users\14590\Desktop\Dagent\WebPage\index.html"
```

## 全局参数

```bash
cdp --help
```

| 参数 | 别名 | 描述 | 默认值 |
|------|------|------|--------|
| --version | -V | 输出版本号 | - |
| --help | -h | 显示帮助信息 | - |
| --host <host> | -h | Chrome 调试主机 | localhost |
| --port <port> | -p | Chrome 调试端口 | 9222 |
| --target <target> | -t | 目标页面的 URL 或标题 | - |

## 命令详解

### 1. dir 命令

显示当前连接页面的资源目录结构。

```bash
cdp dir
```

**选项**：
| 参数 | 别名 | 描述 |
|------|------|------|
| --type <type> | -t | 按类型筛选资源 (script, stylesheet, image等) |
| --scripts | -s | 仅显示脚本资源 |
| --flat | -f | 使用扁平化列表显示，而不是树状结构 |

**示例**：
```bash
# 查看当前页面资源的目录结构
cdp dir

# 仅显示脚本资源
cdp dir --scripts

# 按类型筛选资源
cdp dir --type script

# 扁平化显示所有资源
cdp dir --flat
```

### 2. view 命令

查看指定文件的代码内容。

```bash
cdp view <url> [options]
```

**参数**：
- `<url>`：要查看的文件的 URL

**选项**：
| 参数 | 别名 | 描述 |
|------|------|------|
| --lines <number> | -l | 查看前 N 行代码 |
| --start <line> | -s | 开始行号 |
| --end <line> | -e | 结束行号 |
| --range <range> | -r | 行范围，格式为 "开始行-结束行" |
| --type <type> | -t | 文件类型 (script, stylesheet) |
| --grep <term> | -g | 搜索关键词 |
| --breakpoints | -b | 显示断点位置和虚拟行号，或使用虚拟行号来指定行范围 |

**示例**：
```bash
# 查看完整文件
cdp view file:///c:/path/to/file.js

# 查看文件的前 20 行
cdp view file:///c:/path/to/file.js -l 20

# 查看文件的 5-15 行
cdp view file:///c:/path/to/file.js -s 5 -e 15

# 使用虚拟行号查看文件的 1-10 行
cdp view --breakpoints --range 1-10 file:///c:/path/to/file.js

# 搜索关键词
cdp view file:///c:/path/to/file.js -g "function"

# 查看带虚拟行号的代码（用于设置断点）
cdp view file:///c:/path/to/file.js -b
```

### 3. breakpoint 命令

断点管理命令，用于设置、移除和列出断点。

#### 3.1 set 子命令

在指定文件的指定行设置断点。

```bash
cdp breakpoint set <url> <line> [options]
```

**参数**：
- `<url>`：要设置断点的文件的 URL
- `<line>`：行号（可以是虚拟行号，需要配合 -b/--breakpoints 参数）

**选项**：
| 参数 | 别名 | 描述 |
|------|------|------|
| --condition <condition> | -c | 设置条件表达式 |
| --ignore <count> | -i | 设置忽略次数 |
| --breakpoints | -b | 行号是基于格式化代码的行号（与 view --virtual 显示的虚拟行号对应） |

**示例**：
```bash
# 在指定行设置断点
cdp breakpoint set file:///c:/path/to/file.js 10

# 设置条件断点
cdp breakpoint set file:///c:/path/to/file.js 10 --condition "x > 10"

# 使用虚拟行号设置断点
cdp view file:///c:/path/to/file.js -b
# 记录虚拟行号后设置断点
cdp breakpoint set file:///c:/path/to/file.js 5 -b
```

#### 3.2 remove 子命令

移除指定 ID 的断点。

```bash
cdp breakpoint remove <id>
```

**参数**：
- `<id>`：要移除的断点 ID

**示例**：
```bash
cdp breakpoint remove breakpoint-1
```

#### 3.3 list 子命令

列出所有已设置的断点。

```bash
cdp breakpoint list
```

**示例**：
```bash
cdp breakpoint list
```

#### 3.4 clear 子命令

清除所有已设置的断点。

```bash
cdp breakpoint clear
```

**示例**：
```bash
cdp breakpoint clear
```

## 交互式调试命令

当断点被触发或使用 `breakpoint set` 命令设置断点后，程序会进入交互式调试模式，此时可以使用以下命令：

| 命令 | 别名 | 描述 |
|------|------|------|
| continue | c | 继续执行代码，直到遇到下一个断点 |
| next | n | 执行下一行代码（单步跳过） |
| step | s | 执行下一行代码（单步进入函数） |
| out | o | 从当前函数中跳出（单步跳出） |
| quit | q | 退出调试模式 |
| eval <expression> | e | 在当前执行上下文中执行表达式 |
| breakpoints | bps | 列出所有断点 |
| break/b/create <file> <line> | - | 添加新断点 |
| remove <id> | - | 删除指定断点 |
| clear | - | 清除所有断点 |
| help | h | 显示帮助信息 |

## 使用示例

### 1. 查看文件内容并设置断点

```bash
# 1. 查看带虚拟行号的文件内容
cdp view file:///c:/Users/lenovo/Desktop/项目/CDP/test-fibonacci.js -b

# 输出示例
1|function fibonacci(n) {
2|  if (n <= 1) {
3|    return n;
4|  }
5|  return fibonacci(n - 1) + fibonacci(n - 2);
6|}
7|
8|// 计算并打印斐波那契数列
9|console.log('计算斐波那契数列:');
10|for (let i = 0; i < 10; i++) {
11|  const result = fibonacci(i);
12|  console.log(`fibonacci(${i}) = ${result}`);
13|}
14|
15|console.log('计算完成！');

# 2. 使用虚拟行号设置断点（第 5 行）
cdp breakpoint set file:///c:/Users/lenovo/Desktop/项目/CDP/test-fibonacci.js 5 -b
```

### 2. 调试斐波那契数列

```bash
# 1. 创建测试文件 test-fibonacci.js（见示例文件）

# 2. 在浏览器中打开该文件（通过本地服务器）

# 3. 查看带虚拟行号的代码
cdp view http://localhost:3000/test-fibonacci.js -b

# 4. 设置断点
cdp breakpoint set http://localhost:3000/test-fibonacci.js 5 -b

# 5. 在交互式调试模式中使用命令
> next
> continue
> eval i
> eval result
```

## 常见问题

### Q: 为什么使用虚拟行号设置断点后程序没有中断？
A: 确保您在 `breakpoint set` 命令中使用了 `-b/--breakpoints` 参数，该参数告诉工具您使用的是虚拟行号。

### Q: 如何查看所有断点？
A: 在交互式调试模式中使用 `breakpoints` 或 `b` 命令可以列出所有断点。

### Q: 如何退出交互式调试模式？
A: 使用 `quit` 或 `q` 命令可以退出调试模式。

### Q: 如何在条件满足时才中断代码执行？
A: 使用 `--condition` 参数设置条件表达式，例如：
```bash
cdp breakpoint set file:///c:/path/to/file.js 10 --condition "x > 10"
```

## 更新日志

### v1.0.0
- 初始版本
- 支持 dir、view、breakpoint 命令
- 支持虚拟行号断点调试
- 提供交互式调试界面

## 注意事项

1. 使用前请确保 Chrome 浏览器已启动并开启远程调试模式
2. 虚拟行号断点需要配合 `view -b` 和 `breakpoint set -b` 命令使用
3. 调试时请确保目标文件已被浏览器加载
4. Windows 系统中本地文件路径需要使用 `file:///` 前缀