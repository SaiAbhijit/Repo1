from fastapi import FastAPI, File, UploadFile, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import pandas as pd
import io
import os
from fpdf import FPDF
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AI-driven summary generator
def generate_ai_summary(df):
    summary_lines = []
    total_salary_change = df["Current Salary"].sum() - df["Previous Salary"].sum()
    total_previous_salary = df["Previous Salary"].sum()
    overall_change_percentage = (total_salary_change / total_previous_salary) * 100 if total_previous_salary else 0
    
    summary_lines.append(f"Overall salary change: ₹{total_salary_change:,.2f} ({overall_change_percentage:.2f}%)\n")

    # Analyzing departments and salary trends
    for dept in df["Department"].unique():
        dept_df = df[df["Department"] == dept]
        dept_salary_change = dept_df["Current Salary"].sum() - dept_df["Previous Salary"].sum()
        dept_previous_salary = dept_df["Previous Salary"].sum()
        dept_percentage_change = (dept_salary_change / dept_previous_salary) * 100 if dept_previous_salary else 0
        
        summary_lines.append(f"Department: {dept}\n")
        summary_lines.append(f"  - Salary Change: ₹{dept_salary_change:,.2f} ({dept_percentage_change:.2f}%)\n")
        
        # AI-driven insights on potential salary imbalances
        avg_current_salary = dept_df["Current Salary"].mean()
        avg_previous_salary = dept_df["Previous Salary"].mean()
        if avg_current_salary > avg_previous_salary:
            summary_lines.append(f"  - The department has experienced an overall salary increase.\n")
        elif avg_current_salary < avg_previous_salary:
            summary_lines.append(f"  - The department has experienced a decrease in salary on average.\n")
        else:
            summary_lines.append(f"  - Salary remains stable on average.\n")
        
    return "".join(summary_lines)

# Dynamic PDF creator
def create_pdf(summary: str, df: pd.DataFrame):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, f"Salary Variance Summary - {datetime.now().strftime('%Y-%m-%d')}\n\n")
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, summary)

    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Dynamically fetch column names for the table
    columns = df.columns.tolist()
    col_widths = [max([len(str(val)) for val in df[col]]) * 5 for col in columns]  # Adjusting column width dynamically

    # Table headers
    for col in columns:
        pdf.cell(col_widths[columns.index(col)], 10, col, 1)
    pdf.ln()

    # Table data
    for _, row in df.iterrows():
        for col in columns:
            pdf.cell(col_widths[columns.index(col)], 10, str(row[col]), 1)
        pdf.ln()

    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)
    return output

@app.get("/")
def root():
    return {"message": "AI Salary Tool is live."}

@app.post("/download-report")
def download_report(file: UploadFile = File(...)):
    try:
        contents = file.file.read()
        df = pd.read_excel(io.BytesIO(contents))

        # Ensure that necessary columns exist
        required_columns =_
