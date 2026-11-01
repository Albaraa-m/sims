from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.routes import tests

FRONTEND_DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"


def create_app() -> FastAPI:
    app = FastAPI(title="sims")

    @app.get("/api/health")
    def read_health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(tests.router)

    if FRONTEND_DIST_DIR.exists():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST_DIR, html=True))
    return app


app = create_app()
