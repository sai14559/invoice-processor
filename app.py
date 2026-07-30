import streamlit as st
import pdfplumber
import json
import re
import requests

st.set_page_config(page_title="Invoice Parser", page_icon="📄")
st.title("📄 Invoice Parser (No AI)")

uploaded_file = st.file_uploader("Choose a PDF invoice", type="pdf")

# We initialize 'data' as None so we can use it later
data = None

if uploaded_file is not None:
    st.write("Processing PDF...")
    
    full_text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"

    # Regex extraction
    inv_num_match = re.search(r"Number\s+(\d+)", full_text)
    date_match = re.search(r"Date\s+([A-Za-z]+\s+\d+,\s+\d+)", full_text)
    total_match = re.search(r"Total amount:\s+([\d.]+)", full_text)

    data = {
        "invoice_number": inv_num_match.group(1) if inv_num_match else "Not found",
        "date": date_match.group(1) if date_match else "Not found",
        "total_amount": total_match.group(1) if total_match else "Not found"
    }

    st.subheader("Extracted JSON Data:")
    st.json(data)

    # The "Send" Button
    if st.button("Send to Celigo"):
        if data:
            webhook_url = "https://api.integrator.io/v1/exports/6a3e22e548c8b4a733fbeb15/KVk2DW2JtJkffDcxDfAx0o2S0mwcSyXP/data"
            try:
                response = requests.post(webhook_url, json=data)
                if response.status_code == 200 or response.status_code == 202:
                    st.success("Successfully sent to Celigo!")
                else:
                    st.error(f"Failed to send. Status code: {response.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")