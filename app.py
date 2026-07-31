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

# --- INITIALIZE SESSION STATE ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'show_welcome' not in st.session_state:
    st.session_state['show_welcome'] = False
if 'all_extracted_data' not in st.session_state:
    st.session_state['all_extracted_data'] = []

# --- CLEANING HELPERS (Your logic preserved) ---
def clean_description(text, material_code):
    text = re.sub(re.escape(material_code), "", text, flags=re.IGNORECASE)
    noise = [r"COO: [A-Z]{2}", r"Customer Material:", r"\d+\s+Material:", r"Material:", r"Quantity:.*", r"Prices:.*", r"UoM", r"Rate", r"per", r"COO: US"]
    for pattern in noise:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return " ".join(text.split()).strip()

def get_price_from_row(row_list):
    for item in reversed(row_list):
        if item and re.search(r"[-+]?\d*\.\d+|\d+", str(item)):
            return str(item).replace("USD", "").replace("$", "").replace(",", "").strip()
    return "0.00"

def process_pdf(file_path, filename):
    with pdfplumber.open(file_path) as pdf:
        full_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        invoice_json = {
            "fileName": filename,
            "fileType": "PDF",
            "documentType": "Invoice",
            "invoiceNumber": re.search(r"Number\s*[|:]?\s*(\w+)", full_text, re.IGNORECASE).group(1) if re.search(r"Number\s*[|:]?\s*(\w+)", full_text, re.IGNORECASE) else "Not found",
            "poNumber": re.search(r"PO\s*number\s*[|:]?\s*([\w-]+)", full_text, re.IGNORECASE).group(1) if re.search(r"PO\s*number\s*[|:]?\s*([\w-]+)", full_text, re.IGNORECASE) else "Not found",
            "orderNumber": re.search(r"Order\s*number\s*[|:]?\s*([\w-]+)", full_text, re.IGNORECASE).group(1) if re.search(r"Order\s*number\s*[|:]?\s*([\w-]+)", full_text, re.IGNORECASE) else "Not found",
            "customerNumber": re.search(r"Customer\s*Number\s*[|:]?\s*([\w-]+)", full_text, re.IGNORECASE).group(1) if re.search(r"Customer\s*Number\s*[|:]?\s*([\w-]+)", full_text, re.IGNORECASE) else "Not found",
            "invoiceDate": re.search(r"Date\s*[|:]?\s*([A-Za-z]+\s+\d+,\s+\d+)", full_text, re.IGNORECASE).group(1) if re.search(r"Date\s*[|:]?\s*([A-Za-z]+\s+\d+,\s+\d+)", full_text, re.IGNORECASE) else "Not found",
            "totalAmount": re.search(r"(?:Final amount|Total amount)\s*[|:]?\s*(-?[\d.]+)", full_text, re.IGNORECASE).group(1) if re.search(r"(?:Final amount|Total amount)\s*[|:]?\s*(-?[\d.]+)", full_text, re.IGNORECASE) else "0.00",
            "items": []
        }
        current_item = None
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                for row in table:
                    clean_row = [str(cell) for cell in row if cell is not None]
                    row_str = " ".join(clean_row)
                    material_match = re.search(r"([A-Z]{2,}\d{2,}[A-Z\d]*)", row_str)
                    coo_match = re.search(r"(?:COO|Country of Origin)\s*[:\s]*([A-Z]{2})", row_str, re.IGNORECASE)
                    if material_match:
                        current_item = {
                            "item": clean_row[0] if len(clean_row) > 0 else "N/A",
                            "material": material_match.group(0),
                            "description": clean_description(row_str, material_match.group(0)),
                            "coo": coo_match.group(1) if coo_match else "N/A",
                            "quantity": "1",
                            "uom": "PC",
                            "publicPrice": "0.00",
                            "discount": "0.00",
                            "subtotal": "0.00"
                        }
                        invoice_json["items"].append(current_item)
                    elif current_item:
                        if any(label in row_str for label in ["Public price", "Net Pricelist price", "Manual price"]):
                            current_item["publicPrice"] = get_price_from_row(clean_row)
                        elif "Discount" in row_str:
                            current_item["discount"] = get_price_from_row(clean_row)
                        elif "Subtotal" in row_str:
                            current_item["subtotal"] = get_price_from_row(clean_row)
    return invoice_json

# --- UI PAGES ---
def login_page():
    st.image("https://media.licdn.com/dms/image/v2/D4D0BAQFJviu2NEE-Sw/company-logo_200_200/company-logo_200_200/0/1667374445161/vincent_clouds_logo?e=2147483647&v=beta&t=Jhv9ka9lcSdISkUbqyYaQ36SesJSXP0Br7xNAeEoR_k", width=150)
    st.title("Login to Vincent Cloud")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == "VincentCloud" and password == "Vincent@123":
            st.session_state['show_welcome'] = True
            st.rerun()
        else:
            st.error("Invalid username or password")

def welcome_page():
    st.balloons()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; color: #0E76A8;'>Welcome to Vincent Cloud!</h1>", unsafe_allow_html=True)
        if st.button("🚀 Enter Dashboard", type="primary", use_container_width=True):
            st.session_state['authenticated'] = True
            st.session_state['show_welcome'] = False
            st.rerun()

def main_dashboard():
    st.image("https://media.licdn.com/dms/image/v2/D4D0BAQFJviu2NEE-Sw/company-logo_200_200/company-logo_200_200/0/1667374445161/vincent_clouds_logo?e=2147483647&v=beta&t=Jhv9ka9lcSdISkUbqyYaQ36SesJSXP0Br7xNAeEoR_k", width=100)
    st.title("📄 Vincent Cloud (Nilfisk Invoice Parser)")
    
    uploaded_files = st.file_uploader("Upload Invoices (PDF or ZIP)", type=["pdf", "zip"], accept_multiple_files=True)
    
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("Process Files", type="primary", use_container_width=True):
            if uploaded_files:
                st.session_state['all_extracted_data'] = [] # Reset state for new batch
                with tempfile.TemporaryDirectory() as temp_dir:
                    files_to_process = []
                    for uploaded_file in uploaded_files:
                        if uploaded_file.name.endswith(".zip"):
                            with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                                zip_ref.extractall(temp_dir)
                                for root, dirs, files in os.walk(temp_dir):
                                    for file_name in files:
                                        if file_name.lower().endswith(".pdf"):
                                            files_to_process.append((os.path.join(root, file_name), file_name))
                        else:
                            temp_path = os.path.join(temp_dir, uploaded_file.name)
                            with open(temp_path, "wb") as f:
                                f.write(uploaded_file.getbuffer())
                            files_to_process.append((temp_path, uploaded_file.name))
                    
                    my_bar = st.progress(0, text="Starting processing...")
                    for i, (path, name) in enumerate(files_to_process):
                        st.session_state['all_extracted_data'].append(process_pdf(path, name))
                        my_bar.progress(int(((i + 1) / len(files_to_process)) * 100), text=f"Processing {name}")
                    st.success("Processing Complete!")

    with c2:
        if st.session_state['all_extracted_data']:
            if st.button("📤 Send to Celigo", type="secondary", use_container_width=True):
                webhook_url = "https://api.integrator.io/v1/exports/6a3e22e548c8b4a733fbeb15/KVk2DW2JtJkffDcxDfAx0o2S0mwcSyXP/data"
                with st.spinner("Sending..."):
                    for item in st.session_state['all_extracted_data']:
                        try:
                            response = requests.post(webhook_url, json=item)
                            if response.status_code in [200, 201, 202, 204]:
                                st.success(f"Sent {item['fileName']} successfully")
                            else:
                                st.error(f"Failed {item['fileName']}: {response.status_code}")
                        except Exception as e:
                            st.error(f"Error: {e}")

    with c3:
        if st.button("❌ Clear All", use_container_width=True):
            st.session_state['all_extracted_data'] = []
            st.rerun()

    if st.session_state['all_extracted_data']:
        st.subheader("Batch Review")
        review_data = []
        for entry in st.session_state['all_extracted_data']:
            for item in entry.get("items", []):
                review_data.append({
                    "File": entry["fileName"],
                    "Invoice #": entry["invoiceNumber"],
                    "PO #": entry["poNumber"],
                    "Order #": entry["orderNumber"],
                    "Date": entry["invoiceDate"],
                    "Material": item["material"],
                    "Description": item["description"],
                    "COO": item["coo"],
                    "Qty": item["quantity"],
                    "Total": entry["totalAmount"]
                })
        st.dataframe(pd.DataFrame(review_data))

# --- CONTROL FLOW ---
if not st.session_state['authenticated'] and not st.session_state['show_welcome']:
    login_page()
elif st.session_state['show_welcome']:
    welcome_page()
else:
    main_dashboard()
