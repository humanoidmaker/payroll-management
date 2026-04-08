from fastapi import APIRouter, Depends, HTTPException
from app.core.database import get_db
from app.utils.auth import get_current_user
from bson import ObjectId

router = APIRouter(prefix="/api/salary", tags=["salary"])


async def get_settings_map(db):
    docs = await db.settings.find().to_list(100)
    return {d["key"]: d["value"] for d in docs}


async def compute_salary(emp, settings_map):
    basic = float(emp.get("basic_salary", 0))
    hra_pct = float(emp.get("hra_percent", 40))
    da_pct = float(emp.get("da_percent", 10))
    special = float(emp.get("special_allowance", 0))
    pf_rate = float(settings_map.get("pf_rate", 12))
    esi_rate = float(settings_map.get("esi_rate", 0.75))
    prof_tax = float(settings_map.get("professional_tax", 200))
    tds_threshold = float(settings_map.get("tds_threshold", 500000))

    hra = round(basic * hra_pct / 100, 2)
    da = round(basic * da_pct / 100, 2)
    gross = round(basic + hra + da + special, 2)

    pf = round(basic * pf_rate / 100, 2)
    esi = round(gross * esi_rate / 100, 2) if gross < 21000 else 0
    # TDS estimate: simple annual projection
    annual_gross = gross * 12
    tds_monthly = 0
    if annual_gross > tds_threshold:
        taxable = annual_gross - tds_threshold
        tds_annual = taxable * 0.1  # simplified 10% slab
        tds_monthly = round(tds_annual / 12, 2)

    total_deductions = round(pf + esi + prof_tax + tds_monthly, 2)
    net_salary = round(gross - total_deductions, 2)

    return {
        "basic": basic,
        "hra": hra,
        "hra_percent": hra_pct,
        "da": da,
        "da_percent": da_pct,
        "special_allowance": special,
        "gross": gross,
        "pf": pf,
        "pf_rate": pf_rate,
        "esi": esi,
        "esi_rate": esi_rate,
        "professional_tax": prof_tax,
        "tds": tds_monthly,
        "tds_threshold": tds_threshold,
        "total_deductions": total_deductions,
        "net_salary": net_salary,
    }


@router.get("/structure/{employee_id}")
async def get_salary_structure(employee_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    emp = await db.employees.find_one({"employee_id": employee_id})
    if not emp:
        if ObjectId.is_valid(employee_id):
            emp = await db.employees.find_one({"_id": ObjectId(employee_id)})
    if not emp:
        raise HTTPException(404, "Employee not found")

    settings_map = await get_settings_map(db)
    structure = await compute_salary(emp, settings_map)
    structure["employee_id"] = emp["employee_id"]
    structure["name"] = emp["name"]
    return {"success": True, "structure": structure}


@router.put("/structure/{employee_id}")
async def update_salary_structure(employee_id: str, data: dict, db=Depends(get_db), user=Depends(get_current_user)):
    emp = await db.employees.find_one({"employee_id": employee_id})
    if not emp:
        if ObjectId.is_valid(employee_id):
            emp = await db.employees.find_one({"_id": ObjectId(employee_id)})
    if not emp:
        raise HTTPException(404, "Employee not found")

    update = {}
    if "basic_salary" in data:
        update["basic_salary"] = float(data["basic_salary"])
    if "hra_percent" in data:
        update["hra_percent"] = float(data["hra_percent"])
    if "da_percent" in data:
        update["da_percent"] = float(data["da_percent"])
    if "special_allowance" in data:
        update["special_allowance"] = float(data["special_allowance"])

    if update:
        await db.employees.update_one({"_id": emp["_id"]}, {"$set": update})

    # Return updated structure
    emp.update(update)
    settings_map = await get_settings_map(db)
    structure = await compute_salary(emp, settings_map)
    structure["employee_id"] = emp["employee_id"]
    structure["name"] = emp["name"]
    return {"success": True, "structure": structure}
