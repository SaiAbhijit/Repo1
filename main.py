from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, FileResponse
import pandas as pd
import uuid
import os

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    df = pd.read_excel(file.file)
    summary = "This month saw a salary reduction mainly due to lower payouts in Engineering and Support."
    breakdown = [
        {"department": "Engineering", "reason": "Reduction in contract staff."},
        {"department": "Support", "reason": "One-time bonuses removed."}
    ]
    return JSONResponse(content={
        "summary": summary,
        "breakdown": breakdown
    })

@app.post("/download-report")
async def download_report(file: UploadFile = File(...)):
    temp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}.pdf")
    with open(temp_path, "wb") as f:
        f.write(b"%PDF-1.4 Dummy PDF Report")
    return FileResponse(temp_path, filename="SalaryVarianceReport.pdf", media_type="application/pdf")
