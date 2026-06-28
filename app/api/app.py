from fastapi import FastAPI

from app.api.routes.feasibility import router as feasibility_router
from app.api.routes.parse import router as parse_router

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
