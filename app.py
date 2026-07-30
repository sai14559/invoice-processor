import streamlit as st
import pdfplumber
import requests
import re
import csv
import os
import zipfile
import tempfile
import pandas as pd
from datetime import datetime

# --- CONFIGURATION & AUTH ---
USERS = {
    "admin": "password123",
    "jdoe": "emp123"
}

st.set_page_config(page_title="Vincent Cloud", page_icon="📄", layout="wide")

def check_password():
    if "password_correct" not in st.session_state:
        st.subheader("🔒 Login to Vincent Cloud")
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        if st.button("Login"):
            if st.session_state["username"] in USERS and st.session_state["password"] == USERS[st.session_state["username"]]:
                st.session_state["password_correct"] = True
                st.session_state["logged_in_user"] = st.session_state["username"]
                st.rerun()
            else:
                st.error("😕 User or password incorrect")
        return False
    return st.session_state["password_correct"]

if not check_password():
    st.stop() 

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Settings")
    st.write(f"Logged in as: **{st.session_state.get('logged_in_user')}**")
    if st.button("Logout"):
        st.session_state["password_correct"] = False
        st.rerun()

# --- MAIN UI ---
st.title("📄 Vincent Cloud")
st.markdown("---")

# --- HELPERS ---
def clean_description(text, material_code):
    text = re.sub(re.escape(material_code), "", text, flags=re.IGNORECASE)
    noise = [r"COO: [A-Z]{2}", r"Customer Material:", r"\d+\s+Material:", r"Material:", r"Quantity:.*", r"Prices:.*", r"UoM", r"Rate", r"per", r"COO: US"]
    for pattern in noise:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return " ".join(text.split()).strip()

def get_price_from_row(row_list):
    for item in reversed(row_list):
        if item and re.search(r"[-+]?\d*\.\d+|\d+", str(item)):
            return str(item).replace("USD", "").strip()
    return "0.00"

def process_pdf(file_path, filename):
    with pdfplumber.open(file_path) as pdf:
        full_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        invoice_json = {
            "fileName": filename,
            "invoiceNumber": re.search(r"Number\s*[|:]?\s*(\d+)", full_text).group(1) if re.search(r"Number\s*[|:]?\s*(\d+)", full_text) else "Not found",
            "totalAmount": re.search(r"Total amount:\s*[|:]?\s*([\d.]+)", full_text).group(1) if re.search(r"Total amount:\s*[|:]?\s*([\d.]+)", full_text) else "0.00",
            "items": []
        }
        current_item = None
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                for row in table:
                    clean_row = [str(cell) for cell in row if cell is not None]
                    row_str = " ".join(clean_row)
                    material_match = re.search(r"([A-Z]{2}\d{5}|\d{8,})", row_str)
                    if material_match:
                        current_item = {"material": material_match.group(0), "subtotal": "0.00"}
                        invoice_json["items"].append(current_item)
                    elif current_item:
                        if "Subtotal" in row_str:
                            current_item["subtotal"] = get_price_from_row(clean_row)
    return invoice_json

# --- FILE UPLOAD SECTION ---
st.subheader("1. Upload Invoices")
uploaded_files = st.file_uploader("Drop PDF or ZIP files here", type=["pdf", "zip"], accept_multiple_files=True)

if uploaded_files:
    all_extracted_data = []
    files_to_process = []
    
    with tempfile.TemporaryDirectory() as temp_dir:
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
        
        my_bar = st.progress(0, text="Processing...")
        for i, (path, name) in enumerate(files_to_process):
            all_extracted_data.append(process_pdf(path, name))
            my_bar.progress(int(((i + 1) / len(files_to_process)) * 100))

    # --- REVIEW & ACTION ---
    st.subheader("2. Review & Send")
    review_data = []
    for entry in all_extracted_data:
        for item in entry.get("items", []):
            review_data.append({"File": entry["fileName"], "Invoice #": entry["invoiceNumber"], "Material": item["material"], "Subtotal": item["subtotal"]})
    
    df = pd.DataFrame(review_data)
    if not df.empty:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.dataframe(df, use_container_width=True)
        with col2:
            st.write(f"**Items found:** {len(df)}")
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV", csv_data, 'results.csv', 'text/csv', use_container_width=True)
            
            if st.button("🚀 Send All to Celigo", type="primary", use_container_width=True):
                webhook_url = "https://api.integrator.io/v1/exports/6a3e22e548c8b4a733fbeb15/KVk2DW2JtJkffDcxDfAx0o2S0mwcSyXP/data"
                for item in all_extracted_data:
                    try:
                        response = requests.post(webhook_url, json=item)
                        if response.status_code in [200, 201, 202, 204]:
                            st.toast(f"Sent: {item['fileName']}", icon="✅")
                        else:
                            st.error(f"Failed: {item['fileName']}")
                    except Exception as e:
                        st.error(f"Error with {item['fileName']}")
