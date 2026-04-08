from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from bson import ObjectId
from datetime import datetime, timezone, timedelta
from app.core.database import get_db
from app.utils.auth import hash_password, verify_password, create_token, decode_token, get_current_user, require_admin
import random, string, secrets

router = APIRouter(prefix="/api/auth", tags=["auth"])

def generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))

def get_email_service(db):
    """Create email service from DB settings. Returns None if SMTP not configured."""
    import asyncio
    async def _get():
        settings_docs = await db.settings.find().to_list(100)
        s = {d["key"]: d["value"] for d in settings_docs}
        host = s.get("smtp_host", "")
        if not host:
            return None
        from app.services.email_service import EmailService
        return EmailService(
            host=host, port=int(s.get("smtp_port", "587")),
            user=s.get("smtp_user", ""), password=s.get("smtp_pass", ""),
            from_addr=s.get("smtp_from", s.get("smtp_user", "")),
            app_name=s.get("app_name", s.get("org_name", "App")),
        )
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_get()) if not loop.is_running() else None

async def get_email_service_async(db):
    settings_docs = await db.settings.find().to_list(100)
    s = {d["key"]: d["value"] for d in settings_docs}
    host = s.get("smtp_host", "")
    if not host:
        return None
    from app.services.email_service import EmailService
    return EmailService(
        host=host, port=int(s.get("smtp_port", "587")),
        user=s.get("smtp_user", ""), password=s.get("smtp_pass", ""),
        from_addr=s.get("smtp_from", s.get("smtp_user", "")),
        app_name=s.get("app_name", s.get("org_name", "App")),
    )

async def should_send_email(db, email_type: str) -> bool:
    """Check if admin has enabled this email type."""
    doc = await db.settings.find_one({"key": f"email_{email_type}_enabled"})
    if doc is None:
        return True  # Default: enabled
    return doc["value"] in ("true", "1", True)

@router.post("/register")
async def register(data: dict, background_tasks: BackgroundTasks, db=Depends(get_db)):
    email = data.get("email", "").lower().strip()
    password = data.get("password", "")
    name = data.get("name", "")

    if not email or not password:
        raise HTTPException(400, "Email and password required")
    if len(password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")

    otp = generate_otp()
    user = {
        "email": email,
        "password_hash": hash_password(password),
        "name": name,
        "role": data.get("role", "user"),
        "is_active": True,
        "email_verified": False,
        "email_otp": otp,
        "email_otp_expiry": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        "reset_otp": None,
        "reset_otp_expiry": None,
        "refresh_token": None,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.users.insert_one(user)

    # Send verification email in background
    if await should_send_email(db, "verification"):
        email_svc = await get_email_service_async(db)
        if email_svc:
            background_tasks.add_task(email_svc.send_verification_otp, email, name, otp)

    return {"success": True, "message": "Registration successful. Please verify your email.", "user_id": str(result.inserted_id), "requires_verification": True}

@router.post("/verify-email")
async def verify_email(data: dict, background_tasks: BackgroundTasks, db=Depends(get_db)):
    email = data.get("email", "").lower().strip()
    otp = data.get("otp", "")

    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(404, "User not found")
    if user.get("email_verified"):
        return {"success": True, "message": "Email already verified"}
    if user.get("email_otp") != otp:
        raise HTTPException(400, "Invalid OTP")
    if user.get("email_otp_expiry") and datetime.fromisoformat(user["email_otp_expiry"]) < datetime.now(timezone.utc):
        raise HTTPException(400, "OTP expired. Request a new one.")

    await db.users.update_one({"_id": user["_id"]}, {"$set": {"email_verified": True, "email_otp": None, "email_otp_expiry": None}})

    # Send welcome email
    if await should_send_email(db, "welcome"):
        email_svc = await get_email_service_async(db)
        if email_svc:
            background_tasks.add_task(email_svc.send_welcome, email, user.get("name", ""))

    return {"success": True, "message": "Email verified successfully"}

@router.post("/resend-otp")
async def resend_otp(data: dict, background_tasks: BackgroundTasks, db=Depends(get_db)):
    email = data.get("email", "").lower().strip()
    user = await db.users.find_one({"email": email})
    if not user:
        return {"success": True, "message": "If the email exists, an OTP has been sent."}

    otp = generate_otp()
    await db.users.update_one({"_id": user["_id"]}, {"$set": {
        "email_otp": otp,
        "email_otp_expiry": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
    }})

    email_svc = await get_email_service_async(db)
    if email_svc:
        background_tasks.add_task(email_svc.send_verification_otp, email, user.get("name", ""), otp)

    return {"success": True, "message": "If the email exists, an OTP has been sent."}

@router.post("/login")
async def login(data: dict, db=Depends(get_db)):
    email = data.get("email", "").lower().strip()
    password = data.get("password", "")

    user = await db.users.find_one({"email": email})
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    if not user.get("is_active", True):
        raise HTTPException(403, "Account is disabled")

    # Check email verification (skip for admin)
    require_verify = True
    verify_setting = await db.settings.find_one({"key": "require_email_verification"})
    if verify_setting and verify_setting["value"] in ("false", "0", False):
        require_verify = False

    if require_verify and user.get("role") != "admin" and not user.get("email_verified", False):
        raise HTTPException(403, detail="Please verify your email first")

    # Generate tokens
    access_token = create_token(str(user["_id"]), user.get("role", "user"))
    refresh_token = secrets.token_urlsafe(64)

    await db.users.update_one({"_id": user["_id"]}, {"$set": {
        "refresh_token": refresh_token,
        "last_login_at": datetime.now(timezone.utc),
    }})

    return {
        "success": True,
        "token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "name": user.get("name", ""),
            "role": user.get("role", "user"),
            "email_verified": user.get("email_verified", False),
        },
    }

@router.post("/refresh")
async def refresh_token(data: dict, db=Depends(get_db)):
    token = data.get("refresh_token", "")
    if not token:
        raise HTTPException(401, "Refresh token required")

    user = await db.users.find_one({"refresh_token": token})
    if not user:
        raise HTTPException(401, "Invalid refresh token")

    new_access = create_token(str(user["_id"]), user.get("role", "user"))
    new_refresh = secrets.token_urlsafe(64)
    await db.users.update_one({"_id": user["_id"]}, {"$set": {"refresh_token": new_refresh}})

    return {"success": True, "token": new_access, "refresh_token": new_refresh}

@router.post("/logout")
async def logout(user=Depends(get_current_user), db=Depends(get_db)):
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": {"refresh_token": None}})
    return {"success": True, "message": "Logged out"}

@router.post("/forgot-password")
async def forgot_password(data: dict, background_tasks: BackgroundTasks, db=Depends(get_db)):
    email = data.get("email", "").lower().strip()
    user = await db.users.find_one({"email": email})

    # Always return success (don't reveal if email exists)
    if not user:
        return {"success": True, "message": "If the email exists, a reset code has been sent."}

    otp = generate_otp()
    await db.users.update_one({"_id": user["_id"]}, {"$set": {
        "reset_otp": otp,
        "reset_otp_expiry": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
    }})

    if await should_send_email(db, "password_reset"):
        email_svc = await get_email_service_async(db)
        if email_svc:
            background_tasks.add_task(email_svc.send_password_reset_otp, email, user.get("name", ""), otp)

    return {"success": True, "message": "If the email exists, a reset code has been sent."}

@router.post("/reset-password")
async def reset_password(data: dict, background_tasks: BackgroundTasks, db=Depends(get_db)):
    email = data.get("email", "").lower().strip()
    otp = data.get("otp", "")
    new_password = data.get("new_password", "")

    if len(new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(404, "User not found")
    if user.get("reset_otp") != otp:
        raise HTTPException(400, "Invalid OTP")
    if user.get("reset_otp_expiry") and datetime.fromisoformat(user["reset_otp_expiry"]) < datetime.now(timezone.utc):
        raise HTTPException(400, "OTP expired")

    await db.users.update_one({"_id": user["_id"]}, {"$set": {
        "password_hash": hash_password(new_password),
        "reset_otp": None,
        "reset_otp_expiry": None,
        "refresh_token": None,  # Force re-login everywhere
    }})

    if await should_send_email(db, "password_changed"):
        email_svc = await get_email_service_async(db)
        if email_svc:
            background_tasks.add_task(email_svc.send_password_changed, email, user.get("name", ""))

    return {"success": True, "message": "Password reset successful. Please log in."}

@router.put("/change-password")
async def change_password(data: dict, background_tasks: BackgroundTasks, user=Depends(get_current_user), db=Depends(get_db)):
    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")

    if len(new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    full_user = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not verify_password(current_password, full_user["password_hash"]):
        raise HTTPException(400, "Current password is incorrect")

    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": {
        "password_hash": hash_password(new_password),
        "refresh_token": None,
    }})

    if await should_send_email(db, "password_changed"):
        email_svc = await get_email_service_async(db)
        if email_svc:
            background_tasks.add_task(email_svc.send_password_changed, full_user["email"], full_user.get("name", ""))

    return {"success": True, "message": "Password changed successfully"}

@router.get("/me")
async def me(user=Depends(get_current_user)):
    return {"success": True, "user": {
        "id": user["id"], "email": user["email"],
        "name": user.get("name", ""), "role": user.get("role", "user"),
        "email_verified": user.get("email_verified", False),
    }}

@router.put("/me")
async def update_profile(data: dict, user=Depends(get_current_user), db=Depends(get_db)):
    updates = {}
    if "name" in data: updates["name"] = data["name"]
    if "phone" in data: updates["phone"] = data["phone"]
    if updates:
        await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": updates})
    return {"success": True, "message": "Profile updated"}
