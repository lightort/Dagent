在执行程序前，先执行打开浏览器的命令行命令：

```bash
Start-Process -FilePath <chrome浏览器路径> -ArgumentList "--remote-debugging-port=9222", "--remote-allow-origins=*", <你想测试的html文件路径>
```

例如：
```bash
Start-Process -FilePath "C:\Users\lenovo\AppData\Local\Google\Chrome\Application\chrome.exe" -ArgumentList "--remote-debugging-port=9222", "--remote-allow-origins=*", "D:\Projects\Dagent\Agent\ybs\1.html"
```

打开浏览器后，先完成你想测试的操作的前置性步骤。
比如你想测试登录的运行路径，那你要先讲账号密码验证码输入完毕，确保下一次你的操作是点击“登录”

此时：你执行 python main.py
系统会提示你进行操作（比如点击“登录”按钮）

操作完毕，会在code_path_trace.txt文件中记录下操作的运行路径。
与此同时，会在可疑代码附近打上断点。

要设置的参数：

main.py：   --description <你想定位信息的描述>
            --cdp_path <CDP工具路径>