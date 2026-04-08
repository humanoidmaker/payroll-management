from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from app.core.database import get_db
from app.utils.auth import get_current_user
from bson import ObjectId

router = APIRouter(prefix="/api/payslips", tags=["payslips"])

MONTHS = ["", "January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


def serialize(doc):
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return doc


@router.get("/employee/{employee_id}")
async def get_employee_payslips(
    employee_id: str,
    year: int = Query(0),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    query = {"employee_id": employee_id}
    if year:
        query["year"] = year
    docs = await db.payslips.find(query).sort([("year", -1), ("month", -1)]).to_list(100)
    return {"success": True, "payslips": [serialize(d) for d in docs]}


@router.get("/{payslip_id}")
async def get_payslip(payslip_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    if not ObjectId.is_valid(payslip_id):
        raise HTTPException(400, "Invalid payslip ID")
    doc = await db.payslips.find_one({"_id": ObjectId(payslip_id)})
    if not doc:
        raise HTTPException(404, "Payslip not found")
    return {"success": True, "payslip": serialize(doc)}


@router.get("/{payslip_id}/pdf")
async def get_payslip_pdf(payslip_id: str, db=Depends(get_db)):
    if not ObjectId.is_valid(payslip_id):
        raise HTTPException(400, "Invalid payslip ID")
    slip = await db.payslips.find_one({"_id": ObjectId(payslip_id)})
    if not slip:
        raise HTTPException(404, "Payslip not found")

    settings_docs = await db.settings.find().to_list(100)
    settings_map = {d["key"]: d["value"] for d in settings_docs}
    company = settings_map.get("company_name", "PayRoll Pro Pvt Ltd")

    # Fetch employee details
    emp = await db.employees.find_one({"employee_id": slip["employee_id"]})
    emp_email = emp.get("email", "") if emp else ""
    emp_pan = emp.get("pan_number", "") if emp else ""
    emp_bank = emp.get("bank_account", "") if emp else ""
    emp_doj = emp.get("date_of_joining", "") if emp else ""

    month_name = MONTHS[slip["month"]] if 1 <= slip["month"] <= 12 else str(slip["month"])

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Payslip - {slip['employee_name']}</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; color: #1e293b; }}
  .container {{ max-width: 800px; margin: 0 auto; border: 2px solid #1e293b; }}
  .header {{ background: #1e293b; color: white; padding: 20px; text-align: center; }}
  .header h1 {{ margin: 0; font-size: 22px; }}
  .header p {{ margin: 5px 0 0; font-size: 13px; opacity: 0.8; }}
  .meta {{ display: flex; justify-content: space-between; padding: 15px 20px; border-bottom: 1px solid #e2e8f0; background: #f8fafc; }}
  .meta div {{ font-size: 13px; }}
  .meta strong {{ color: #1e293b; }}
  .section {{ padding: 15px 20px; }}
  .section h3 {{ margin: 0 0 10px; font-size: 14px; color: #6366f1; text-transform: uppercase; letter-spacing: 1px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
  th {{ background: #f1f5f9; font-weight: 600; color: #475569; }}
  .amount {{ text-align: right; font-family: monospace; }}
  .total-row {{ font-weight: 700; background: #f8fafc; font-size: 14px; }}
  .net-pay {{ background: #1e293b; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; font-size: 18px; }}
  .net-pay .label {{ font-weight: 600; }}
  .net-pay .value {{ font-family: monospace; font-size: 22px; font-weight: 700; }}
  .footer {{ padding: 15px 20px; font-size: 11px; color: #94a3b8; text-align: center; border-top: 1px solid #e2e8f0; }}
  @media print {{ body {{ padding: 0; }} .container {{ border: none; }} }}
</style></head><body>
<div class="container">
  <div class="header">
    <h1>{company}</h1>
    <p>Payslip for {month_name} {slip['year']}</p>
  </div>
  <div class="meta">
    <div><strong>Employee ID:</strong> {slip['employee_id']}<br><strong>Name:</strong> {slip['employee_name']}<br><strong>Email:</strong> {emp_email}</div>
    <div><strong>Department:</strong> {slip.get('department', '')}<br><strong>Designation:</strong> {slip.get('designation', '')}<br><strong>PAN:</strong> {emp_pan}</div>
    <div><strong>Bank A/C:</strong> {emp_bank}<br><strong>DOJ:</strong> {emp_doj}<br><strong>Working Days:</strong> {slip.get('effective_days', 22)}/{slip.get('working_days', 22)}</div>
  </div>
  <div style="display: flex;">
    <div style="flex:1;" class="section">
      <h3>Earnings</h3>
      <table>
        <tr><th>Component</th><th class="amount">Amount</th></tr>
        <tr><td>Basic Salary</td><td class="amount">&#8377;{slip['basic']:,.2f}</td></tr>
        <tr><td>HRA</td><td class="amount">&#8377;{slip['hra']:,.2f}</td></tr>
        <tr><td>DA</td><td class="amount">&#8377;{slip['da']:,.2f}</td></tr>
        <tr><td>Special Allowance</td><td class="amount">&#8377;{slip['special_allowance']:,.2f}</td></tr>
        <tr class="total-row"><td>Gross Salary</td><td class="amount">&#8377;{slip['gross']:,.2f}</td></tr>
      </table>
    </div>
    <div style="flex:1;" class="section">
      <h3>Deductions</h3>
      <table>
        <tr><th>Component</th><th class="amount">Amount</th></tr>
        <tr><td>Provident Fund</td><td class="amount">&#8377;{slip['pf']:,.2f}</td></tr>
        <tr><td>ESI</td><td class="amount">&#8377;{slip['esi']:,.2f}</td></tr>
        <tr><td>Professional Tax</td><td class="amount">&#8377;{slip['professional_tax']:,.2f}</td></tr>
        <tr><td>TDS</td><td class="amount">&#8377;{slip['tds']:,.2f}</td></tr>
        <tr class="total-row"><td>Total Deductions</td><td class="amount">&#8377;{slip['total_deductions']:,.2f}</td></tr>
      </table>
    </div>
  </div>
  <div class="net-pay">
    <span class="label">Net Pay</span>
    <span class="value">&#8377;{slip['net_salary']:,.2f}</span>
  </div>
  <div class="footer">This is a computer-generated payslip and does not require a signature.</div>
</div>
</body></html>"""

    return HTMLResponse(content=html)
