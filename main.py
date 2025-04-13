from fastapi import FastAPI, File, UploadFile, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import pandas as pd
import io
from fpdf import FPDF
from datetime import datetime

app = FastAPI()

# CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Function to generate salary variance summary
def generate_summary(df):
    summary_lines = []
    overall_change = df["Current Salary"].sum() - df["Previous Salary"].sum()
    percent_change = (overall_change / df["Previous Salary"].sum()) * 100 if df["Previous Salary"].sum() else 0
    summary_lines.append(f"Total salary change: ₹{overall_change:,.2f} ({percent_change:.2f}%)\n")

    # Calculate change per department
    for dept in df["Department"].unique():
        dept_df = df[df["Department"] == dept]
        change = dept_df["Current Salary"].sum() - dept_df["Previous Salary"].sum()
        pct = (change / dept_df["Previous Salary"].sum()) * 100 if dept_df["Previous Salary"].sum() else 0
        summary_lines.append(f"{dept}: ₹{change:,.2f} ({pct:.2f}%)\n")

    return "".join(summary_lines)

# Function to create the PDF report
def create_pdf(summary: str, df: pd.DataFrame):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12, encoding='UTF-8')
    pdf.multi_cell(0, 10, f"Salary Variance Summary - {datetime.now().strftime('%Y-%m-%d')}\n\n")
    pdf.set_font("Arial", size=10, encoding='UTF-8')
    pdf.multi_cell(0, 10, summary)

    pdf.add_page()
    pdf.set_font("Arial", size=10, encoding='UTF-8')
    col_widths = [30, 40, 40, 30, 30, 30]
    headers = ["Employee ID", "Name", "Department", "Previous Salary", "Current Salary", "Bonus"]

    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, 1)
    pdf.ln()

    for _, row in df.iterrows():
        values = [
            str(row.get("Employee ID", "")),
            str(row.get("Name", "")),
            str(row.get("Department", "")),
            f"₹{row.get('Previous Salary', 0):,.2f}",
            f"₹{row.get('Current Salary', 0):,.2f}",
            f"₹{row.get('Bonus', 0):,.2f}"
        ]
        for i, value in enumerate(values):
            pdf.cell(col_widths[i], 10, value, 1)
        pdf.ln()

    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)
    return output

# Root endpoint for health check
@app.get("/")
def root():
    return {"message": "AI Salary Tool is live."}

# Endpoint to handle file upload and download salary report
@app.post("/download-report")
def download_report(file: UploadFile = File(...)):
    try:
        contents = file.file.read()
        df = pd.read_excel(io.BytesIO(contents))

        # Check for required columns
        required_columns = ["Employee ID", "Name", "Department", "Previous Salary", "Current Salary"]
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        # Convert necessary columns to numeric values
        df["Bonus"] = df.get("Bonus", 0)
        df["Previous Salary"] = pd.to_numeric(df["Previous Salary"], errors='coerce').fillna(0)
        df["Current Salary"] = pd.to_numeric(df["Current Salary"], errors='coerce').fillna(0)
        df["Bonus"] = pd.to_numeric(df["Bonus"], errors='coerce').fillna(0)

        # Generate AI summary and create PDF
        summary = generate_summary(df)
        pdf = create_pdf(summary, df)

        return StreamingResponse(pdf, media_type="application/pdf", headers={
            "Content-Disposition": f"attachment; filename=salary_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        })

    except Exception as e:
        import logging
        logging.error(f"Error processing request: {e}")
        return Response(content=f"500 Internal Server Error\n\n{str(e)}", status_code=500)
