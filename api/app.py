from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import runs, swarms, system, tests

FRONTEND_DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"


def create_app() -> FastAPI:
    app = FastAPI(title="sims")

    @app.get("/api/health")
    def read_health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(tests.router)
    app.include_router(runs.router)
    app.include_router(swarms.router)
    app.include_router(system.router)

    if FRONTEND_DIST_DIR.exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST_DIR / "assets"))

        # The frontend routes its own paths, so a reload on /tests/<id> must
        # still get index.html.
        @app.get("/{path:path}", include_in_schema=False)
        def serve_frontend(path: str) -> FileResponse:
            if path.startswith("api/"):
                raise HTTPException(status_code=404)
            return FileResponse(FRONTEND_DIST_DIR / "index.html")

    return app


app = create_app()
