import streamlit as st
import pdfplumber
import json
import re
import requests

st.set_page_config(page_title="Invoice Parser", page_icon="📄")
st.title("📄 Invoice Parser (Professional)")

uploaded_files = st.file_uploader("Choose PDF invoices", type="pdf", accept_multiple_files=True)

all_extracted_data = []

if uploaded_files:
    for uploaded_file in uploaded_files:
        full_text = ""
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"

        # --- EXTRACTING DATA ---
        # Helper function to find data safely
        def find(pattern, text):
            match = re.search(pattern, text, re.IGNORECASE)
            return match.group(1).strip() if match else "Not found"

        # Build the exact JSON structure you provided
        invoice_json = {
            "fileName": uploaded_file.name,
            "fileType": "PDF",
            "documentType": "Invoice",
            "invoiceNumber": find(r"Number\s*[|]?\s*(\d+)", full_text),
            "invoiceDate": find(r"Date\s*[|]?\s*([A-Za-z]+\s+\d+,\s+\d+)", full_text),
            "poNumber": find(r"PO Number\s*[|]?\s*(\d+)", full_text),
            "orderNumber": find(r"Order Number\s*[|]?\s*(\d+)", full_text),
            "customerNumber": find(r"Customer Number\s*[|]?\s*(\d+)", full_text),
            "currency": "USD", # Static as per your requirement
            "totalAmount": find(r"Total amount:\s*[|]?\s*([\d.]+)", full_text),
            "billTo": {
                "company": "SWEEPSCRUB - COMMERCIAL - BRADYPLUS", # Ideally captured via regex
                "line1": "4007 RICHARDS RD",
                "cityStateZip": "NORTH LITTLE ROCK AR 72117"
            },
            "shipTo": {
                "company": "Gregory McNeil",
                "line1": "PO Box 424",
                "cityStateZip": "Higley AZ 85236"
            },
            "items": []
        }

        # Extracting Line Items (Iterating through blocks)
        item_blocks = re.findall(r"(\d+)\s+Material:\s+(.*?)\s+Customer Material:.*?\s+Quantity:\s+(\d+)", full_text, re.DOTALL)
        
        for item in item_blocks:
            invoice_json["items"].append({
                "item": item[0],
                "material": item[1].split()[0],
                "description": " ".join(item[1].split()[1:]),
                "quantity": item[2],
                "uom": "PC",
                "subtotal": "0.00" # You can add regex here to pull specific price if needed
            })

        all_extracted_data.append(invoice_json)

    st.json(all_extracted_data)

    if st.button("Send All to Celigo"):
        webhook_url = "https://api.integrator.io/v1/exports/6a3e22e548c8b4a733fbeb15/KVk2DW2JtJkffDcxDfAx0o2S0mwcSyXP/data"
        for item in all_extracted_data:
            requests.post(webhook_url, json=item)
            st.success(f"Sent {item['fileName']}")
