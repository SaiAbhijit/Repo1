from fastapi import FastAPI, File, UploadFile, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import pandas as pd
import io
import os
import openai
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

    for standard_col, possible_names in column_mappings.items():
        for name in possible_names:
            if name in df.columns:
                df.rename(columns={name: standard_col}, inplace=True)

    return df

def generate_summary(df: pd.DataFrame) -> str:
    """ AI-driven summary with insights and anomalies """
    try:
        prompt = "You are an expert HR analyst. Analyze the following salary data and provide insights:\n\n"
        prompt += df.groupby("Department
