from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import pandas as pd
from io import BytesIO
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
        # Read file content and load it into a DataFrame
        content = await file.read()
        df = pd.read_excel(BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail="Error reading Excel file. " + str(e))
    
    # Check for necessary columns – adjust these as needed
    required_columns = ['Salary', 'Previous Salary', 'Department']
    for col in required_columns:
        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"Missing required column: {col}")

    try:
        # Process the data for dynamic summary.
        total_salary_current = df['Salary'].sum()
        total_salary_previous = df['Previous Salary'].sum()
        if total_salary_previous == 0:
            raise HTTPException(status_code=400, detail="Previous salary total cannot be zero.")
        salary_variance = total_salary_current - total_salary_previous
        salary_change_percentage = (salary_variance / total_salary_previous) * 100

        summary = f"Total salary payout change: {salary_variance:.2f} ({salary_change_percentage:.2f}%) compared to the previous month."

        breakdown = []
        for dept in df['Department'].unique():
            dept_data = df[df['Department'] == dept]
            dept_salary_change = dept_data['Salary'].sum() - dept_data['Previous Salary'].sum()
            breakdown.append(f"Department: {dept}, Salary change: {dept_salary_change:.2f}")

        # Generate PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Salary Variance Report", ln=True, align="C")
        pdf.ln(10)
        pdf.multi_cell(0, 10, txt=summary)
        pdf.ln(10)
        pdf.multi_cell(0, 10, txt="Breakdown:")
        for line in breakdown:
            pdf.multi_cell(0, 10, txt=line)

        # Instead of writing to a BytesIO stream directly,
        # get PDF as a string and then encode it.
        pdf_data = pdf.output(dest="S").encode("latin1")  # using 'latin1' as recommended by fpdf docs

        return Response(content=pdf_data,
                        media_type="application/pdf",
                        headers={"Content-Disposition": "attachment; filename=SalaryVarianceReport.pdf"})
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error generating PDF: " + str(e))
