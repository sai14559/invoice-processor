import re
import pdfplumber
import streamlit as st
import pandas as pd
import zipfile
import io
import requests

# --- Configuration ---
st.set_page_config(page_title="Invoice Processor", layout="wide")

if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = None

# --- UI ---
try:
    st.image("logo.jfif.jfif", width=200)
except:
    pass

st.title("Bulk Invoice Processor & Celigo Sync")

# --- Helper Functions ---
def find_field(text, patterns):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return "0.00"

def process_pdf_content(file_bytes, filename):
    try:
        with pdfplumber.open(file_bytes) as pdf:
            # Join text from all pages
            full_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
            
            # Expanded search patterns to catch more formats
            total_str = find_field(full_text, [
                r"(?:Total|Credit|Balance|Amount Due|Grand Total)\s*[:\s]*\$?\s*([\d,]+\.\d{2})",
                r"(?:Total|Credit|Balance|Amount Due|Grand Total)\s*[\w\s]*\$?\s*([\d,]+\.\d{2})"
            ])
            
            invoice_num = find_field(full_text, [r"(?:Invoice|Credit Note|Document)\s*Number\s*[|:]?\s*([\w-]+)", r"Number\s*[|:]?\s*([\w-]+)"])
            po_num = find_field(full_text, [r"PO\s*Number\s*[|:]?\s*([\w-]+)", r"Purchase Order\s*[|:]?\s*([\w-]+)"])
            
            return {
                "File Name": filename,
                "Invoice Number": invoice_num,
                "PO Number": po_num,
                "Total Amount": total_str.replace(",", "")
            }
    except Exception as e:
        return {"File Name": filename, "Error": f"Extraction Failed: {str(e)}"}

# --- Process Logic ---
uploaded_files = st.file_uploader("Upload PDF or ZIP files", type=["pdf", "zip"], accept_multiple_files=True)

if uploaded_files and st.button("Step 1: Process Files"):
    all_data = []
    with st.spinner("Extracting data..."):
        for uploaded_file in uploaded_files:
            # Handle ZIP files
            if uploaded_file.name.endswith(".zip"):
                with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                    # List all files, even in subdirectories
                    for name in zip_ref.namelist():
                        # We try to process ANY file that looks like a PDF
                        if name.lower().endswith(".pdf"):
                            pdf_bytes = io.BytesIO(zip_ref.read(name))
                            all_data.append(process_pdf_content(pdf_bytes, name))
            # Handle standard PDFs
            else:
                all_data.append(process_pdf_content(uploaded_file, uploaded_file.name))
    
    st.session_state.extracted_data = all_data
    st.rerun()

# --- Display & Send ---
if st.session_state.extracted_data:
    st.subheader("Extracted Data Preview")
    df = pd.DataFrame(st.session_state.extracted_data)
    st.table(df)
    
    if st.button("Step 2: Send to Celigo"):
        webhook_url = "https://api.integrator.io/v1/exports/6a3e22e548c8b4a733fbeb15/KVk2DW2JtJkffDcxDfAx0o2S0mwcSyXP/data"
        with st.spinner("Sending to Celigo..."):
            try:
                response = requests.post(webhook_url, json=st.session_state.extracted_data)
                if response.status_code in [200, 202, 204]:
                    st.success("Successfully sent all data to Celigo!")
                else:
                    st.error(f"Failed. Status Code: {response.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")
