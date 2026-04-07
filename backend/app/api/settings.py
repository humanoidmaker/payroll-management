from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.utils.auth import require_admin

router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.get("/")
async def get_all(db=Depends(get_db)):
    docs = await db.settings.find().to_list(100)
    return {"success": True, "settings": {d["key"]: d["value"] for d in docs}}

@router.put("/")
async def update(data: dict, user=Depends(require_admin), db=Depends(get_db)):
    for k, v in data.items():
        await db.settings.update_one({"key": k}, {"$set": {"value": v}}, upsert=True)
    return {"success": True}
