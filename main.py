from fastapi import FastAPI, UploadFile, File, HTTPException
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
def root():
    return {"message": "Salary Variance Tool API is running"}

@app.post("/download-report")
async def download_report(file: UploadFile = File(...)):
    try:
        # Read the uploaded Excel file into a DataFrame.
        content = await file.read()
        df = pd.read_excel(BytesIO(content))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file format or corrupted file.")

    # Ensure required columns are present.
    required_columns = ['Salary', 'Previous Salary', 'Department']
    for col in required_columns:
        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"Missing required column: {col}")

    # Process the data for dynamic summary.
    total_salary_current = df['Salary'].sum()
    total_salary_previous = df['Previous Salary'].sum()
    if total_salary_previous == 0:
        raise HTTPException(status_code=400, detail="Previous salary total cannot be zero for calculation.")
    
    salary_variance = total_salary_current - total_salary_previous
    salary_change_percentage = (salary_variance / total_salary_previous) * 100

    summary = f"Total salary payout change: {salary_variance:.2f} ({salary_change_percentage:.2f}%) compared to the previous month."

    # Generate a breakdown per department.
    breakdown = []
    for dept in df['Department'].unique():
        dept_data = df[df['Department'] == dept]
        dept_salary_current = dept_data['Salary'].sum()
        dept_salary_previous = dept_data['Previous Salary'].sum()
        dept_salary_change = dept_salary_current - dept_salary_previous
        breakdown.append({
            "department": dept,
            "reason": f"Salary change: {dept_salary_change:.2f}"
        })

    # Create the PDF document.
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    # Title
    pdf.cell(200, 10, txt="Salary Variance Report", ln=True, align="C")
    pdf.ln(10)
    # Dynamic summary
    pdf.multi_cell(0, 10, txt=summary)
    pdf.ln(10)
    # Breakdown section
    pdf.multi_cell(0, 10, txt="Breakdown:")
    for entry in breakdown:
        pdf.multi_cell(0, 10, txt=f"Department: {entry['department']}, Reason: {entry['reason']}")
    
    # Save PDF to a BytesIO object.
    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)

    # Return the PDF as a streaming response.
    return StreamingResponse(
        pdf_output,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=SalaryVarianceReport.pdf"}
    )
