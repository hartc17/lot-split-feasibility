import pathlib

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.feasibility import router as feasibility_router
from app.api.routes.parse import router as parse_router

_STATIC_DIR = pathlib.Path(__file__).parent.parent / "static"

app = FastAPI(
    title="Lot Split Feasibility API",
    version="0.3.0",
    description="Determine whether a residential parcel can be subdivided and how many lots it yields.",
)

app.include_router(parse_router, prefix="/v1/parse")
app.include_router(feasibility_router, prefix="/v1/feasibility")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "0.3.0"}


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


# Serve CSS, JS, and other static assets at /static/*
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
