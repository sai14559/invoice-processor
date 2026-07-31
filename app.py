import streamlit as st
import pdfplumber
import json
import requests
import re
import os
import zipfile
import tempfile
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Vincent Cloud", page_icon="☁️", layout="wide")

# --- NAVIGATION STATE ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'welcome_completed' not in st.session_state:
    st.session_state['welcome_completed'] = False

# --- UI COMPONENTS ---
def login_screen():
    st.image("https://media.licdn.com/dms/image/v2/D4D0BAQFJviu2NEE-Sw/company-logo_200_200/company-logo_200_200/0/1667374445161/vincent_clouds_logo?e=2147483647&v=beta&t=Jhv9ka9lcSdISkUbqyYaQ36SesJSXP0Br7xNAeEoR_k", width=150)
    st.title("Login to Vincent Cloud")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == "admin" and password == "Vincent@123":
            st.session_state['authenticated'] = True
            st.rerun()
        else:
            st.error("Invalid username or password")

def welcome_screen():
    st.balloons()
    st.title("Welcome to Vincent Cloud!")
    if st.button("Enter Dashboard"):
        st.session_state['welcome_completed'] = True
        st.rerun()

# --- MAIN DASHBOARD ---
def main_dashboard():
    st.image("https://media.licdn.com/dms/image/v2/D4D0BAQFJviu2NEE-Sw/company-logo_200_200/company-logo_200_200/0/1667374445161/vincent_clouds_logo?e=2147483647&v=beta&t=Jhv9ka9lcSdISkUbqyYaQ36SesJSXP0Br7xNAeEoR_k", width=150)
    st.title("📄 Vincent Cloud (Nilfisk Invoice Parser)")

    # --- UPDATED PARSER ---
    def process_pdf(file_path, filename):
        with pdfplumber.open(file_path) as pdf:
            full_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

            # Extract basic header info
            invoice_json = {
                "fileName": filename,
                "invoiceNumber": re.search(r"Number\s*[|:]?\s*(\w+)", full_text, re.IGNORECASE).group(1) if re.search(r"Number\s*[|:]?\s*(\w+)", full_text, re.IGNORECASE) else "N/A",
                "poNumber": re.search(r"PO\s*Number\s*[|:]?\s*([\w-]+)", full_text, re.IGNORECASE).group(1) if re.search(r"PO\s*Number\s*[|:]?\s*([\w-]+)", full_text, re.IGNORECASE) else "N/A",
                "trackingNumber": re.search(r"Tracking nr\.\s*[|:]?\s*(\w+)", full_text, re.IGNORECASE).group(1) if re.search(r"Tracking nr\.\s*[|:]?\s*(\w+)", full_text, re.IGNORECASE) else "N/A",
                "totalAmount": re.search(r"(?:Total amount:)\s*[|:]?\s*([\d.]+)", full_text, re.IGNORECASE).group(1) if re.search(r"(?:Total amount:)\s*[|:]?\s*([\d.]+)", full_text, re.IGNORECASE) else "0.00",
                "items": []
            }

            # Improved Item Extraction: Regex looks for 5+ digit codes (handles purely numeric materials)
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    for row in table:
                        row_str = " ".join([str(cell) for cell in row if cell])
                        # New Regex: Looks for 5-10 digit numbers (covers your material codes)
                        material_match = re.search(r"(\b\d{5,10}\b)", row_str)
                        if material_match and "Total" not in row_str:
                            invoice_json["items"].append({
                                "material": material_match.group(1),
                                "raw_row": row_str
                            })
            return invoice_json

    uploaded_files = st.file_uploader("Upload Invoices", type=["pdf"], accept_multiple_files=True)

    if uploaded_files:
        all_data = []
        with tempfile.TemporaryDirectory() as temp_dir:
            for uploaded_file in uploaded_files:
                temp_path = os.path.join(temp_dir, uploaded_file.name)
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                all_data.append(process_pdf(temp_path, uploaded_file.name))

        # --- PREVIEW SECTION ---
        st.subheader("Data Preview (Before Sending)")
        for entry in all_data:
            with st.expander(f"Data for {entry['fileName']}"):
                st.json(entry)

        # --- BATCH REVIEW TABLE ---
        st.subheader("Batch Review")
        df_list = []
        for entry in all_data:
            # If no items found, still show the invoice info
            if not entry["items"]:
                df_list.append({"File": entry["fileName"], "Invoice": entry["invoiceNumber"], "Tracking": entry["trackingNumber"], "Material": "No items detected", "Amount": entry["totalAmount"]})
            else:
                for item in entry["items"]:
                    df_list.append({"File": entry["fileName"], "Invoice": entry["invoiceNumber"], "Tracking": entry["trackingNumber"], "Material": item["material"], "Amount": entry["totalAmount"]})
        
        st.dataframe(pd.DataFrame(df_list))

        if st.button("Send All to Celigo"):
            st.info("Sending data...")
            # Logic remains the same

# --- APP FLOW ---
if not st.session_state['authenticated']:
    login_screen()
elif not st.session_state['welcome_completed']:
    welcome_screen()
else:
    main_dashboard()
