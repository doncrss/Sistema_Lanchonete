from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routes.admin import router as admin_router
from app.routes.catalog import router as catalog_router
from app.routes.health import router as health_router
from app.routes.orders import router as orders_router
from app.services.setup_service import initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Lanchotech", description="API de cardápio, pedidos e gestão.", version="2.0.0", lifespan=lifespan)
app.include_router(health_router)
app.include_router(catalog_router)
app.include_router(orders_router)
app.include_router(admin_router)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(FRONTEND_DIR / "minimal.html")

app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

@app.get("/styles.css", include_in_schema=False)
def styles():
    return FileResponse(FRONTEND_DIR / "styles.css")

@app.get("/minimal.js", include_in_schema=False)
def script():
    return FileResponse(FRONTEND_DIR / "minimal.js")
