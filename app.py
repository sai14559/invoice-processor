import re
import pdfplumber
import streamlit as st
import pandas as pd
import zipfile
import io
import requests

# --- Configuration ---
st.set_page_config(page_title="Invoice Processor", layout="wide")

# --- UI Header ---
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
    return "0.00" # Default to 0.00 if not found

def process_pdf_content(file_bytes, filename):
    """Parses PDF bytes and extracts data."""
    with pdfplumber.open(file_bytes) as pdf:
        full_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        
        # Enhanced Regex for Amount
        total_str = find_field(full_text, [
            r"(?:Total|Credit|Balance|Amount Due)\s*[:\s]*\$?\s*([\d,]+\.\d{2})",
            r"(?:Total|Credit|Balance|Amount Due)\s*[\w\s]*\$?\s*([\d,]+\.\d{2})"
        ])
        
        invoice_num = find_field(full_text, [r"(?:Invoice|Credit Note|Document)\s*Number\s*[|:]?\s*([\w-]+)", r"Number\s*[|:]?\s*([\w-]+)"])
        po_num = find_field(full_text, [r"PO\s*Number\s*[|:]?\s*([\w-]+)", r"Purchase Order\s*[|:]?\s*([\w-]+)"])
        
        return {
            "File Name": filename,
            "Invoice Number": invoice_num,
            "PO Number": po_num,
            "Total Amount": total_str.replace(",", "")
        }

# --- Main UI ---
webhook_url = st.text_input("Enter Celigo Webhook URL")
uploaded_files = st.file_uploader("Upload PDF or ZIP files", type=["pdf", "zip"], accept_multiple_files=True)

if uploaded_files and st.button("Process & Send to Celigo"):
    all_data = []
    
    with st.spinner("Processing files..."):
        for uploaded_file in uploaded_files:
            # Handle ZIP files
            if uploaded_file.name.endswith(".zip"):
                with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                    for name in zip_ref.namelist():
                        if name.endswith(".pdf"):
                            pdf_bytes = io.BytesIO(zip_ref.read(name))
                            all_data.append(process_pdf_content(pdf_bytes, name))
            # Handle standard PDFs
            else:
                all_data.append(process_pdf_content(uploaded_file, uploaded_file.name))

    # Display Results
    df = pd.DataFrame(all_data)
    st.table(df)

    # Celigo Send Logic
    if webhook_url:
        try:
            response = requests.post(webhook_url, json=all_data)
            if response.status_code == 200:
                st.success("Successfully sent data to Celigo!")
            else:
                st.error(f"Failed to send to Celigo. Status Code: {response.status_code}")
        except Exception as e:
            st.error(f"Error connecting to Celigo: {e}")
    else:
        st.warning("Please enter a Webhook URL to send data to Celigo.")
