import platform
import subprocess
from typing import Tuple

def detect_os() -> str:
    system = platform.system().lower()
    if 'linux' in system:
        return 'linux'
    if 'darwin' in system:
        return 'mac'
    if 'windows' in system:
        return 'windows'
    return 'unknown'

def run_command(cmd: str, logger: any) -> Tuple[int, str]:
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    output = ""
    for line in proc.stdout:
        output += line
        logger.info(line.strip())
    code = proc.wait()
    return code, output
