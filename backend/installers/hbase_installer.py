from .base import BaseInstaller
from .utils import run_command
import socket
import json
import time
import re
import docker

def extraire_json_sortie(stdout: str):
    match = re.search(r'\{[\s\S]*?\}', stdout)
    if match:
        return json.loads(match.group())
    raise ValueError("Aucun bloc JSON valide trouvé dans la sortie.")

class HBaseInstaller(BaseInstaller):
    def check_prerequisites(self) -> None:
        code, _ = run_command("docker --version", self.logger)
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

        cmd = (
            f"docker run -d --name {container_name} "
            f"-e HBASE_USER={username} -e HBASE_PASSWORD={password} "
            f"-p {requested_port}:16010 custom-hbase master"
        )

        self.logger.info(f"Commande Docker exécutée : {cmd}")
        code, output = run_command(cmd, self.logger)
        if code != 0:
            self.logger.error(f"Erreur Docker : {output}")
            raise RuntimeError("Échec du lancement du conteneur HBase.")

        self.logger.info(f"Conteneur HBase lancé sur le port {requested_port}.")
        self.progress(100)

    def test_installation(self) -> bool:
        container_name = self.config.get("container_name", "hbase_container")
        code, output = run_command(
            f'docker ps --filter "name={container_name}" --filter "status=running" --format "{{{{.Names}}}}"',
            self.logger
        )
        return code == 0 and container_name in output

    def rollback(self) -> None:
        container_name = self.config.get("container_name", "hbase_container")
        run_command(f"docker rm -f {container_name}", self.logger)
        self.logger.info(f"Conteneur {container_name} supprimé.")

    def wait_for_removal(self, container_name: str, timeout: int = 10):
        for _ in range(timeout * 2):
            code, output = run_command(
                f"docker ps -a --filter name={container_name} --format '{{{{.ID}}}}'", self.logger
            )
            if code == 0 and not output.strip():
                return
            time.sleep(0.5)
        raise RuntimeError(f"{container_name} n'a pas été supprimé après {timeout}s.")

    def wait_until_ready(self, container_name: str, timeout: int = 20):
        self.logger.info(f"Attente initialisation complète de {container_name}...")
        for _ in range(timeout * 2):
            code, _ = run_command(f'docker exec {container_name} ls /hbase-2.1.3', self.logger)
            if code == 0:
                return
            time.sleep(0.5)
        raise RuntimeError(f"{container_name} n'est pas prêt après {timeout} secondes.")

    def restart_with_new_config(self, new_config: dict):
        self.logger.info("Redémarrage HBase avec nouvelle configuration : %s", new_config)
        container_name = self.config.get("container_name", "hbase_container")
        port = self.config.get("port", 16010)

        run_command(f"docker stop {container_name}", self.logger)
        run_command(f"docker rm {container_name}", self.logger)
        self.wait_for_removal(container_name)

        env_args = " ".join([f"-e {key}={value}" for key, value in new_config.items()])
        run_cmd_str = (
            f'docker run -d --name {container_name} '
            f'{env_args} '
            f'-p {port}:16010 custom-hbase master'
        )

        code, output = run_command(run_cmd_str, self.logger)
        if code != 0:
            self.logger.error(f"Erreur redémarrage HBase : {output}")
            raise RuntimeError("Erreur redémarrage conteneur HBase.")

        self.wait_until_ready(container_name)

        if not self.test_installation():
            raise RuntimeError("HBase non fonctionnel après redémarrage.")

    def get_configuration(self, container_name: str) -> dict:
        try:
            client = docker.from_env()
            container = client.containers.get(container_name)

            exec_result = container.exec_run("python3 /hbase-2.1.3/get_hbase_config_dynamic.py")
            if exec_result.exit_code != 0:
                raise RuntimeError("Erreur lors de l'exécution du script dans le conteneur.")

            output = exec_result.output.decode("utf-8")
            return json.loads(output)

        except Exception as e:
            raise RuntimeError(f"Erreur lors de la récupération de la configuration HBase : {str(e)}")
