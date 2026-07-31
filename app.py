import streamlit as st
import os
import re
import pdfplumber
import pandas as pd

# --- Logic Functions ---
def classify_document(filename, text):
    name_lower = filename.lower()
    if "credit" in name_lower:
        return "Credit Invoice"
    if "po" in name_lower or re.search(r'\d{8}$', os.path.splitext(filename)[0]):
        return "Invoice (with PO)"
    return "Invoice"

def extract_details(text):
    data = {"invoice_number": "N/A", "po_number": "N/A", "total_amount": "N/A"}
    inv_match = re.search(r"(?:Invoice|Credit Note)\s*[:#]?\s*(\d{10})", text, re.IGNORECASE)
    po_match = re.search(r"(?:PO|Purchase Order|P\.O\.)\s*[:#]?\s*(\d{8,})", text, re.IGNORECASE)
    total_match = re.search(r"(?:Total|Amount Due)\s*[:\$\s]*([\d,\.]+)", text, re.IGNORECASE)
    
    if inv_match: data["invoice_number"] = inv_match.group(1)
    if po_match: data["po_number"] = po_match.group(1)
    if total_match: data["total_amount"] = total_match.group(1)
    return data

# --- Streamlit UI ---
st.set_page_config(page_title="Nilfisk Invoice Processor", layout="wide")
st.title("Nilfisk Invoice Processor")

input_folder = "./invoices"

if st.button("Process Invoices"):
    if not os.path.exists(input_folder):
        st.error(f"Folder '{input_folder}' not found. Please ensure it exists in your repository.")
    else:
        results = []
        files = [f for f in os.listdir(input_folder) if f.endswith(".pdf")]
        
        if not files:
            st.warning("No PDF files found in the 'invoices' folder.")
        else:
            with st.spinner('Processing PDFs...'):
                for filename in files:
                    file_path = os.path.join(input_folder, filename)
                    full_text = ""
                    with pdfplumber.open(file_path) as pdf:
                        for page in pdf.pages:
                            full_text += page.extract_text() or ""
                    
                    doc_type = classify_document(filename, full_text)
                    details = extract_details(full_text)
                    results.append({
                        "Filename": filename,
                        "Document Type": doc_type,
                        "Invoice #": details["invoice_number"],
                        "PO #": details["po_number"],
                        "Total": details["total_amount"]
                    })
            
            df = pd.DataFrame(results)
            st.success(f"Successfully processed {len(results)} files!")
            st.dataframe(df, use_container_width=True)
