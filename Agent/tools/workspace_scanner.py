import subprocess
import os

def run_cdp_command(command: str, cwd: str = None) -> str:
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            cwd=cwd          # 指定工作目录
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if stderr:
            return f"[stderr]\n{stderr}"
        if not stdout:
            return "[no output]"
        return stdout

    except Exception as e:
        return f"[error] {e}"

def workspace_scanner(mode="flat"):
    # 指定目标工作目录（注意使用原始字符串或双反斜杠）
    target_dir = os.path.join(os.getcwd(), "CDP")
    # 确保目录存在（可选）
    if not os.path.isdir(target_dir):
        return f"[error] Directory does not exist: {target_dir}"

    if mode == "flat" or mode == "scripts":
        cmd = "node bin/cli.js dir --" + mode
        return run_cdp_command(cmd, cwd=target_dir)
    else:
        return run_cdp_command("node bin/cli.js dir --flat", cwd=target_dir)

if __name__ == "__main__":
    print(workspace_scanner())