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
    """
    Exécute une commande shell, loggue chaque ligne et capture toutes les sorties.
    Retourne (code de sortie, sortie complète).
    """
    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        output = ""
        for line in proc.stdout:
            output += line
            logger.info(line.strip())

        code = proc.wait()
        if code != 0:
            logger.error(f"Commande échouée avec le code {code}")
        else:
            logger.debug(f"Commande exécutée avec succès.")

        return code, output.strip()

    except Exception as e:
        error_msg = f"Erreur lors de l'exécution de la commande : {e}"
        logger.exception(error_msg)
        return 1, error_msg
