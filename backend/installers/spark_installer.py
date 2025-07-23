from .base import BaseInstaller
from .utils import run_command
import json
import socket
import re
import time
import os


def extraire_json_sortie(stdout: str):
    """Tente d'extraire un bloc JSON depuis une sortie qui pourrait contenir d'autres logs."""
    match = re.search(r'\{[\s\S]*?\}', stdout)
    if match:
        return json.loads(match.group())
    raise ValueError("Aucun bloc JSON valide trouvé dans la sortie.")


class SparkInstaller(BaseInstaller):

    def check_prerequisites(self) -> None:
        code, _ = run_command("docker --version", self.logger)
        if code != 0:
            raise RuntimeError("Docker n'est pas installé ou disponible dans le PATH.")
        self.logger.info("Docker est installé.")
        self.progress(10)

    def is_port_in_use(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    def find_available_port(self, start=8000, end=9000) -> int:
        for port in range(start, end):
            if not self.is_port_in_use(port):
                return port
        raise RuntimeError("Aucun port libre entre 8000 et 9000.")

    def install(self) -> None:
        container_name = self.config.get("container_name", "spark_container")
        username = self.config.get("username", "admin")
        password = self.config.get("password", "password")
        requested_port = self.config.get("port", 8080)

        if not isinstance(requested_port, int) or requested_port <= 0:
            raise RuntimeError("Port invalide.")

        if self.is_port_in_use(requested_port):
            self.logger.warning(f"Port {requested_port} déjà utilisé. Recherche d’un port libre...")
            requested_port = self.find_available_port()
            self.config["port"] = requested_port

        image_name = "custom-spark-image"
        dockerfile_path = "./backend/docker/spark"
        volume_path = os.path.abspath(f"./data/{container_name}")
        os.makedirs(volume_path, exist_ok=True)

        self.logger.info("Construction de l'image Docker Spark...")
        build_cmd = f"docker build -t {image_name} {dockerfile_path}"
        code, output = run_command(build_cmd, self.logger)
        if code != 0:
            raise RuntimeError(f"Échec du build Docker : {output}")

        self.logger.info("Lancement du conteneur Spark...")
        run_cmd_str = (
            f"docker run -d "
            f"--name {container_name} "
            f"--label myapp=mon_interface "
            f"--label created_by=mon_app " 
            f"-e SPARK_USER={username} "
            f"-e SPARK_PASSWORD={password} "
            f"-e HOME=/home/sparkuser "
            f"-p {requested_port}:8080 "
            f"-v {volume_path}:/opt/bitnami/spark/workspace "
            f"{image_name}"
        )


        code, output = run_command(run_cmd_str, self.logger)
        if code != 0:
            raise RuntimeError(f"Erreur lancement conteneur : {output}")

        self.logger.info(f"Conteneur Spark démarré sur le port {requested_port}.")
        self.progress(100)

    def test_installation(self) -> bool:
        container_name = self.config.get("container_name", "spark_container")
        self.logger.info(f"Vérification du conteneur Spark : {container_name}")
        code, output = run_command(
            f'docker ps --filter "name={container_name}" --filter "status=running"',
            self.logger
        )
        return code == 0 and container_name in output

    def rollback(self) -> None:
        container_name = self.config.get("container_name", "spark_container")
        self.logger.info(f"Rollback : suppression de {container_name}")
        run_command(f"docker rm -f {container_name}", self.logger)

    def wait_for_removal(self, container_name: str, timeout: int = 10):
        for _ in range(timeout * 2):
            code, output = run_command(
                f"docker ps -a --filter name={container_name} --format '{{{{.ID}}}}'", self.logger
            )
            if code == 0 and not output.strip():
                return
            time.sleep(0.5)
        raise RuntimeError(f"{container_name} non supprimé après {timeout} secondes.")

    def wait_until_ready(self, container_name: str, timeout: int = 20):
        self.logger.info(f"Attente de l'état prêt de {container_name}...")
        for _ in range(timeout * 2):
            code, _ = run_command(
                f'docker exec {container_name} ls /opt/bitnami/spark', self.logger
            )
            if code == 0:
                return
            time.sleep(0.5)
        raise RuntimeError(f"{container_name} non prêt après {timeout} secondes.")

    def get_configuration(self):
        container_name = self.config.get("container_name", "spark_container")

        docker_cmd = (
            f'docker exec {container_name} bash -c '
            f'"HOME=/home/sparkuser /opt/bitnami/spark/bin/spark-submit /opt/bitnami/spark/get_spark_config.py"'
        )

        self.logger.info("Extraction configuration Spark...")
        code, output = run_command(docker_cmd, self.logger)
        if code != 0:
            raise RuntimeError("Erreur lors de la récupération de la configuration.")

        try:
            return extraire_json_sortie(output)
        except Exception as e:
            self.logger.error(f"Erreur JSON : {e} — Sortie brute : {output}")
            raise RuntimeError("Impossible d'analyser la configuration JSON.")

    def restart_with_new_config(self, new_config: dict):
        container_name = self.config.get("container_name", "spark_container")
        port = self.config.get("port", 8080)
        image_name = "custom-spark-image"
        volume_path = os.path.abspath(f"./data/{container_name}")
        os.makedirs(volume_path, exist_ok=True)

        self.logger.info("Redémarrage du conteneur Spark...")

        run_command(f"docker stop {container_name}", self.logger)
        run_command(f"docker rm {container_name}", self.logger)
        self.wait_for_removal(container_name)

        config_args = " ".join([f"{k}={v}" for k, v in new_config.items()])

        run_cmd_str = (
            f'docker run -d '
            f'--name {container_name} '
            f'--label myapp=mon_interface '
            f'-e HOME=/home/sparkuser '
            f'-p {port}:8080 '
            f'-v {volume_path}:/opt/bitnami/spark/workspace '
            f'{image_name} '
            f'bash -c "/opt/bitnami/spark/bin/spark-submit '
            f'/opt/bitnami/spark/get_spark_config.py {config_args} && tail -f /dev/null"'
        )

        code, output = run_command(run_cmd_str, self.logger)
        if code != 0:
            raise RuntimeError("Redémarrage échoué : " + output)

        self.wait_until_ready(container_name)

        if not self.test_installation():
            raise RuntimeError("Le conteneur n'est pas fonctionnel après redémarrage.")
