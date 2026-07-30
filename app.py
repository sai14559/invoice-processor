import streamlit as st
import pdfplumber
import json
import re
import requests

st.set_page_config(page_title="Invoice Parser", page_icon="📄")
st.title("📄 Invoice Parser (No AI)")

uploaded_files = st.file_uploader("Choose PDF invoices", type="pdf", accept_multiple_files=True)

all_extracted_data = []

if uploaded_files:
    st.write(f"Processing {len(uploaded_files)} file(s)...")

    for uploaded_file in uploaded_files:
        full_text = ""
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

        # --- EXCLUSION LOGIC ---
        clean_text = re.sub(r"Bill-to address:.*?(?=Ship-to address:)", "", full_text, flags=re.DOTALL | re.IGNORECASE)
        clean_text = re.sub(r"Conditions:.*?(?=Text:)", "", clean_text, flags=re.DOTALL | re.IGNORECASE)

        # 1. Extract Summary Data
        # We now check for "Number" OR "Document" to be safe
        inv_num_match = re.search(r"(?:Number|Document)\s*[|]?\s*(\d+)", clean_text, re.IGNORECASE)
        date_match = re.search(r"Date\s*[|]?\s*([A-Za-z]+\s+\d+,\s+\d+)", clean_text, re.IGNORECASE)
        total_match = re.search(r"Total amount:\s*[|]?\s*([\d.]+)", clean_text, re.IGNORECASE)

        # 2. Extract Line Items
        items = re.findall(r"Material:\s+(.*?)(?:\s*COO:|Customer Material:)", clean_text, re.IGNORECASE)
        cleaned_items = [item.strip() for item in items]

        # 3. Capture Everything Else
        remaining_content = clean_text.strip()

        data = {
            "file_name": uploaded_file.name,
            "invoice_number": inv_num_match.group(1) if inv_num_match else "Not found",
            "date": date_match.group(1) if date_match else "Not found",
            "total_amount": total_match.group(1) if total_match else "Not found",
            "line_items": cleaned_items,
            "additional_details": remaining_content
        }
        all_extracted_data.append(data)

    st.subheader("Extracted Data Preview:")
    st.json(all_extracted_data)

    if st.button("Send All to Celigo"):
        webhook_url = "https://api.integrator.io/v1/exports/6a3e22e548c8b4a733fbeb15/KVk2DW2JtJkffDcxDfAx0o2S0mwcSyXP/data"
        
        for item in all_extracted_data:
            try:
                response = requests.post(webhook_url, json=item)
                if response.status_code in [200, 201, 202, 204]:
                    st.success(f"Successfully sent {item['file_name']}!")
                else:
                    st.error(f"Failed to send {item['file_name']}. Status code: {response.status_code}")
            except Exception as e:
                st.error(f"Error sending {item['file_name']}: {e}")
