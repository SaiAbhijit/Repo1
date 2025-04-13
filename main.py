from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
from io import BytesIO
from fastapi.responses import StreamingResponse
from fpdf import FPDF

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/download-report")
async def download_report(file: UploadFile = File(...)):
    try:
        content = await file.read()
        df = pd.read_excel(BytesIO(content))

        if df.empty:
            return {"error": "Uploaded file is empty or invalid."}

        # Identify numerical columns for analysis
        numeric_cols = df.select_dtypes(include=np.number).columns.tolist()

        # Detect month-to-month comparison columns
        current_cols = [col for col in numeric_cols if "Current" in col or "Salary" in col or "Now" in col]
        previous_cols = [col for col in numeric_cols if "Previous" in col or "Last" in col or "Before" in col]

        summary_lines = []
        breakdown = []

        for curr_col in current_cols:
            matched_prev = None
            for prev_col in previous_cols:
                if prev_col.split()[0] in curr_col:
                    matched_prev = prev_col
                    break

            if matched_prev:
                diff = df[curr_col].sum() - df[matched_prev].sum()
                pct = (diff / df[matched_prev].sum()) * 100 if df[matched_prev].sum() != 0 else 0
                summary_lines.append(
                    f"Total change in {curr_col}: {diff:.2f} ({pct:.2f}%) compared to {matched_prev}."
                )

                # Department-wise or group-wise breakdown if available
                if 'Department' in df.columns:
                    departments = df['Department'].unique()
                    for dept in departments:
                        dept_df = df[df['Department'] == dept]
                        dept_diff = dept_df[curr_col].sum() - dept_df[matched_prev].sum()
                        breakdown.append(
                            f"Department: {dept}, Change in {curr_col}: {dept_diff:.2f}"
                        )

        summary_text = "\n".join(summary_lines)
        breakdown_text = "\n".join(breakdown)

        # === PDF Generation ===
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(200, 10, txt="Detailed Salary Variance Report", ln=True, align="C")
        pdf.ln(10)

        pdf.multi_cell(0, 10, txt="Summary:")
        pdf.multi_cell(0, 10, txt=summary_text)
        pdf.ln(10)

        if breakdown_text:
            pdf.multi_cell(0, 10, txt="Breakdown by Department:")
            pdf.multi_cell(0, 10, txt=breakdown_text)

        pdf_output = BytesIO()
        pdf.output(pdf_output)
        pdf_output.seek(0)

        return StreamingResponse(
            pdf_output,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=DetailedSalaryVarianceReport.pdf"},
        )

    except Exception as e:
        return {"error": str(e)}
