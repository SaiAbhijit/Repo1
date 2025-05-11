# Core libraries
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import io
from typing import List, Optional

app = FastAPI(title="HR Variance Analyzer API")

# Simulated database
EMPLOYEE_DATA = {}  # key: employee_id, value: {period: payroll data}

# Utility functions
def read_excel(file_bytes: bytes) -> pd.DataFrame:
    try:
        return pd.read_excel(io.BytesIO(file_bytes))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

def detect_columns(df: pd.DataFrame) -> dict:
    mapping = {}
    for col in df.columns:
        normalized = col.strip().lower()
        if "id" in normalized:
            mapping[col] = "employee_id"
        elif "name" in normalized:
            mapping[col] = "name"
        elif "basic" in normalized or "salary" in normalized:
            mapping[col] = "basic"
        elif "hra" in normalized:
            mapping[col] = "hra"
        elif "bonus" in normalized:
            mapping[col] = "bonus"
        elif "net" in normalized:
            mapping[col] = "net_salary"
        else:
            mapping[col] = col  # keep as-is
    return mapping

def compute_variance(current: dict, previous: dict) -> dict:
    result = {}
    total_curr = 0
    total_prev = 0
    for key in current:
        if key == "employee_id":
            continue
        c_val = current.get(key, 0) or 0
        p_val = previous.get(key, 0) or 0
        diff = c_val - p_val
        pct = ((diff / p_val) * 100) if p_val != 0 else None
        result[key] = {
            "current": c_val,
            "previous": p_val,
            "difference": diff,
            "percent_change": pct
        }
        total_curr += c_val
        total_prev += p_val
    result["total_variance"] = {
        "difference": total_curr - total_prev,
        "percent_change": ((total_curr - total_prev) / total_prev * 100) if total_prev != 0 else None
    }
    return result

def generate_summary_from_variance(variance: dict) -> str:
    parts = []
    for key, stats in variance.items():
        if key == "total_variance":
            continue
        curr = stats["current"]
        prev = stats["previous"]
        diff = stats["difference"]
        pct = stats["percent_change"]

        if pct is not None:
            direction = "increased" if pct > 0 else "decreased"
            parts.append(f"{key.capitalize()} {direction} by {abs(pct):.1f}% (₹{abs(diff):,.0f})")
        else:
            if prev == 0 and curr != 0:
                parts.append(f"{key.capitalize()} changed from ₹0 to ₹{curr:,.0f}")
            else:
                parts.append(f"{key.capitalize()} changed by ₹{diff:,.0f}")

    return ". ".join(parts) + "." if parts else "No variance data found."

# API endpoints
@app.post("/upload/{period}")
async def upload_file(period: str, file: UploadFile = File(...)):
    df = read_excel(await file.read())
    columns = detect_columns(df)
    parsed_records = []

    for _, row in df.iterrows():
        record = {}
        for orig, mapped in columns.items():
            record[mapped] = row[orig]
        emp_id = str(record.get("employee_id"))
        if emp_id not in EMPLOYEE_DATA:
            EMPLOYEE_DATA[emp_id] = {}
        EMPLOYEE_DATA[emp_id][period] = record
        parsed_records.append(record)

    return {"uploaded_records": len(parsed_records), "columns_detected": columns}

class VarianceResult(BaseModel):
    employee_id: str
    variance: dict
    summary: str

@app.get("/variance/{employee_id}/{period1}/{period2}", response_model=VarianceResult)
def get_variance(employee_id: str, period1: str, period2: str):
    data = EMPLOYEE_DATA.get(employee_id)
    if not data or period1 not in data or period2 not in data:
        raise HTTPException(status_code=404, detail="Data for one or both periods not found")

    variance = compute_variance(data[period2], data[period1])
    summary = generate_summary_from_variance(variance)
    return {"employee_id": employee_id, "variance": variance, "summary": summary}
