from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client = None
db = None

async def get_db():
    return db

async def init_db():
    global client, db
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db_name = settings.MONGODB_URI.rsplit("/", 1)[-1].split("?")[0] or "payroll_mgmt"
    db = client[db_name]

    # Core indexes
    await db.users.create_index("email", unique=True)
    await db.employees.create_index("employee_id", unique=True)
    await db.employees.create_index("email", unique=True)
    await db.payroll_runs.create_index([("month", 1), ("year", 1)], unique=True)
    await db.payslips.create_index([("employee_id", 1), ("month", 1), ("year", 1)], unique=True)
    await db.attendance.create_index([("employee_id", 1), ("date", 1)], unique=True)

    # Seed settings
    if not await db.settings.find_one({"key": "app_name"}):
        await db.settings.insert_many([
            {"key": "app_name", "value": "PayRoll Pro"},
            {"key": "org_name", "value": "PayRoll Pro Organization"},
            {"key": "company_name", "value": "PayRoll Pro Pvt Ltd"},
            {"key": "pf_rate", "value": "12"},
            {"key": "esi_rate", "value": "0.75"},
            {"key": "professional_tax", "value": "200"},
            {"key": "tds_threshold", "value": "500000"},
        ])

    # Seed departments
    if await db.departments.count_documents({}) == 0:
        await db.departments.insert_many([
            {"name": "Engineering", "code": "ENG"},
            {"name": "Human Resources", "code": "HR"},
            {"name": "Finance", "code": "FIN"},
            {"name": "Marketing", "code": "MKT"},
            {"name": "Operations", "code": "OPS"},
            {"name": "Sales", "code": "SAL"},
        ])
