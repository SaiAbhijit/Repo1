from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
import pandas as pd
from io import BytesIO
import os
from typing import List, Optional
from io import StringIO

app = FastAPI()

# Define required columns
REQUIRED_COLUMNS = ['Employee ID', 'Employee Name', 'Department', 'Salary']

# Function to generate a natural language summary
def generate_summary(df: pd.DataFrame):
    summary = []
    total_employees = len(df)
    total_salary = df['Salary'].sum()
    avg_salary = df['Salary'].mean()

    summary.append(f"Total employees: {total_employees}")
    summary.append(f"Total salary expense: {total_salary:,.2f}")
    summary.append(f"Average salary: {avg_salary:,.2f}")

    if 'Bonus' in df.columns:
        total_bonus = df['Bonus'].sum()
        avg_bonus = df['Bonus'].mean()
        summary.append(f"Total bonuses: {total_bonus:,.2f}")
        summary.append(f"Average bonus: {avg_bonus:,.2f}")
    
    return "\n".join(summary)

@app.post("/upload-excel/")
async def upload_excel(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))

        # Check for missing required columns
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                raise HTTPException(status_code=400, detail=f"Missing required column: {col}")
        
        # Validate data types and preprocess if needed
        df['Salary'] = pd.to_numeric(df['Salary'], errors='coerce')
        if 'Bonus' in df.columns:
            df['Bonus'] = pd.to_numeric(df['Bonus'], errors='coerce')

        # Generate natural language summary
        summary = generate_summary(df)

        # Return summary in response
        return {
            "summary": summary,
            "data": df.to_dict(orient="records")  # Return data in case further use is required
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/download-report/")
async def download_report(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))

        # Check for missing required columns
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                raise HTTPException(status_code=400, detail=f"Missing required column: {col}")
        
        # Validate data types and preprocess if needed
        df['Salary'] = pd.to_numeric(df['Salary'], errors='coerce')
        if 'Bonus' in df.columns:
            df['Bonus'] = pd.to_numeric(df['Bonus'], errors='coerce')

        # Generate natural language summary
        summary = generate_summary(df)

        # Export data to Excel and return for download
        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)

        return {
            "summary": summary,
            "file": output.read()  # This will allow the file to be downloaded
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
