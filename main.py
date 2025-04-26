from fastapi import FastAPI, File, UploadFile, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import pandas as pd
import io
import os
from fpdf import FPDF
from datetime import datetime
import openai
import logging

# Set up logging (add this near the start of your script)
logging.basicConfig(level=logging.INFO)
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def generate_summary(df, selected_columns):
    try:
        # Ensure 'Department' is included for grouping if it's not in selected_columns
        if "Department" not in selected_columns:
            selected_columns = ["Department"] + selected_columns
        
        summary_table = df[selected_columns].groupby("Department").sum().reset_index()
        
        prompt = (
            "You are an HR data analyst. ONLY analyze the data given below.\n"
            "Do not invent or assume anything outside of the data shown.\n"
            f"Columns provided: {', '.join(selected_columns)}\n\n"
            + summary_table.to_string(index=False) +
            "\n\nWrite a clear and concise summary under 100 words. Highlight department-wise changes and total values if relevant."
        )
        
        if openai.api_key:
            logging.info("Using OpenAI for AI-generated summary.")
            response = openai.ChatCompletion.create(
                model="gpt-4-turbo",
                messages=[ 
                    {"role": "system", "content": "You are a precise HR analyst. Never invent information."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300
            )
            logging.info("AI summary generated successfully.")
            return response.choices[0].message.content.strip()
        else:
            logging.warning("OpenAI API key not set.")
            raise ValueError("OpenAI API key not set.")
    except Exception as e:
        logging.error(f"Error generating AI summary: {e}")
        # Fallback logic in case of error
        fallback_summary_lines = []
        overall_change = df["Current Salary"].sum() - df["Previous Salary"].sum()
        percent_change = (overall_change / df["Previous Salary"].sum()) * 100 if df["Previous Salary"].sum() else 0
        bonus_total = df["Bonus"].sum()
        fallback_summary_lines.append(f"Total salary change: Rs {overall_change:,.2f} ({percent_change:.2f}%)\n")
        fallback_summary_lines.append(f"Total bonuses awarded: Rs {bonus_total:,.2f}\n")

        for dept in df["Department"].unique():
            dept_df = df[df["Department"] == dept]
            change = dept_df["Current Salary"].sum() - dept_df["Previous Salary"].sum()
            pct = (change / dept_df["Previous Salary"].sum()) * 100 if dept_df["Previous Salary"].sum() else 0
            dept_bonus = dept_df["Bonus"].sum()
            fallback_summary_lines.append(f"{dept}: Rs {change:,.2f} ({pct:.2f}%), Bonus: Rs {dept_bonus:,.2f}\n")

        return "".join(fallback_summary_lines)

def create_pdf(summary: str, df: pd.DataFrame):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, f"Salary Variance Summary - {datetime.now().strftime('%Y-%m-%d')}\n\n")
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, summary)

    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Dynamically set column headers and widths based on dataframe columns
    headers = df.columns.tolist()
    col_widths = [max(len(str(col)), 30) for col in headers]  # Adjust widths based on column name length
    
    # Add headers
    for header in headers:
        pdf.cell(col_widths[headers.index(header)], 10, header, 1)
    pdf.ln()

    # Add rows
    for _, row in df.iterrows():
        values = [str(row.get(col, "")) for col in headers]
        for i, value in enumerate(values):
            pdf.cell(col_widths[i], 10, value, 1)
        pdf.ln()

    output = io.BytesIO()
    pdf_output = pdf.output(dest='S').encode('latin-1')
    output.write(pdf_output)
    output.seek(0)
    return output

@app.get("/")
def root():
    return {"message": "AI Salary Tool is live."}

@app.post("/download-report")
async def download_report(file: UploadFile = File(...), selected_columns: list = ["Department", "Previous Salary", "Current Salary", "Bonus"]):
    try:
        contents = await file.read()  # Ensure file is read as a byte object
        df = pd.read_excel(io.BytesIO(contents))

        required_columns = ["Employee ID", "Name", "Department", "Previous Salary", "Current Salary"]
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        df["Bonus"] = df.get("Bonus", 0)
        df["Previous Salary"] = pd.to_numeric(df["Previous Salary"], errors='coerce').fillna(0)
        df["Current Salary"] = pd.to_numeric(df["Current Salary"], errors='coerce').fillna(0)
        df["Bonus"] = pd.to_numeric(df["Bonus"], errors='coerce').fillna(0)

        summary = generate_summary(df, selected_columns)
        pdf = create_pdf(summary, df)

        return StreamingResponse(pdf, media_type="application/pdf", headers={
            "Content-Disposition": f"attachment; filename=salary_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        })

    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return Response(content=f"500 Internal Server Error\n\n{str(e)}", status_code=500)
