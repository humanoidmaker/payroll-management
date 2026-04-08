from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import init_db
from app.api import auth, settings as settings_api
from app.api import employees, salary, payroll, payslips, attendance

@asynccontextmanager
async def lifespan(a):
    await init_db()
    yield

app = FastAPI(title="PayRoll Pro API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(settings_api.router)
app.include_router(employees.router)
app.include_router(salary.router)
app.include_router(payroll.router)
app.include_router(payslips.router)
app.include_router(attendance.router)

@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "PayRoll Pro"}

@app.get("/api/stats")
async def stats():
    from app.core.database import get_db as gdb
    from datetime import datetime, timezone
    db = await gdb()
    now = datetime.now(timezone.utc)

    total_employees = await db.employees.count_documents({"is_active": True})

    # This month payroll total
    current_run = await db.payroll_runs.find_one({"month": now.month, "year": now.year})
    this_month_total = current_run["total_net"] if current_run else 0

    # Average salary
    pipeline = [
        {"$match": {"is_active": True}},
        {"$group": {"_id": None, "avg_salary": {"$avg": "$basic_salary"}}},
    ]
    avg_result = await db.employees.aggregate(pipeline).to_list(1)
    avg_salary = round(avg_result[0]["avg_salary"], 2) if avg_result else 0

    # Departments count
    departments = await db.departments.count_documents({})

    # Department-wise salary distribution
    dept_pipeline = [
        {"$match": {"is_active": True}},
        {"$group": {"_id": "$department", "total_salary": {"$sum": "$basic_salary"}, "count": {"$sum": 1}}},
        {"$sort": {"total_salary": -1}},
    ]
    dept_dist = []
    async for doc in db.employees.aggregate(dept_pipeline):
        dept_dist.append({"department": doc["_id"], "total_salary": doc["total_salary"], "count": doc["count"]})

    # Recent payroll runs
    recent_runs = await db.payroll_runs.find().sort([("year", -1), ("month", -1)]).limit(6).to_list(6)
    for r in recent_runs:
        r["id"] = str(r["_id"])
        del r["_id"]

    # Pending payroll (current month not yet processed)
    pending = current_run is None

    return {
        "success": True,
        "stats": {
            "total_employees": total_employees,
            "this_month_payroll_total": this_month_total,
            "avg_salary": avg_salary,
            "departments_count": departments,
            "department_distribution": dept_dist,
            "recent_payroll_runs": recent_runs,
            "pending_payroll": pending,
        },
    }
