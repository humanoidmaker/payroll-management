from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import init_db
from app.api import auth, settings as settings_api

@asynccontextmanager
async def lifespan(a):
    await init_db()
    yield

app = FastAPI(title="PayRoll Pro API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(settings_api.router)

@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "PayRoll Pro"}

@app.get("/api/stats")
async def stats():
    from app.core.database import get_db as gdb
    db = await gdb()
    counts = {}
    for coll in await db.list_collection_names():
        if coll != "system.indexes":
            counts[f"total_{coll}"] = await db[coll].count_documents({})
    return {"stats": counts}
