from .base import BaseInstaller
from .utils import run_command, run_docker_command
import socket
import json
import time
import re
import os
import platform


def extraire_json_sortie(stdout: str):
    """Tente d'extraire un bloc JSON depuis une sortie qui pourrait contenir d'autres logs."""
    match = re.search(r'\{[\s\S]*?\}', stdout)
    if match:
        return json.loads(match.group())
    raise ValueError("Aucun bloc JSON valide trouvé dans la sortie.")


def get_volume_path(container_name: str) -> str:
    """Retourne un chemin de volume compatible multiplateforme pour Docker."""
    base_dir = os.path.join(".", "data")
    full_path = os.path.abspath(os.path.join(base_dir, container_name))
    os.makedirs(full_path, exist_ok=True)

    if platform.system() == "Windows":
        return full_path.replace("\\", "/")
    return full_path


class HBaseInstaller(BaseInstaller):
    def check_prerequisites(self) -> None:
        code, _ = run_docker_command("--version", self.logger)
        if code != 0:
            raise RuntimeError("Docker n'est pas installé ou non disponible dans le PATH.")
        self.logger.info("Docker est disponible.")
        self.progress(10)

    def is_port_in_use(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    def find_available_port(self, start=16000, end=16100) -> int:
        for port in range(start, end):
            if not self.is_port_in_use(port):
                return port
        raise RuntimeError("Aucun port disponible trouvé pour HBase.")

    def install(self) -> None:
        container_name = self.config.get("container_name", "hbase_container")
        username = self.config.get("username", "admin")
        password = self.config.get("password", "password")
        requested_port = self.config.get("port", 16010)

        if not isinstance(requested_port, int) or requested_port <= 0:
            raise RuntimeError(f"Port invalide fourni : {requested_port}")

        if self.is_port_in_use(requested_port):
            self.logger.warning(f"Port {requested_port} utilisé. Recherche d’un port libre...")
            requested_port = self.find_available_port()
            self.logger.info(f"Port libre trouvé : {requested_port}")
            self.config["port"] = requested_port

        image_name = "custom-hbase"
        volume_path = get_volume_path(container_name)

        self.logger.info("Lancement du conteneur HBase...")
        run_cmd_str = (
            f"run -d "
            f"--name {container_name} "
            f"--label myapp=mon_interface "
            f"--label created_by=mon_app "
            f"-e HBASE_USER={username} "
            f"-e HBASE_PASSWORD={password} "
            f"-p {requested_port}:16010 "
            f"-v {volume_path}:/hbase-2.1.3/workspace "
            f"{image_name} master"
        )

        code, output = run_docker_command(run_cmd_str, self.logger)
        if code != 0:
            self.logger.error(f"Erreur Docker : {output}")
            raise RuntimeError("Échec du lancement du conteneur HBase.")

        self.logger.info(f"Conteneur HBase lancé sur le port {requested_port}.")
        self.progress(100)

    def test_installation(self) -> bool:
        container_name = self.config.get("container_name", "hbase_container")
        code, output = run_docker_command(
            f'ps --filter "name={container_name}" --filter "status=running" --format "{{{{.Names}}}}"',
            self.logger
        )
        return code == 0 and container_name in output

    def rollback(self) -> None:
        container_name = self.config.get("container_name", "hbase_container")
        run_docker_command(f"rm -f {container_name}", self.logger)
        self.logger.info(f"Conteneur {container_name} supprimé.")

    def wait_for_removal(self, container_name: str, timeout: int = 10):
        for _ in range(timeout * 2):
            code, output = run_docker_command(
                f"ps -a --filter name={container_name} --format '{{{{.ID}}}}'", self.logger
            )
            if code == 0 and not output.strip():
                return
            time.sleep(0.5)
        raise RuntimeError(f"{container_name} n'a pas été supprimé après {timeout}s.")

    def wait_until_ready(self, container_name: str, timeout: int = 20):
        self.logger.info(f"Attente initialisation complète de {container_name}...")
        for _ in range(timeout * 2):
            code, _ = run_docker_command(f"exec {container_name} ls /hbase-2.1.3", self.logger)
            if code == 0:
                return
            time.sleep(0.5)
        raise RuntimeError(f"{container_name} n'est pas prêt après {timeout} secondes.")

    def restart_with_new_config(self, new_config: dict):
        container_name = self.config.get("container_name", "hbase_container")
        port = self.config.get("port", 16010)
        image_name = "custom-hbase"
        volume_path = get_volume_path(container_name)

        self.logger.info("Redémarrage HBase avec nouvelle configuration...")

        run_docker_command(f"stop {container_name}", self.logger)
        run_docker_command(f"rm {container_name}", self.logger)
        self.wait_for_removal(container_name)

        env_args = " ".join([f"-e {key}={value}" for key, value in new_config.items()])
        run_cmd_str = (
            f'run -d '
            f'--name {container_name} '
            f'--label myapp=mon_interface '
            f'-p {port}:16010 '
            f'-v {volume_path}:/hbase-2.1.3/workspace '
            f'{env_args} '
            f'{image_name} master'
        )

        code, output = run_docker_command(run_cmd_str, self.logger)
        if code != 0:
            self.logger.error(f"Erreur redémarrage HBase : {output}")
            raise RuntimeError("Erreur redémarrage conteneur HBase.")

        self.wait_until_ready(container_name)

        if not self.test_installation():
            raise RuntimeError("HBase non fonctionnel après redémarrage.")

    def get_configuration(self):
        container_name = self.config.get("container_name", "hbase_container")

        docker_cmd = (
            f'exec {container_name} bash -c '
            f'"python3 /hbase-2.1.3/get_hbase_config_dynamic.py"'
        )

        self.logger.info("Extraction configuration HBase...")
        code, output = run_docker_command(docker_cmd, self.logger)
        if code != 0:
            raise RuntimeError("Erreur lors de la récupération de la configuration.")

        try:
            return extraire_json_sortie(output)
        except Exception as e:
            self.logger.error(f"Erreur JSON : {e} — Sortie brute : {output}")
            raise RuntimeError("Impossible d'analyser la configuration JSON.")
