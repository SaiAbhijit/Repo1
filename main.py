from fastapi import FastAPI, File, UploadFile, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import pandas as pd
import io
from datetime import datetime
from fpdf import FPDF

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AI Summary generation function
def generate_summary(df):
    summary_lines = []
    overall_change = df["Current Salary"].sum() - df["Previous Salary"].sum()
    percent_change = (overall_change / df["Previous Salary"].sum()) * 100 if df["Previous Salary"].sum() else 0
    summary_lines.append(f"Total salary change: ₹{overall_change:,.2f} ({percent_change:.2f}%)\n")

    for dept in df["Department"].unique():
        dept_df = df[df["Department"] == dept]
        change = dept_df["Current Salary"].sum() - dept_df["Previous Salary"].sum()
        pct = (change / dept_df["Previous Salary"].sum()) * 100 if dept_df["Previous Salary"].sum() else 0
        summary_lines.append(f"{dept}: ₹{change:,.2f} ({pct:.2f}%)\n")

    return "".join(summary_lines)

# PDF creation function
def create_pdf(summary: str, df: pd.DataFrame):
    pdf = FPDF()

    # Add a page
    pdf.add_page()

    # Set the font to a default Arial font
    pdf.set_font("Arial", size=12)

    # Title with summary
    pdf.multi_cell(0, 10, f"Salary Variance Summary - {datetime.now().strftime('%Y-%m-%d')}\n\n")

    # Set the font again for the summary section
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, summary)

    # Add another page for table data
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    # Define column widths
    col_widths = [30, 40, 40, 30, 30, 30]
    headers = ["Employee ID", "Name", "Department", "Previous Salary", "Current Salary", "Bonus"]

    # Add headers
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, 1)
    pdf.ln()

    # Add data rows
    for _, row in df.iterrows():
        values = [
            str(row.get("Employee ID", "")),
            str(row.get("Name", "")),
            str(row.get("Department", "")),
            f"{row.get('Previous Salary', 0):,.2f}",
            f"{row.get('Current Salary', 0):,.2f}",
            f"{row.get('Bonus', 0):,.2f}"
        ]
        for i, value in enumerate(values):
            pdf.cell(col_widths[i], 10, value, 1)
        pdf.ln()

    # Output the PDF to a byte stream
    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)
    return output

# Root endpoint to check if the service is live
@app.get("/")
def root():
    return {"message": "AI Salary Tool is live."}

# Endpoint to download the salary variance report
@app.post("/download-report")
def download_report(file: UploadFile = File(...)):
    try:
        # Read the file content
        contents = file.file.read()
        df = pd.read_excel(io.BytesIO(contents))

        # Check if required columns are present
        required_columns = ["Employee ID", "Name", "Department", "Previous Salary", "Current Salary"]
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        # Convert data columns to numeric, filling invalid values with 0
        df["Bonus"] = df.get("Bonus", 0)
        df["Previous Salary"] = pd.to_numeric(df["Previous Salary"], errors='coerce').fillna(0)
        df["Current Salary"] = pd.to_numeric(df["Current Salary"], errors='coerce').fillna(0)
        df["Bonus"] = pd.to_numeric(df["Bonus"], errors='coerce').fillna(0)

        # Generate the AI summary
        summary = generate_summary(df)

        # Create the PDF report with the summary and data
        pdf = create_pdf(summary, df)

        # Return the PDF as a streaming response for download
        return StreamingResponse(pdf, media_type="application/pdf", headers={
            "Content-Disposition": f"attachment; filename=salary_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        })

    except Exception as e:
        import logging
        logging.error(f"Error processing request: {e}")
        return Response(content=f"500 Internal Server Error\n\n{str(e)}", status_code=500)
