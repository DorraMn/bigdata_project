from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
import logging
import importlib
import docker

router = APIRouter()

# ==================== CONFIGURATION ====================

# Mapping outil -> classe d'installateur
TOOLS = {
    "spark": "SparkInstaller",
    "mongodb": "MongoDBInstaller",
    "hbase": "HBaseInstaller"
}

# Logger global
logger = logging.getLogger("installer_logger")
logging.basicConfig(level=logging.INFO)

# Callback de progression
def dummy_progress(p: int):
    logger.info(f"Progression : {p}%")


# ==================== SCHÉMAS Pydantic ====================

class ToolConfig(BaseModel):
    container_name: str
    username: str
    password: str
    port: int | None = Field(default=None, ge=1, le=65535)
    volume: str | None = None

class ToolUpdateConfig(BaseModel):
    container_name: str
    port: int = Field(ge=1, le=65535)
    config: dict


# ==================== ROUTES GÉNÉRIQUES ====================

@router.post("/tools/{tool_name}/start")
def start_tool(tool_name: str, config: ToolConfig = Body(...)):
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


@router.post("/tools/{tool_name}/stop")
def stop_tool(tool_name: str, config: ToolConfig = Body(...)):
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


@router.get("/tools/containers")
def list_all_containers():
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True, filters={"label": "created_by=mon_app"})

        result = []
        for c in containers:
            try:
                image_tag = c.image.tags[0] if c.image.tags else "untagged"
            except docker.errors.ImageNotFound:
                image_tag = "image_not_found"
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


# ==================== SPARK ====================

@router.post("/tools/spark/config")
def get_spark_config(config: ToolConfig = Body(...)):
    try:
        from backend.installers.spark_installer import SparkInstaller
        installer = SparkInstaller(config=config.dict(), progress_callback=dummy_progress, logger=logger)
        return installer.get_configuration()

    except Exception as e:
        logger.error(f"Erreur récupération config Spark : {e}")
        raise HTTPException(status_code=500, detail="Impossible d'extraire la configuration Spark.")


@router.post("/tools/spark/update-config")
def update_spark_config(update: ToolUpdateConfig):
    try:
        from backend.installers.spark_installer import SparkInstaller
        logger.info(f"Redémarrage Spark avec config : {update.config}")

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


# ==================== HBASE ====================

@router.post("/tools/hbase/config")
def get_hbase_config(config: ToolConfig = Body(...)):
    try:
        from backend.installers.hbase_installer import HBaseInstaller
        installer = HBaseInstaller(config=config.dict(), progress_callback=dummy_progress, logger=logger)
        return installer.get_configuration(config.container_name)

    except Exception as e:
        logger.error(f"Erreur récupération config HBase : {e}")
        raise HTTPException(status_code=500, detail="Impossible d'extraire la configuration HBase.")


@router.post("/tools/hbase/update-config")
def update_hbase_config(update: ToolUpdateConfig):
    try:
        from backend.installers.hbase_installer import HBaseInstaller
        logger.info(f"Redémarrage HBase avec config : {update.config}")

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
