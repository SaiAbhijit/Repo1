from fastapi import FastAPI, File, UploadFile, HTTPException
import pandas as pd
import io
from fpdf import FPDF
import openai
import logging
import os

# Set up logging for debugging and error handling
logging.basicConfig(level=logging.INFO)
openai.api_key = os.getenv("OPENAI_API_KEY")  # Make sure the API key is set correctly

app = FastAPI()

# Function to generate summary using OpenAI GPT-4
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
            return response.choices[0].message['content']
    except Exception as e:
        logging.error(f"Error in generating summary: {e}")
        return "Error in generating summary."

@app.post("/download-report")
async def download_report(file: UploadFile = File(...), selected_columns: list = None):
    try:
        # Read the uploaded file as binary stream
        file_content = await file.read()
        
        # Create a buffer to read the Excel file
        df = pd.read_excel(io.BytesIO(file_content))
        
        # If no columns are selected, return an error
        if not selected_columns:
            raise HTTPException(status_code=400, detail="Please provide the selected columns.")

        # Generate the summary using the columns provided
        summary = generate_summary(df, selected_columns)
        
        # Create a PDF to include the summary and data
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Generated Report", ln=True, align="C")
        pdf.ln(10)
        pdf.multi_cell(0, 10, txt=summary)
        
        # Save the PDF to a buffer
        pdf_output = io.BytesIO()
        pdf.output(pdf_output)
        pdf_output.seek(0)
        
        # Send the PDF as a response
        return StreamingResponse(pdf_output, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=report.pdf"})
    
    except Exception as e:
        logging.error(f"Error processing file: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the file.")
