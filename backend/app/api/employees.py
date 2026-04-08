from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.database import get_db
from app.utils.auth import get_current_user
from bson import ObjectId
from datetime import datetime, timezone
import random

router = APIRouter(prefix="/api/employees", tags=["employees"])


def emp_serial(doc):
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return doc


async def next_employee_id(db):
    last = await db.employees.find_one(sort=[("employee_id", -1)])
    if last:
        num = int(last["employee_id"].split("-")[1]) + 1
    else:
        num = 1001
    return f"EMP-{num:04d}"


@router.get("/")
async def list_employees(
    q: str = Query("", description="Search name/email/employee_id"),
    department: str = Query("", description="Filter by department"),
    status: str = Query("", description="active/inactive"),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    query = {}
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}},
            {"employee_id": {"$regex": q, "$options": "i"}},
        ]
    if department:
        query["department"] = department
    if status == "active":
        query["is_active"] = True
    elif status == "inactive":
        query["is_active"] = False

    docs = await db.employees.find(query).sort("employee_id", 1).to_list(500)
    return {"success": True, "employees": [emp_serial(d) for d in docs]}


@router.post("/")
async def create_employee(data: dict, db=Depends(get_db), user=Depends(get_current_user)):
    # Check email uniqueness
    if await db.employees.find_one({"email": data["email"]}):
        raise HTTPException(400, "Email already exists")

    employee_id = await next_employee_id(db)
    doc = {
        "employee_id": employee_id,
        "name": data["name"],
        "email": data["email"],
        "phone": data.get("phone", ""),
        "department": data["department"],
        "designation": data.get("designation", ""),
        "date_of_joining": data.get("date_of_joining", ""),
        "bank_account": data.get("bank_account", ""),
        "pan_number": data.get("pan_number", ""),
        "basic_salary": float(data.get("basic_salary", 0)),
        "hra_percent": float(data.get("hra_percent", 40)),
        "da_percent": float(data.get("da_percent", 10)),
        "special_allowance": float(data.get("special_allowance", 0)),
        "is_active": data.get("is_active", True),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    result = await db.employees.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc["_id"] = result.inserted_id
    return {"success": True, "employee": emp_serial(doc)}


@router.get("/search")
async def search_employees(q: str = Query(""), db=Depends(get_db), user=Depends(get_current_user)):
    if not q:
        return {"success": True, "employees": []}
    query = {
        "$or": [
            {"name": {"$regex": q, "$options": "i"}},
            {"employee_id": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}},
        ],
        "is_active": True,
    }
    docs = await db.employees.find(query).limit(20).to_list(20)
    return {"success": True, "employees": [emp_serial(d) for d in docs]}


@router.get("/departments")
async def list_departments(db=Depends(get_db), user=Depends(get_current_user)):
    docs = await db.departments.find().to_list(100)
    return {"success": True, "departments": [{"id": str(d["_id"]), "name": d["name"], "code": d["code"]} for d in docs]}


@router.get("/{employee_id}")
async def get_employee(employee_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    doc = None
    if ObjectId.is_valid(employee_id):
        doc = await db.employees.find_one({"_id": ObjectId(employee_id)})
    if not doc:
        doc = await db.employees.find_one({"employee_id": employee_id})
    if not doc:
        raise HTTPException(404, "Employee not found")

    emp = emp_serial(doc)
    # Attach recent payslips
    payslips = await db.payslips.find({"employee_id": emp["employee_id"]}).sort([("year", -1), ("month", -1)]).limit(12).to_list(12)
    emp["recent_payslips"] = []
    for p in payslips:
        p["id"] = str(p["_id"])
        del p["_id"]
        emp["recent_payslips"].append(p)

    return {"success": True, "employee": emp}


@router.put("/{employee_id}")
async def update_employee(employee_id: str, data: dict, db=Depends(get_db), user=Depends(get_current_user)):
    query = {"_id": ObjectId(employee_id)} if ObjectId.is_valid(employee_id) else {"employee_id": employee_id}
    data.pop("_id", None)
    data.pop("id", None)
    data.pop("employee_id", None)
    data["updated_at"] = datetime.now(timezone.utc)

    # Convert numeric fields
    for f in ["basic_salary", "hra_percent", "da_percent", "special_allowance"]:
        if f in data:
            data[f] = float(data[f])

    result = await db.employees.update_one(query, {"$set": data})
    if result.matched_count == 0:
        raise HTTPException(404, "Employee not found")
    return {"success": True}


@router.delete("/{employee_id}")
async def delete_employee(employee_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    query = {"_id": ObjectId(employee_id)} if ObjectId.is_valid(employee_id) else {"employee_id": employee_id}
    result = await db.employees.update_one(query, {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}})
    if result.matched_count == 0:
        raise HTTPException(404, "Employee not found")
    return {"success": True}
