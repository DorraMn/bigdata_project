from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from backend.routers import tools
from fastapi.middleware.cors import CORSMiddleware
import os
import docker

app = FastAPI()
app.include_router(tools.router)

# Configuration CORS pour permettre les requêtes depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Remplace par les origines spécifiques si nécessaire
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from the frontend directory
frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# Serve index.html at root
@app.get("/")
def read_index():
    return FileResponse(os.path.join(frontend_path, "index.html"))

@app.get("/tools/containers")
def list_containers(created_by: str = None):
    client = docker.from_env()
    containers = client.containers.list(all=True)
    result = []
    for c in containers:
        # Optionally filter by label or name
        if created_by:
            if not c.name or created_by not in c.name:
                continue
        ports = c.attrs.get('NetworkSettings', {}).get('Ports', {})
        result.append({
            "name": c.name,
            "image": c.image.tags[0] if c.image.tags else c.image.short_id,
            "status": c.status,
            "ports": ports
        })
    return JSONResponse({"containers": result})