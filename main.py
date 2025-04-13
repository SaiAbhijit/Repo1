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

@app.post("/download-report")
async def download_report(file: UploadFile = File(...)):
    # Read the file content and load it into a DataFrame
    content = await file.read()
    df = pd.read_excel(BytesIO(content))

    # Automatically detect and handle columns
    expected_columns = ['Salary', 'Previous Salary', 'Bonus', 'Previous Bonus', 'Department']
    salary_columns = [col for col in expected_columns if col in df.columns]

    # Calculate total salary and bonus if columns exist
    total_salary_current = df['Salary'].sum() if 'Salary' in df.columns else 0
    total_salary_previous = df['Previous Salary'].sum() if 'Previous Salary' in df.columns else 0
    total_bonus_current = df['Bonus'].sum() if 'Bonus' in df.columns else 0
    total_bonus_previous = df['Previous Bonus'].sum() if 'Previous Bonus' in df.columns else 0

    # Calculate total variance and change
    total_current = total_salary_current + total_bonus_current
    total_previous = total_salary_previous + total_bonus_previous
    salary_variance = total_current - total_previous
    salary_change_percentage = (salary_variance / total_previous) * 100 if total_previous != 0 else 0

    # Generate a summary based on the data
    summary = f"Total salary payout (including bonus) is {salary_variance:.2f} ({salary_change_percentage:.2f}%) compared to the previous period."

    # Generate breakdown of salary variance reasons based on department (example logic)
    breakdown = []
    departments = df['Department'].unique() if 'Department' in df.columns else ['Unknown']
    
    for dept in departments:
        dept_data = df[df['Department'] == dept]
        dept_salary_change = dept_data['Salary'].sum() - dept_data['Previous Salary'].sum() if 'Salary' in df.columns and 'Previous Salary' in df.columns else 0
        dept_bonus_change = dept_data['Bonus'].sum() - dept_data['Previous Bonus'].sum() if 'Bonus' in df.columns and 'Previous Bonus' in df.columns else 0
        dept_total_change = dept_salary_change + dept_bonus_change
        breakdown.append({
            "department": dept,
            "reason": f"Salary change: {dept_salary_change:.2f}, Bonus change: {dept_bonus_change:.2f}, Total change: {dept_total_change:.2f}"
        })
    
    # Generate the natural language summary
    nl_summary = "The salary variance report indicates the following summary and department-wise breakdown:\n\n"
    nl_summary += summary + "\n\nBreakdown by department:\n"
    
    for entry in breakdown:
        nl_summary += f"Department: {entry['department']}, Reason: {entry['reason']}\n"
    
    # Create PDF document
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Title
    pdf.cell(200, 10, txt="Salary Variance Report", ln=True, align="C")
    pdf.ln(10)  # Add space between title and content
    
    # Add Dynamic Summary to the PDF
    pdf.multi_cell(0, 10, txt=nl_summary)
    
    # Save PDF to BytesIO to serve as a file
    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)

    # Return PDF as a downloadable response
    return StreamingResponse(pdf_output, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=SalaryVarianceReport.pdf"})
