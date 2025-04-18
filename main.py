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

def generate_summary(df):
    try:
        prompt = "You are an HR analyst. Analyze the following salary data:\n\n"
        summary_table = df[["Department", "Previous Salary", "Current Salary", "Bonus"]].groupby("Department").sum().reset_index()
        prompt += summary_table.to_string(index=False)
        prompt += "\n\nWrite a concise, insightful summary highlighting trends and changes in less than 100 words. Include observations on total salary, bonus variations, and department-level differences."

        if openai.api_key:
            logging.info("Using OpenAI for AI-generated summary.")  # Add this log to confirm API call
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300
            )
            logging.info("AI summary generated successfully.")  # Confirmation of successful AI summary generation
            return response.choices[0].message.content.strip()
        else:
            logging.warning(" OpenAI API key not set.")  # Log if API key is not set
            raise ValueError("OpenAI API key not set.")
    except Exception as e:
        logging.error(f"Error generating AI summary: {e}")  # Log the error if something goes wrong
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
            f"Rs {row.get('Previous Salary', 0):,.2f}",
            f"Rs {row.get('Current Salary', 0):,.2f}",
            f"Rs {row.get('Bonus', 0):,.2f}"
        ]
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
def download_report(file: UploadFile = File(...)):
    try:
        contents = file.file.read()
        df = pd.read_excel(io.BytesIO(contents))

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
        import logging
        logging.error(f"Error processing request: {e}")
        return Response(content=f"500 Internal Server Error\n\n{str(e)}", status_code=500)
