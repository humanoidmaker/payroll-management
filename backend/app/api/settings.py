from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.utils.auth import require_admin, get_current_user

router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.get("/")
async def get_all(db=Depends(get_db)):
    docs = await db.settings.find().to_list(200)
    result = {}
    for d in docs:
        # Hide SMTP password from non-admin responses
        if d["key"] == "smtp_pass":
            result[d["key"]] = "********" if d["value"] else ""
        else:
            result[d["key"]] = d["value"]
    return {"success": True, "settings": result}

@router.put("/")
async def update(data: dict, user=Depends(require_admin), db=Depends(get_db)):
    for k, v in data.items():
        # Don't overwrite smtp_pass with masked value
        if k == "smtp_pass" and v == "********":
            continue
        await db.settings.update_one({"key": k}, {"$set": {"value": v}}, upsert=True)
    return {"success": True}

@router.get("/email-config")
async def email_config(user=Depends(require_admin), db=Depends(get_db)):
    """Get email configuration for admin dashboard."""
    docs = await db.settings.find({"key": {"$regex": "^(smtp_|email_|require_email)"}}).to_list(50)
    config = {d["key"]: d["value"] for d in docs}
    # Mask password
    if "smtp_pass" in config and config["smtp_pass"]:
        config["smtp_pass"] = "********"
    return {"success": True, "config": config}

@router.put("/email-config")
async def update_email_config(data: dict, user=Depends(require_admin), db=Depends(get_db)):
    """Update email configuration."""
    allowed_keys = [
        "smtp_host", "smtp_port", "smtp_user", "smtp_pass", "smtp_from",
        "email_verification_enabled", "email_welcome_enabled",
        "email_password_reset_enabled", "email_password_changed_enabled",
        "require_email_verification",
    ]
    for k, v in data.items():
        if k in allowed_keys:
            if k == "smtp_pass" and v == "********":
                continue
            await db.settings.update_one({"key": k}, {"$set": {"value": str(v)}}, upsert=True)
    return {"success": True}

@router.post("/test-email")
async def test_email(data: dict, user=Depends(require_admin), db=Depends(get_db)):
    """Send a test email to verify SMTP configuration."""
    from app.services.email_service import EmailService
    docs = await db.settings.find().to_list(100)
    s = {d["key"]: d["value"] for d in docs}

    host = s.get("smtp_host", "")
    if not host:
        return {"success": False, "error": "SMTP not configured"}

    svc = EmailService(
        host=host, port=int(s.get("smtp_port", "587")),
        user=s.get("smtp_user", ""), password=s.get("smtp_pass", ""),
        from_addr=s.get("smtp_from", s.get("smtp_user", "")),
        app_name=s.get("app_name", "App"),
    )
    to = data.get("to", user["email"])
    result = svc.send_custom(to, "Test Email", f"This is a test email from {s.get('app_name', 'App')}. SMTP is working correctly.")
    return {"success": result, "message": "Test email sent" if result else "Failed to send"}
