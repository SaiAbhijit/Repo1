from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
import pandas as pd
import numpy as np
from io import BytesIO
from fpdf import FPDF

app = FastAPI()

# Allow all CORS origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/download-report")
async def download_report(file: UploadFile = File(...)):
    try:
        # Read and load Excel data
        content = await file.read()
        df = pd.read_excel(BytesIO(content))

        if 'Salary' not in df.columns or 'Previous Salary' not in df.columns:
            return JSONResponse(status_code=400, content={"error": "Required columns 'Salary' and 'Previous Salary' not found."})

        # Core Calculations
        total_salary_current = df['Salary'].sum()
        total_salary_previous = df['Previous Salary'].sum()
        salary_diff = total_salary_current - total_salary_previous
        percent_change = (salary_diff / total_salary_previous) * 100 if total_salary_previous != 0 else 0

        # Generate natural language summary
        direction = "increased" if salary_diff > 0 else "decreased"
        summary = f"The total salary payout has {direction} by {abs(salary_diff):,.2f} ({abs(percent_change):.2f}%) compared to the previous month."

        # Identify related columns
        breakdown = []
        if 'Department' in df.columns:
            for dept in df['Department'].unique():
                sub_df = df[df['Department'] == dept]
                sub_salary_change = sub_df['Salary'].sum() - sub_df['Previous Salary'].sum()
                direction = "increased" if sub_salary_change > 0 else "decreased"
                breakdown.append(f"Department: {dept} - Salary {direction} by {abs(sub_salary_change):,.2f}.")

        # Include any other numeric columns for summary
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        metric_summary = "\n".join([
            f"Average {col}: {df[col].mean():,.2f}, Max: {df[col].max():,.2f}, Min: {df[col].min():,.2f}"
            for col in numeric_cols if col not in ['Salary', 'Previous Salary']
        ])

        # Create PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Salary Variance Report", ln=True, align="C")
        pdf.ln(10)
        pdf.multi_cell(0, 10, summary)

        if breakdown:
            pdf.ln(5)
            pdf.multi_cell(0, 10, "Department-wise Breakdown:")
            for item in breakdown:
                pdf.multi_cell(0, 10, item)

        if metric_summary:
            pdf.ln(5)
            pdf.multi_cell(0, 10, "Other Metric Summary:")
            pdf.multi_cell(0, 10, metric_summary)

        # Prepare response
        pdf_output = BytesIO()
        pdf.output(pdf_output)
        pdf_output.seek(0)

        return StreamingResponse(pdf_output, media_type="application/pdf", headers={
            "Content-Disposition": "attachment; filename=SalaryVarianceReport.pdf"
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
