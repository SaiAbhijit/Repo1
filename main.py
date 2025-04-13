from fastapi import FastAPI, File, UploadFile, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import pandas as pd
import io
import os
import openai
from fpdf import FPDF
from datetime import datetime
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

openai.api_key = os.getenv("OPENAI_API_KEY")  # Set your key in environment or replace with your key string

def map_columns(df: pd.DataFrame):
    """ Maps potentially varying column names to standard names """
    column_mappings = {
        "Employee ID": ["Emp ID", "ID"],
        "Name": ["Full Name", "Employee Name"],
        "Department": ["Dept", "Division"],
        "Previous Salary": ["Old Salary", "Base Salary", "Salary 2023"],
        "Current Salary": ["New Salary", "Salary 2024", "Updated Salary"],
        "Bonus": ["Incentive", "Performance Bonus"]
    }
    
    mapped_df = df.copy()
    for standard_col, possible_names in column_mappings.items():
        for name in possible_names:
            if name in df.columns:
                mapped_df.rename(columns={name: standard_col}, inplace=True)

    return mapped_df

def generate_summary(df: pd.DataFrame) -> str:
    """ AI-driven summary with insights and anomalies """
    try:
        prompt = "You are an expert HR analyst. Analyze the following salary data and provide insights:\n\n"
        prompt += df.groupby("Department").agg({
            "Previous Salary": "sum",
            "Current Salary": "sum",
            "Bonus": "sum"
        }).to_string()
        
        prompt += "\n\nIdentify key trends, anomalies, high percentage salary changes, and department-level insights."
        prompt += " Your summary should be detailed but concise, with relevant insights in around 150 words."

        if openai.api_key:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400
            )
            return response.choices[0].message.content.strip()
        else:
            return "AI summary could not be generated due to missing API key."

    except Exception as e:
        return f"Error generating AI summary: {str(e)}"

def create_pdf(summary: str, df: pd.DataFrame):
    """ Generates a PDF report from AI analysis and raw data """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, f"Employee Salary Analysis Report - {datetime.now().strftime('%Y-%m-%d')}\n\n")
    
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, summary)

    pdf.add_page()
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
            pdf.cell(col_widths[i], 10, value.encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.ln()

    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)
    return output

@app.get("/")
def root():
    return {"message": "AI Salary Analysis Tool is live."}

@app.post("/upload-file")
def upload_file(file: UploadFile = File(...)):
    try:
        contents = file.file.read()
        df = pd.read_excel(io.BytesIO(contents))
        df = map_columns(df)

        required_columns = ["Employee ID", "Name", "Department", "Previous Salary", "Current Salary"]
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        df["Bonus"] = df.get("Bonus", 0)
        df["Previous Salary"] = pd.to_numeric(df["Previous Salary"], errors='coerce').fillna(0)
        df["Current Salary"] = pd.to_numeric(df["Current Salary"], errors='coerce').fillna(0)
        df["Bonus"] = pd.to_numeric(df["Bonus"], errors='coerce').fillna(0)

        summary = generate_summary(df)
        pdf = create_pdf(summary, df)

        return StreamingResponse(pdf, media_type="application/pdf", headers={
            "Content-Disposition": f"attachment; filename=salary_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        })

    except Exception as e:
        return Response(content=f"500 Internal Server Error\n\n{str(e)}", status_code=500)

@app.post("/upload-api-data")
def upload_api_data(data: dict):
    """ Allows API-based data ingestion """
    try:
        df = pd.DataFrame(data)
        df = map_columns(df)

        summary = generate_summary(df)
        return {"summary": summary}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
