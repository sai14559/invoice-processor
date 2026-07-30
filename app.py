import streamlit as st
import pdfplumber
import json
import re
import requests

st.set_page_config(page_title="Multi-Invoice Parser", page_icon="📄")
st.title("📄 Multi-Invoice Parser (No AI)")

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

        # 1. Extract Summary Data
        inv_num_match = re.search(r"Number\s+(\d+)", full_text)
        date_match = re.search(r"Date\s+([A-Za-z]+\s+\d+,\s+\d+)", full_text)
        total_match = re.search(r"Total amount:\s+([\d.]+)", full_text)

        # 2. Extract Line Items (Updated Regex)
        # This now captures text between "Material:" and either "COO:" or "Customer Material:"
        # It handles cases where spaces might be missing before "COO:"
        items = re.findall(r"Material:\s+(.*?)(?:\s*COO:|Customer Material:)", full_text, re.IGNORECASE)

        # Clean up each item: remove extra whitespace and newlines
        cleaned_items = [item.strip() for item in items]

        data = {
            "file_name": uploaded_file.name,
            "invoice_number": inv_num_match.group(1) if inv_num_match else "Not found",
            "date": date_match.group(1) if date_match else "Not found",
            "total_amount": total_match.group(1) if total_match else "Not found",
            "line_items": cleaned_items
        }
        all_extracted_data.append(data)

    st.subheader("Extracted Data Preview:")
    st.json(all_extracted_data)

    # The "Send" Button
    if st.button("Send All to Celigo"):
        webhook_url = "https://api.integrator.io/v1/exports/6a3e22e548c8b4a733fbeb15/KVk2DW2JtJkffDcxDfAx0o2S0mwcSyXP/data"
        
        for item in all_extracted_data:
            try:
                response = requests.post(webhook_url, json=item)
                # Success codes
                if response.status_code in [200, 201, 202, 204]:
                    st.success(f"Successfully sent {item['file_name']}!")
                else:
                    st.error(f"Failed to send {item['file_name']}. Status code: {response.status_code}")
            except Exception as e:
                st.error(f"Error sending {item['file_name']}: {e}")