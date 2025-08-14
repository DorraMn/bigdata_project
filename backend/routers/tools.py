from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
import logging
import importlib
import docker

router = APIRouter(prefix="/tools", tags=["tools"])

# Mapping entre le nom d'un outil et sa classe d'installateur correspondante
TOOLS = {
    "spark": "SparkInstaller",
    "mongodb": "MongoDBInstaller",
    "hbase": "HBaseInstaller"
}

# Configuration du logger
logger = logging.getLogger("installer_logger")
logging.basicConfig(level=logging.INFO)

def dummy_progress(p: int):
    """Callback de progression pour logging."""
    logger.info(f"Progression : {p}%")


# ------------------- MODELS -------------------

class ToolConfig(BaseModel):
    container_name: str
    username: str | None = None
    password: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    volume: str | None = None

class ToolUpdateConfig(BaseModel):
    container_name: str
    port: int = Field(..., ge=1, le=65535)
    config: dict

class MongoToolConfig(BaseModel):
    container_name: str


# ------------------- ROUTES -------------------

@router.post("/{tool_name}/start")
def start_tool(tool_name: str, config: ToolConfig = Body(...)):
    """
    Démarre un outil donné avec la configuration fournie.
    Importe dynamiquement l'installateur correspondant.
    """
    if tool_name not in TOOLS:
        raise HTTPException(status_code=404, detail="Outil non supporté")
    try:
        module = importlib.import_module(f"backend.installers.{tool_name}_installer")
        installer_class = getattr(module, TOOLS[tool_name])
        installer = installer_class(config=config.dict(), progress_callback=dummy_progress, logger=logger)

        installer.check_prerequisites()
        installer.install()

        if not installer.test_installation():
            installer.rollback()
            raise HTTPException(status_code=500, detail="Test d'installation échoué.")

        return {"status": "started", "tool": tool_name}

    except Exception as e:
        logger.error(f"Erreur installation {tool_name} : {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{tool_name}/stop")
def stop_tool(tool_name: str, config: ToolConfig = Body(...)):
    """
    Arrête un outil donné en effectuant un rollback via l'installateur.
    """
    if tool_name not in TOOLS:
        raise HTTPException(status_code=404, detail="Outil non supporté")
    try:
        module = importlib.import_module(f"backend.installers.{tool_name}_installer")
        installer_class = getattr(module, TOOLS[tool_name])
        installer = installer_class(config=config.dict(), progress_callback=dummy_progress, logger=logger)

        installer.rollback()

        return {"status": "stopped", "tool": tool_name}

    except Exception as e:
        logger.error(f"Erreur arrêt {tool_name} : {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/containers")
def list_all_containers():
    """
    Retourne la liste de tous les conteneurs Docker (avec détails).
    """
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True)

        result = []
        for c in containers:
            try:
                image_tag = c.image.tags[0] if c.image.tags else "untagged"
            except Exception as ex:
                logger.warning(f"Erreur récupération image du conteneur {c.name}: {ex}")
                image_tag = "unknown_error"
            result.append({
                "id": c.id,
                "name": c.name,
                "status": c.status,
                "image": image_tag,
                "ports": c.attrs.get("NetworkSettings", {}).get("Ports", {}),
            })

        return {"containers": result}

    except Exception as e:
        logger.error(f"Erreur récupération des conteneurs Docker : {e}")
        raise HTTPException(status_code=500, detail="Impossible de récupérer les conteneurs Docker.")


# ------------- SPARK --------------

@router.post("/spark/config")
def get_spark_config(config: ToolConfig = Body(...)):
    """
    Retourne la configuration actuelle de Spark.
    """
    try:
        from backend.installers.spark_installer import SparkInstaller
        installer = SparkInstaller(config=config.dict(), progress_callback=dummy_progress, logger=logger)
        return installer.get_configuration()
    except Exception as e:
        logger.error(f"Erreur récupération config Spark : {e}")
        raise HTTPException(status_code=500, detail="Impossible d'extraire la configuration Spark.")


@router.post("/spark/update-config")
def update_spark_config(update: ToolUpdateConfig):
    """
    Met à jour la configuration Spark et redémarre le conteneur avec cette nouvelle config.
    """
    try:
        from backend.installers.spark_installer import SparkInstaller
        installer = SparkInstaller(
            config={"container_name": update.container_name, "port": update.port},
            progress_callback=dummy_progress,
            logger=logger
        )
        installer.restart_with_new_config(update.config)

        if not installer.test_installation():
            raise HTTPException(status_code=500, detail="Redémarrage Spark échoué.")

        return {"status": "updated", "tool": "spark"}

    except Exception as e:
        logger.error(f"Erreur mise à jour Spark : {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ------------- HBASE --------------

@router.post("/hbase/config")
def get_hbase_config(config: ToolConfig = Body(...)):
    """
    Retourne la configuration actuelle de HBase.
    """
    try:
        from backend.installers.hbase_installer import HBaseInstaller
        installer = HBaseInstaller(config=config.dict(), progress_callback=dummy_progress, logger=logger)
        return installer.get_configuration()
    except Exception as e:
        logger.error(f"Erreur récupération config HBase : {e}")
        raise HTTPException(status_code=500, detail="Impossible d'extraire la configuration HBase.")


@router.post("/hbase/update-config")
def update_hbase_config(update: ToolUpdateConfig):
    """
    Met à jour la configuration HBase et redémarre le conteneur.
    """
    try:
        from backend.installers.hbase_installer import HBaseInstaller
        installer = HBaseInstaller(
            config={"container_name": update.container_name, "port": update.port},
            progress_callback=dummy_progress,
            logger=logger
        )
        installer.restart_with_new_config(update.config)

        if not installer.test_installation():
            raise HTTPException(status_code=500, detail="Redémarrage HBase échoué.")

        return {"status": "updated", "tool": "hbase"}

    except Exception as e:
        logger.error(f"Erreur mise à jour HBase : {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ------------- MONGODB --------------

@router.post("/mongodb/config")
def get_mongodb_config(config: MongoToolConfig = Body(...)):
    """
    Retourne les informations détaillées d'un conteneur MongoDB donné.
    """
    client = docker.from_env()
    try:
        container = client.containers.get(config.container_name)
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail=f"Conteneur '{config.container_name}' non trouvé")
    except Exception as e:
        logger.error(f"Erreur récupération conteneur MongoDB : {e}")
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération du conteneur")

    container_info = {
        "id": container.id,
        "name": container.name,
        "status": container.status,
        "image": container.image.tags[0] if container.image.tags else "untagged",
        "ports": container.attrs.get("NetworkSettings", {}).get("Ports", {}),
        "env": {},
    }
    env_list = container.attrs.get("Config", {}).get("Env", [])
    for env_var in env_list:
        if '=' in env_var:
            k, v = env_var.split('=', 1)
            container_info["env"][k] = v

    return container_info


@router.post("/mongodb/update-config")
def update_mongodb_config(update: ToolUpdateConfig):
    """
    Met à jour la configuration MongoDB et redémarre le conteneur.
    """
    try:
        from backend.installers.mongodb_installer import MongoDBInstaller
        installer = MongoDBInstaller(
            config={"container_name": update.container_name, "port": update.port},
            progress_callback=dummy_progress,
            logger=logger
        )
        installer.update_config(update.config)  # <-- Changement ici

        if not installer.test_installation():
            raise HTTPException(status_code=500, detail="Redémarrage MongoDB échoué.")

        return {"status": "updated", "tool": "mongodb"}

    except Exception as e:
        logger.error(f"Erreur mise à jour MongoDB : {e}")
        raise HTTPException(status_code=500, detail=str(e))
