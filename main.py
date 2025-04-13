from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fpdf import FPDF
import pandas as pd
from io import BytesIO
import logging

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.DEBUG)

@app.post("/download-report")
async def download_report(file: UploadFile = File(...)):
    try:
        # Read the file content
        content = await file.read()
        df = pd.read_excel(BytesIO(content))

        # Verify that the required columns exist in the uploaded data
        required_columns = ['Employee ID', 'Department', 'Salary', 'Previous Salary', 'Bonus']  # Example required columns
        for col in required_columns:
            if col not in df.columns:
                raise HTTPException(status_code=400, detail=f"Missing required column: {col}")

        # Calculate summary based on salary variance
        total_salary_current = df['Salary'].sum()
        total_salary_previous = df['Previous Salary'].sum()
        salary_variance = total_salary_current - total_salary_previous
        salary_change_percentage = (salary_variance / total_salary_previous) * 100 if total_salary_previous != 0 else 0
        
        # Generate a summary based on the data
        summary = f"Total salary payout is {salary_variance:.2f} ({salary_change_percentage:.2f}%) compared to the previous month."
        
        # Generate breakdown of salary variance reasons based on department (example logic)
        breakdown = []
        departments = df['Department'].unique()
        
        for dept in departments:
            dept_data = df[df['Department'] == dept]
            dept_salary_change = dept_data['Salary'].sum() - dept_data['Previous Salary'].sum()
            breakdown.append({
                "department": dept,
                "reason": f"Salary change: {dept_salary_change:.2f}"
            })

        # Create PDF document
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        # Title
        pdf.cell(200, 10, txt="Salary Variance Report", ln=True, align="C")
        pdf.ln(10)  # Add space between title and content
        
        # Add Dynamic Summary to the PDF
        pdf.multi_cell(0, 10, txt=summary)
        
        # Add Breakdown of Salary Variance to the PDF
        pdf.ln(10)  # Add space before breakdown
        pdf.multi_cell(0, 10, txt="Breakdown:")
        
        for entry in breakdown:
            pdf.multi_cell(0, 10, txt=f"Department: {entry['department']}, Reason: {entry['reason']}")
        
        # Save PDF to BytesIO to serve as a file
        pdf_output = BytesIO()
        pdf.output(pdf_output)
        pdf_output.seek(0)

        # Return PDF as a downloadable response
        return StreamingResponse(pdf_output, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=SalaryVarianceReport.pdf"})
    
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error occurred")
