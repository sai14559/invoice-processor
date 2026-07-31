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

# --- UI Header ---
try:
    st.image("logo.jfif.jfif", width=200)
except:
    pass

st.title("Bulk Invoice Processor & Celigo Sync")

# --- Helper Functions ---
def find_field(text, patterns, default="N/A"):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return default

def process_pdf_content(file_bytes, filename):
    try:
        with pdfplumber.open(file_bytes) as pdf:
            # We join the first 2 pages to get header/footer info
            full_text = "\n".join([page.extract_text() for page in pdf.pages[:2] if page.extract_text()])
            
            # --- EXTRACTING FIELDS ---
            order_number = find_field(full_text, [r"(?:Order\s*Number|Order\s*#)\s*[:\s]*([\w-]+)"])
            customer_number = find_field(full_text, [r"(?:Customer\s*Number|Account\s*#)\s*[:\s]*([\w-]+)"])
            description = find_field(full_text, [r"(?:Description)\s*[:\s]*(.*)"])
            coo = find_field(full_text, [r"(?:COO|Country\s*of\s*Origin)\s*[:\s]*([\w\s]+)"])
            material = find_field(full_text, [r"(?:Material)\s*[:\s]*([\w-]+)"])
            item = find_field(full_text, [r"(?:Item)\s*[:\s]*([\w-]+)"])
            quantity = find_field(full_text, [r"(?:Quantity|Qty)\s*[:\s]*([\d]+)"])
            public_price = find_field(full_text, [r"(?:Public\s*Price)\s*[:\s]*\$?\s*([\d,]+\.\d{2})"])
            discount = find_field(full_text, [r"(?:Discount)\s*[:\s]*([\d]+%)"])
            subtotal = find_field(full_text, [r"(?:Subtotal)\s*[:\s]*\$?\s*([\d,]+\.\d{2})"], default="0.00")
            total_amount = find_field(full_text, [
                r"(?:Total\s*Amount|Grand\s*Total|Total)\s*[:\s]*\$?\s*([\d,]+\.\d{2})"
            ], default="0.00")
            date = find_field(full_text, [r"(?:Date)\s*[:\s]*\s*([\d\/\-\.]{8,10})"])
            
            return {
                "File Name": filename,
                "Order Number": order_number,
                "Customer Number": customer_number,
                "Description": description,
                "COO": coo,
                "Material": material,
                "Item": item,
                "Quantity": quantity,
                "Public Price": public_price.replace(",", ""),
                "Discount": discount,
                "Subtotal": subtotal.replace(",", ""),
                "Total Amount": total_amount.replace(",", ""),
                "Date": date
            }
    except Exception as e:
        return {"File Name": filename, "Error": f"Extraction Failed: {str(e)}"}

# --- Step 1: Processing ---
uploaded_files = st.file_uploader("Upload PDF or ZIP files", type=["pdf", "zip"], accept_multiple_files=True)

if uploaded_files and st.button("Step 1: Process Files"):
    all_data = []
    with st.spinner("Extracting data..."):
        for uploaded_file in uploaded_files:
            if uploaded_file.name.endswith(".zip"):
                with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                    for name in zip_ref.namelist():
                        if name.lower().endswith(".pdf"):
                            pdf_bytes = io.BytesIO(zip_ref.read(name))
                            all_data.append(process_pdf_content(pdf_bytes, name))
            else:
                all_data.append(process_pdf_content(uploaded_file, uploaded_file.name))
    
    st.session_state.extracted_data = all_data
    st.rerun()

# --- Step 2: Display & Send ---
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
