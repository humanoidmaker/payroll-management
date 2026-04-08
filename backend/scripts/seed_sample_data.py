import asyncio, sys, random
from datetime import datetime, timezone, timedelta
sys.path.insert(0, ".")
from app.core.database import init_db, get_db

EMPLOYEES = [
    ("Aarav Sharma", "Engineering", "Senior Developer", 65000), ("Diya Patel", "Engineering", "Junior Developer", 35000),
    ("Vihaan Reddy", "Engineering", "Tech Lead", 80000), ("Ananya Nair", "Design", "UI Designer", 45000),
    ("Arjun Desai", "Design", "Senior Designer", 55000), ("Ishita Gupta", "Marketing", "Marketing Manager", 60000),
    ("Kabir Singh", "Marketing", "Content Writer", 30000), ("Myra Joshi", "Sales", "Sales Executive", 35000),
    ("Reyansh Verma", "Sales", "Sales Manager", 55000), ("Saanvi Pillai", "HR", "HR Manager", 50000),
    ("Dhruv Kumar", "HR", "Recruiter", 32000), ("Kiara Bhat", "Finance", "Accountant", 40000),
    ("Aditya Rao", "Engineering", "DevOps Engineer", 60000), ("Navya Iyer", "Engineering", "QA Engineer", 40000),
    ("Vivaan Menon", "Design", "Product Designer", 50000), ("Siya Das", "Marketing", "Social Media Manager", 35000),
    ("Krishna Kapoor", "Sales", "Business Analyst", 45000), ("Riya Nair", "HR", "Training Lead", 42000),
    ("Ayan Mehta", "Finance", "Finance Manager", 65000), ("Nisha Verma", "Engineering", "Frontend Developer", 42000),
]

async def seed():
    await init_db()
    db = await get_db()
    if await db.employees.count_documents({}) > 0:
        print("Data exists"); return

    emp_ids = []
    for i, (name, dept, desg, basic) in enumerate(EMPLOYEES):
        r = await db.employees.insert_one({
            "employee_id": f"EMP-{1001+i}", "name": name, "email": f"{name.split()[0].lower()}@company.local",
            "phone": f"987654{i:04d}", "department": dept, "designation": desg,
            "date_of_joining": f"2023-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            "bank_account": f"XXXX{random.randint(1000,9999)}", "pan_number": f"ABCDE{random.randint(1000,9999)}F",
            "basic_salary": basic, "hra_percent": 40, "da_percent": 10,
            "special_allowance": random.choice([2000, 3000, 5000]),
            "is_active": True,
        })
        emp_ids.append(str(r.inserted_id))

    now = datetime.now(timezone.utc)
    # Generate 3 months of payroll
    for month_offset in range(3):
        m = now - timedelta(days=30 * month_offset)
        month = m.strftime("%Y-%m")
        year = int(m.strftime("%Y"))
        month_num = int(m.strftime("%m"))

        total_gross = total_net = 0
        payslip_ids = []
        for emp_id in emp_ids:
            emp = await db.employees.find_one({"_id": __import__("bson").ObjectId(emp_id)})
            basic = emp["basic_salary"]
            hra = round(basic * emp["hra_percent"] / 100)
            da = round(basic * emp["da_percent"] / 100)
            special = emp.get("special_allowance", 0)
            gross = basic + hra + da + special
            pf = round(basic * 0.12)
            esi = round(gross * 0.0075) if gross < 21000 else 0
            pt = 200
            tds = round(gross * 0.1) if gross * 12 > 500000 else 0
            deductions = pf + esi + pt + tds
            net = gross - deductions

            ps = await db.payslips.insert_one({
                "employee_id": emp_id, "employee_name": emp["name"],
                "month": month, "year": year, "month_num": month_num,
                "basic": basic, "hra": hra, "da": da, "special_allowance": special, "gross": gross,
                "pf": pf, "esi": esi, "professional_tax": pt, "tds": tds, "total_deductions": deductions,
                "net_salary": net, "status": "processed",
            })
            payslip_ids.append(str(ps.inserted_id))
            total_gross += gross
            total_net += net

        await db.payroll_runs.insert_one({
            "month": month, "year": year, "month_num": month_num,
            "employee_count": len(emp_ids), "total_gross": total_gross, "total_net": total_net,
            "total_deductions": total_gross - total_net,
            "status": "processed", "processed_at": m,
        })

    print(f"Seeded: {len(EMPLOYEES)} employees, 3 months payroll")

asyncio.run(seed())
