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
            cwd=cwd
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode != 0:
            return f"[error]\n{stderr or stdout or 'command failed'}"

        if stdout:
            return stdout

        if stderr:
            return f"[stderr]\n{stderr}"

        return "[no output]"

    except Exception as e:
        return f"[error] {e}"


def workspace_scanner(workspace_root: str, mode: str = "flat") -> str:
    target_dir = workspace_root

    if not os.path.isdir(target_dir):
        return f"[error] Directory does not exist: {target_dir}"

    if mode in {"flat", "scripts"}:
        cmd = f"node ./CDP/bin/cli.js dir --{mode}"
    else:
        cmd = "node ./CDP/bin/cli.js dir --flat"

    return run_cdp_command(cmd, cwd=target_dir)


if __name__ == "__main__":
    test_dir = os.path.join(os.getcwd(), "CDP")
    print(workspace_scanner(test_dir, mode="flat"))


