from fastapi import APIRouter, Depends, HTTPException
from app.core.database import get_db
from app.utils.auth import get_current_user
from app.api.salary import compute_salary, get_settings_map
from bson import ObjectId
from datetime import datetime, timezone

router = APIRouter(prefix="/api/payroll", tags=["payroll"])


def serialize(doc):
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return doc


@router.post("/run")
async def run_payroll(data: dict, db=Depends(get_db), user=Depends(get_current_user)):
    month = int(data["month"])
    year = int(data["year"])

    # Check if already run
    existing = await db.payroll_runs.find_one({"month": month, "year": year})
    if existing:
        raise HTTPException(400, f"Payroll already run for {month}/{year}")

    settings_map = await get_settings_map(db)
    employees = await db.employees.find({"is_active": True}).to_list(1000)

    if not employees:
        raise HTTPException(400, "No active employees found")

    payslips = []
    total_gross = 0
    total_net = 0

    for emp in employees:
        # Get attendance for proration
        attendance = await db.attendance.find({
            "employee_id": emp["employee_id"],
            "month": month,
            "year": year,
        }).to_list(100)

        # If no attendance records, assume full month (22 working days)
        working_days = 22
        if attendance:
            present = sum(1 for a in attendance if a["status"] == "present")
            half_days = sum(1 for a in attendance if a["status"] == "half_day")
            effective_days = present + (half_days * 0.5)
        else:
            effective_days = working_days

        proration = min(effective_days / working_days, 1.0)

        structure = await compute_salary(emp, settings_map)

        # Prorate
        prorated_basic = round(structure["basic"] * proration, 2)
        prorated_hra = round(structure["hra"] * proration, 2)
        prorated_da = round(structure["da"] * proration, 2)
        prorated_special = round(structure["special_allowance"] * proration, 2)
        prorated_gross = round(prorated_basic + prorated_hra + prorated_da + prorated_special, 2)

        # Deductions (PF on prorated basic, others on prorated gross)
        pf_rate = float(settings_map.get("pf_rate", 12))
        esi_rate = float(settings_map.get("esi_rate", 0.75))
        prof_tax = float(settings_map.get("professional_tax", 200))

        pf = round(prorated_basic * pf_rate / 100, 2)
        esi = round(prorated_gross * esi_rate / 100, 2) if structure["gross"] < 21000 else 0
        tds = round(structure["tds"] * proration, 2)
        total_deductions = round(pf + esi + prof_tax + tds, 2)
        net = round(prorated_gross - total_deductions, 2)

        payslip = {
            "employee_id": emp["employee_id"],
            "employee_name": emp["name"],
            "department": emp["department"],
            "designation": emp.get("designation", ""),
            "month": month,
            "year": year,
            "working_days": working_days,
            "effective_days": effective_days,
            "basic": prorated_basic,
            "hra": prorated_hra,
            "da": prorated_da,
            "special_allowance": prorated_special,
            "gross": prorated_gross,
            "pf": pf,
            "esi": esi,
            "professional_tax": prof_tax,
            "tds": tds,
            "total_deductions": total_deductions,
            "net_salary": net,
            "status": "generated",
            "created_at": datetime.now(timezone.utc),
        }

        try:
            result = await db.payslips.insert_one(payslip)
            payslip["id"] = str(result.inserted_id)
            payslip["_id"] = result.inserted_id
        except Exception:
            # Duplicate - skip
            continue

        payslips.append(payslip)
        total_gross += prorated_gross
        total_net += net

    # Create payroll run record
    run_doc = {
        "month": month,
        "year": year,
        "employee_count": len(payslips),
        "total_gross": round(total_gross, 2),
        "total_net": round(total_net, 2),
        "total_deductions": round(total_gross - total_net, 2),
        "status": "processed",
        "created_at": datetime.now(timezone.utc),
        "processed_by": user.get("name", user.get("email", "")),
    }
    run_result = await db.payroll_runs.insert_one(run_doc)

    run_doc["id"] = str(run_result.inserted_id)
    for p in payslips:
        p.pop("_id", None)

    return {
        "success": True,
        "payroll_run": serialize(run_doc) if "_id" in run_doc else run_doc,
        "payslips_count": len(payslips),
        "total_gross": round(total_gross, 2),
        "total_net": round(total_net, 2),
    }


@router.get("/")
async def list_payroll_runs(db=Depends(get_db), user=Depends(get_current_user)):
    runs = await db.payroll_runs.find().sort([("year", -1), ("month", -1)]).to_list(100)
    return {"success": True, "payroll_runs": [serialize(r) for r in runs]}


@router.get("/stats")
async def payroll_stats(db=Depends(get_db), user=Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    current_run = await db.payroll_runs.find_one({"month": now.month, "year": now.year})
    total_runs = await db.payroll_runs.count_documents({})

    # Last 6 months trend
    pipeline = [
        {"$sort": {"year": -1, "month": -1}},
        {"$limit": 6},
        {"$project": {"month": 1, "year": 1, "total_gross": 1, "total_net": 1, "employee_count": 1}},
    ]
    trend = []
    async for doc in db.payroll_runs.aggregate(pipeline):
        doc["id"] = str(doc["_id"])
        del doc["_id"]
        trend.append(doc)

    return {
        "success": True,
        "stats": {
            "total_runs": total_runs,
            "current_month_processed": current_run is not None,
            "current_month_total": current_run["total_net"] if current_run else 0,
            "trend": list(reversed(trend)),
        },
    }


@router.get("/{run_id}")
async def get_payroll_run(run_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    if not ObjectId.is_valid(run_id):
        raise HTTPException(400, "Invalid run ID")
    run = await db.payroll_runs.find_one({"_id": ObjectId(run_id)})
    if not run:
        raise HTTPException(404, "Payroll run not found")

    payslips = await db.payslips.find({"month": run["month"], "year": run["year"]}).to_list(500)

    return {
        "success": True,
        "payroll_run": serialize(run),
        "payslips": [serialize(p) for p in payslips],
    }


@router.put("/{run_id}/status")
async def update_run_status(run_id: str, data: dict, db=Depends(get_db), user=Depends(get_current_user)):
    if not ObjectId.is_valid(run_id):
        raise HTTPException(400, "Invalid run ID")
    status = data.get("status", "paid")
    await db.payroll_runs.update_one({"_id": ObjectId(run_id)}, {"$set": {"status": status}})
    # Update payslips too
    run = await db.payroll_runs.find_one({"_id": ObjectId(run_id)})
    if run:
        await db.payslips.update_many(
            {"month": run["month"], "year": run["year"]},
            {"$set": {"status": status}},
        )
    return {"success": True}
