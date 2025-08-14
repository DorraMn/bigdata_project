# backend/docker/mongodb/get_mongodb_config.py

import sys
import json
import docker

args = sys.argv[1:]
config = {}

for arg in args:
    if '=' in arg:
        key, val = arg.split('=', 1)
        config[key] = val

container_name = config.get("container_name")
if not container_name:
    print(json.dumps({"error": "container_name argument required"}))
    sys.exit(1)

client = docker.from_env()

try:
    container = client.containers.get(container_name)
except docker.errors.NotFound:
    print(json.dumps({"error": f"Conteneur '{container_name}' non trouvé"}))
    sys.exit(1)

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

print(json.dumps(container_info))
