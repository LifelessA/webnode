# scratch/git_status.py
import subprocess
import os

def check_git():
    cwd = r"c:\Users\lifel\Downloads\framework"
    print("Checking git status in", cwd)
    try:
        # Run git status directly without shell to avoid powershell lookup issues
        res = subprocess.run(["git", "status"], cwd=cwd, capture_output=True, text=True, check=False)
        print("STDOUT:")
        print(res.stdout)
        print("STDERR:")
        print(res.stderr)
        print("Exit Code:", res.returncode)
    except Exception as e:
        print("Error running git:", e)

if __name__ == "__main__":
    check_git()
