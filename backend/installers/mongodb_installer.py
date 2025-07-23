from .base import BaseInstaller
from .utils import run_command
import time

class MongoDBInstaller(BaseInstaller):

    def check_prerequisites(self) -> None:
        code, _ = run_command("docker --version", self.logger)
        if code != 0:
            raise RuntimeError("Docker n'est pas installé. Veuillez l’installer d’abord.")
        self.logger.info("Docker est disponible.")
        self.progress(10)

    def install(self) -> None:
        container = self.config.get("container_name", "mongodb_docker")
        username = self.config.get("username", "admin")
        password = self.config.get("password", "password")
        port = self.config.get("port", 27017)
        volume = self.config.get("volume")

        self.logger.info(f"Lancement de MongoDB avec : container={container}, port={port}, user={username}, volume={volume or 'non spécifié'}")

        # Pull de l’image MongoDB
        code, output = run_command("docker pull mongo", self.logger)
        if code != 0:
            self.logger.error(f"Échec du téléchargement de l’image MongoDB : {output}")
            raise RuntimeError("Échec du téléchargement de l’image MongoDB.")
        self.progress(40)

        # Construction de la commande Docker
        docker_cmd = (
            f"docker run -d --name {container} "
            f"-p {port}:27017 "
            f"-e MONGO_INITDB_ROOT_USERNAME={username} "
            f"-e MONGO_INITDB_ROOT_PASSWORD={password} "
        )

        if volume:
            docker_cmd += f"-v {volume}:/data/db "

        docker_cmd += "mongo"

        self.logger.info(f"Commande Docker : {docker_cmd}")

        # Lancement du conteneur
        code, output = run_command(docker_cmd, self.logger)
        if code != 0:
            self.logger.error(f"Erreur au démarrage de MongoDB : {output}")
            raise RuntimeError("Échec du lancement de MongoDB en conteneur.")

        self.logger.info("Conteneur MongoDB lancé avec succès.")
        self.progress(100)

    def test_installation(self) -> bool:
        container = self.config.get("container_name", "mongodb_docker")
        self.logger.info(f"Vérification du conteneur MongoDB '{container}'...")

        for _ in range(5):
            code, output = run_command(
                f'docker ps --filter "name={container}" --filter "status=running" --format "{{{{.Names}}}}"',
                self.logger
            )
            if code == 0 and container in output:
                self.logger.info("Conteneur MongoDB actif.")
                return True
            time.sleep(2)

        self.logger.warning("Conteneur MongoDB non trouvé ou non actif.")
        return False

    def rollback(self) -> None:
        container = self.config.get("container_name", "mongodb_docker")
        self.logger.info(f"Rollback en cours pour le conteneur MongoDB : {container}")
        run_command(f"docker rm -f {container}", self.logger)
        self.logger.info(f"Rollback MongoDB terminé pour {container}.")
