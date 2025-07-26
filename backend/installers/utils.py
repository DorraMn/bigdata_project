import platform
import subprocess
import shutil
import logging
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

def get_docker_command() -> str:
    """
    Retourne le chemin complet vers la commande docker, ou lève une erreur si non trouvée.
    """
    docker_cmd = shutil.which("docker")
    if docker_cmd is None:
        raise RuntimeError("Docker n'est pas installé ou 'docker' n'est pas dans le PATH.")
    return docker_cmd

def run_command(cmd: str, logger: logging.Logger) -> Tuple[int, str]:
    """
    Exécute une commande shell, loggue chaque ligne et capture toutes les sorties.
    Retourne (code de sortie, sortie complète).
    """
    try:
        logger.debug(f"Exécution de la commande : {cmd}")
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
            logger.debug("Commande exécutée avec succès.")

        return code, output.strip()

    except Exception as e:
        error_msg = f"Erreur lors de l'exécution de la commande : {e}"
        logger.exception(error_msg)
        return 1, error_msg

def run_docker_command(args: str, logger: logging.Logger) -> Tuple[int, str]:
    """
    Exécute une commande Docker en utilisant le chemin absolu de docker détecté.
    'args' est la partie après 'docker', par exemple 'ps -a'.
    """
    try:
        docker_cmd = get_docker_command()
        # Pour Windows, les guillemets dans shell=True peuvent poser problème, donc on adapte :
        if detect_os() == 'windows':
            full_cmd = f'{docker_cmd} {args}'
        else:
            full_cmd = f'"{docker_cmd}" {args}'
        logger.debug(f"Commande Docker construite : {full_cmd}")
        return run_command(full_cmd, logger)
    except Exception as e:
        logger.error(f"Erreur exécution commande Docker : {e}")
        return 1, str(e)
