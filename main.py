from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from io import BytesIO
from fastapi.responses import StreamingResponse
from fpdf import FPDF

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
async def read_root():
    return {"message": "Welcome to the Salary Variance Tool API"}
    
@app.post("/analyze")
async def analyze_salary_data(file: UploadFile = File(...)):
    content = await file.read()
    df = pd.read_excel(BytesIO(content))

    summary = "Total salary payout decreased by 8.3% compared to the previous month."
    breakdown = [
        {"department": "Engineering", "reason": "3 employees resigned"},
        {"department": "Sales", "reason": "Lower commissions this month"},
        {"department": "HR", "reason": "1 employee on unpaid leave"}
    ]

    return {
        "summary": summary,
        "breakdown": breakdown
    }

@app.post("/download-report")
async def download_report(file: UploadFile = File(...)):
    content = await file.read()
    df = pd.read_excel(BytesIO(content))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Salary Variance Report", ln=True, align="C")
    pdf.ln(10)
    pdf.multi_cell(0, 10, txt="This month's salary variance is primarily due to team changes in Engineering and Sales. See breakdown in tool.")

    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)

    return StreamingResponse(pdf_output, media_type="application/pdf", headers={"Content-Disposition": "attachment;filename=SalaryVarianceReport.pdf"})
