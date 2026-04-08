from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.database import get_db
from app.utils.auth import get_current_user
from bson import ObjectId
from datetime import datetime, timezone

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


def serialize(doc):
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return doc


@router.post("/")
async def mark_attendance(data: dict, db=Depends(get_db), user=Depends(get_current_user)):
    employee_id = data["employee_id"]
    date_str = data["date"]  # YYYY-MM-DD
    status = data["status"]  # present, absent, half_day, leave

    if status not in ("present", "absent", "half_day", "leave"):
        raise HTTPException(400, "Invalid status. Use: present, absent, half_day, leave")

    # Verify employee exists
    emp = await db.employees.find_one({"employee_id": employee_id})
    if not emp:
        raise HTTPException(404, "Employee not found")

    # Parse date for month/year
    dt = datetime.strptime(date_str, "%Y-%m-%d")

    doc = {
        "employee_id": employee_id,
        "employee_name": emp["name"],
        "date": date_str,
        "day": dt.day,
        "month": dt.month,
        "year": dt.year,
        "status": status,
        "updated_at": datetime.now(timezone.utc),
    }

    # Upsert by employee_id + date
    await db.attendance.update_one(
        {"employee_id": employee_id, "date": date_str},
        {"$set": doc},
        upsert=True,
    )

    return {"success": True}


@router.post("/bulk")
async def bulk_attendance(data: dict, db=Depends(get_db), user=Depends(get_current_user)):
    """Mark attendance for multiple employees at once."""
    entries = data.get("entries", [])
    count = 0
    for entry in entries:
        employee_id = entry["employee_id"]
        date_str = entry["date"]
        status = entry["status"]
        dt = datetime.strptime(date_str, "%Y-%m-%d")

        emp = await db.employees.find_one({"employee_id": employee_id})
        if not emp:
            continue

        doc = {
            "employee_id": employee_id,
            "employee_name": emp["name"],
            "date": date_str,
            "day": dt.day,
            "month": dt.month,
            "year": dt.year,
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }
        await db.attendance.update_one(
            {"employee_id": employee_id, "date": date_str},
            {"$set": doc},
            upsert=True,
        )
        count += 1

    return {"success": True, "updated": count}


@router.get("/employee/{employee_id}")
async def get_employee_attendance(
    employee_id: str,
    month: int = Query(0),
    year: int = Query(0),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    if not month:
        month = now.month
    if not year:
        year = now.year

    docs = await db.attendance.find({
        "employee_id": employee_id,
        "month": month,
        "year": year,
    }).sort("day", 1).to_list(31)

    return {"success": True, "attendance": [serialize(d) for d in docs]}


@router.get("/summary")
async def attendance_summary(
    month: int = Query(0),
    year: int = Query(0),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    if not month:
        month = now.month
    if not year:
        year = now.year

    pipeline = [
        {"$match": {"month": month, "year": year}},
        {"$group": {
            "_id": "$employee_id",
            "employee_name": {"$first": "$employee_name"},
            "present_days": {"$sum": {"$cond": [{"$eq": ["$status", "present"]}, 1, 0]}},
            "absent_days": {"$sum": {"$cond": [{"$eq": ["$status", "absent"]}, 1, 0]}},
            "half_days": {"$sum": {"$cond": [{"$eq": ["$status", "half_day"]}, 1, 0]}},
            "leaves": {"$sum": {"$cond": [{"$eq": ["$status", "leave"]}, 1, 0]}},
            "total_records": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]

    results = []
    async for doc in db.attendance.aggregate(pipeline):
        results.append({
            "employee_id": doc["_id"],
            "employee_name": doc["employee_name"],
            "present_days": doc["present_days"],
            "absent_days": doc["absent_days"],
            "half_days": doc["half_days"],
            "leaves": doc["leaves"],
            "total_records": doc["total_records"],
        })

    return {"success": True, "summary": results, "month": month, "year": year}
