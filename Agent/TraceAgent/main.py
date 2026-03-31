from static_code_analyzer import static_code_analyzer
from code_path_tracker import test_code_path_tracker
import subprocess
import os

def main():
    description = '这是一段登录的加密代码，会将用户名15924231565加密成token:04d635d2ccea813cf9f7645cbd974dcb4a797edc21894e9be2d948f1b033574a104027da8b9e94a0c7dd025801e64a02f2a5c89b76c10cb031d724cd38f7316af6dde84bda0b6ad7226d98ebd12be31408ccee3bede2de61b130f4ab15255213eae113373ad015f489aece2b，将密码13819912565加密成token:0436679559170009c0c7a7702fae527b0498ce64f6da4011ac39281f4ffeb616aaff3ad42d21b0eca88999fd2dbfe49a0a0390391eb66fe101337d92aa2048e5687ee90c59c81f6da16034aa53713d040ced7f9f58c35cb0922d036a356a2559f9de88ed0d657e4ffe0ef4aceb6f8cb9d3952a40248ef5d1e8c971b2add815c9a13bcba575ea752445ecf0534ab2ca846ef52bc96a80a5696ff93de2555a7831cc'

    cdp_path = r"D:\Projects\Dagent\Agent\CDP"

    '''
    chrome_path = r"D:\Projects\debug_tool\CDP\chrome-win64\chrome.exe"
    url_path = r"https://yngwypt.zmnyjk.com/#/"
    args = [
        "--remote-debugging-port=9222",
        "--remote-allow-origins=*",
        url_path
    ]

    process = subprocess.Popen([chrome_path] + args)
    '''      

    test_code_path_tracker()
    token_functions = static_code_analyzer(description)
    print(token_functions)
    
    subprocess.run(
        ["node", "bin/cli.js", "breakpoint", "clear"],
        cwd=cdp_path,
        check=True
    )
    for key in token_functions.keys():
        subprocess.run(
            ["node", "bin/cli.js", "breakpoint-seq", key],
            cwd=cdp_path,
            check=True
        )

if __name__ == "__main__":
    main()
