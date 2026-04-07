from fastapi import APIRouter, Depends, HTTPException
from app.core.database import get_db
from app.utils.auth import hash_password, verify_password, create_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register")
async def register(data: dict, db=Depends(get_db)):
    if await db.users.find_one({"email": data["email"]}):
        raise HTTPException(400, "Email exists")
    r = await db.users.insert_one({"email": data["email"], "password_hash": hash_password(data["password"]), "name": data.get("name", ""), "role": data.get("role", "user"), "is_active": True})
    return {"success": True, "user_id": str(r.inserted_id)}

@router.post("/login")
async def login(data: dict, db=Depends(get_db)):
    user = await db.users.find_one({"email": data["email"]})
    if not user or not verify_password(data["password"], user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    return {"success": True, "token": create_token(str(user["_id"]), user.get("role", "user")), "user": {"id": str(user["_id"]), "email": user["email"], "name": user.get("name", ""), "role": user.get("role", "user")}}

@router.get("/me")
async def me(user=Depends(get_current_user)):
    return {"success": True, "user": {"id": user["id"], "email": user["email"], "name": user.get("name", ""), "role": user.get("role", "user")}}
