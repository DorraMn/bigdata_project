import os
import platform
import socket
import time
import json
import re
from .base import BaseInstaller
from .utils import run_command, run_docker_command


def extraire_json_sortie(stdout: str):
    """
    Extrait un bloc JSON valide de la sortie standard donnée.
    """
    match = re.search(r'\{[\s\S]*?\}', stdout)
    if match:
        return json.loads(match.group())
    raise ValueError("Aucun bloc JSON valide trouvé dans la sortie.")


def get_volume_path(container_name: str) -> str:
    """
    Retourne le chemin absolu du volume pour Docker, en adaptant le format selon l'OS.
    """
    base_dir = os.path.join(".", "data")
    full_path = os.path.abspath(os.path.join(base_dir, container_name))
    os.makedirs(full_path, exist_ok=True)
    if platform.system() == "Windows":
        return full_path.replace("\\", "/")
    return full_path


class HBaseInstaller(BaseInstaller):

    def check_prerequisites(self):
        code, _ = run_docker_command("--version", self.logger)
        if code != 0:
            raise RuntimeError("Docker n'est pas installé ou disponible.")
        self.logger.info("Docker est installé.")
        self.progress(10)

    def is_port_in_use(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    def find_available_port(self, start=16010, end=17000) -> int:
        for port in range(start, end):
            if not self.is_port_in_use(port):
                return port
        raise RuntimeError("Aucun port libre trouvé entre 16010 et 17000.")

    def install(self):
        container_name = self.config.get("container_name", "hbase_container")
        requested_port_master = self.config.get("master_port", 16010)
        requested_port_rs = self.config.get("regionserver_port", 16020)
        requested_port_zk = self.config.get("zookeeper_port", 2181)

        # Vérification des ports et recherche d'alternatives si occupés
        if self.is_port_in_use(requested_port_master):
            self.logger.warning(f"Port master {requested_port_master} occupé, recherche d’un autre...")
            requested_port_master = self.find_available_port()
            self.config["master_port"] = requested_port_master
        if self.is_port_in_use(requested_port_rs):
            self.logger.warning(f"Port regionserver {requested_port_rs} occupé, recherche d’un autre...")
            requested_port_rs = self.find_available_port(start=16020)
            self.config["regionserver_port"] = requested_port_rs
        if self.is_port_in_use(requested_port_zk):
            self.logger.warning(f"Port zookeeper {requested_port_zk} occupé, recherche d’un autre...")
            requested_port_zk = self.find_available_port(start=2181, end=2300)
            self.config["zookeeper_port"] = requested_port_zk

        image_name = "custom-hbase-image"
        dockerfile_path = "./backend/docker/hbase"
        volume_path = get_volume_path(container_name)

        self.logger.info("Construction de l'image Docker HBase...")
        build_cmd = f"docker build -t {image_name} {dockerfile_path}"
        code, output = run_command(build_cmd, self.logger)
        if code != 0:
            raise RuntimeError(f"Échec du build Docker : {output}")

        self.logger.info("Lancement du conteneur HBase...")
        run_cmd_str = (
            f"run -d "
            f"--name {container_name} "
            f"--label myapp=mon_interface "
            f"--label created_by=mon_app "
            f"-p {requested_port_master}:16010 "
            f"-p {requested_port_rs}:16020 "
            f"-p {requested_port_zk}:2181 "
            f"-v {volume_path}:/opt/hbase-2.1.3/data "
            f"{image_name}"
        )
        code, output = run_docker_command(run_cmd_str, self.logger)
        if code != 0:
            raise RuntimeError(f"Erreur lancement conteneur : {output}")

        self.logger.info(f"Conteneur HBase démarré sur les ports: master={requested_port_master}, rs={requested_port_rs}, zk={requested_port_zk}.")
        self.progress(100)

    def test_installation(self) -> bool:
        container_name = self.config.get("container_name", "hbase_container")
        self.logger.info(f"Vérification du conteneur HBase : {container_name}")
        code, output = run_docker_command(
            f'ps --filter "name={container_name}" --filter "status=running"',
            self.logger
        )
        return code == 0 and container_name in output

    def rollback(self):
        container_name = self.config.get("container_name", "hbase_container")
        self.logger.info(f"Rollback : suppression de {container_name}")
        run_docker_command(f"rm -f {container_name}", self.logger)

    def wait_for_removal(self, container_name: str, timeout: int = 10):
        for _ in range(timeout * 2):
            code, output = run_docker_command(
                f"ps -a --filter name={container_name} --format '{{{{.ID}}}}'", self.logger
            )
            if code == 0 and not output.strip():
                return
            time.sleep(0.5)
        raise RuntimeError(f"{container_name} non supprimé après {timeout} secondes.")

    def wait_until_ready(self, container_name: str, timeout: int = 20):
        self.logger.info(f"Attente que {container_name} soit prêt...")
        for _ in range(timeout * 2):
            code, _ = run_docker_command(
                f"exec {container_name} ls /opt/hbase-2.1.3", self.logger
            )
            if code == 0:
                return
            time.sleep(0.5)
        raise RuntimeError(f"{container_name} non prêt après {timeout} secondes.")

    def get_configuration(self):
        container_name = self.config.get("container_name", "hbase_container")
        docker_cmd = (
            f'exec {container_name} bash -c '
            f'"HOME=/home/hbaseuser python3 /opt/hbase-2.1.3/get_hbase_config_dynamic.py"'
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

    def restart_with_new_config(self, new_config: dict):
        container_name = self.config.get("container_name", "hbase_container")
        master_port = self.config.get("master_port", 16010)
        regionserver_port = self.config.get("regionserver_port", 16020)
        zk_port = self.config.get("zookeeper_port", 2181)
        image_name = "custom-hbase-image"
        volume_path = get_volume_path(container_name)

        self.logger.info("Redémarrage du conteneur HBase...")

        run_docker_command(f"stop {container_name}", self.logger)
        run_docker_command(f"rm {container_name}", self.logger)
        self.wait_for_removal(container_name)

        # Construire la chaîne d'arguments pour le script Python
        config_args = " ".join([f"{k}={v}" for k, v in new_config.items()])

        run_cmd_str = (
            f'run -d '
            f'--name {container_name} '
            f'--label myapp=mon_interface '
            f'-p {master_port}:16010 '
            f'-p {regionserver_port}:16020 '
            f'-p {zk_port}:2181 '
            f'-v {volume_path}:/opt/hbase-2.1.3/data '
            f'{image_name} '
            f'bash -c "HOME=/home/hbaseuser python3 /opt/hbase-2.1.3/get_hbase_config_dynamic.py {config_args} && tail -f /dev/null"'
        )

        code, output = run_docker_command(run_cmd_str, self.logger)
        if code != 0:
            raise RuntimeError("Redémarrage échoué : " + output)

        self.wait_until_ready(container_name)

        if not self.test_installation():
            raise RuntimeError("Le conteneur n'est pas fonctionnel après redémarrage.")
