import streamlit as st
import pdfplumber
import re
import csv
import os
import tempfile
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
# Define your users here (Username: Password)
USERS = {
    "admin": "password123",
    "jdoe": "emp123"
}

# --- CUSTOM AUTHENTICATION SYSTEM ---
def check_password():
    """Returns True if the user has the correct password."""
    def password_entered():
        if st.session_state["username"] in USERS and st.session_state["password"] == USERS[st.session_state["username"]]:
            st.session_state["password_correct"] = True
            st.session_state["logged_in_user"] = st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show inputs
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password", on_change=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        # Wrong password
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password", on_change=password_entered)
        st.error("😕 User not known or password incorrect")
        return False
    else:
        # Password correct
        return True

# --- APP START ---
st.title("📄 Vincent Cloud")

if not check_password():
    st.stop()  # Do not show the rest of the app until logged in

# --- APP LOGIC (Only visible after login) ---
name = st.session_state["logged_in_user"]
st.write(f'Welcome *{name}*')

# --- ADMIN DASHBOARD ---
if name == 'admin':
    st.subheader("Admin: Employee Activity Log")
    if os.path.exists("invoice_history.csv"):
        df_history = pd.read_csv("invoice_history.csv")
        st.dataframe(df_history)
    else:
        st.info("No activity logs found yet.")
    st.divider()

# --- INVOICE PARSING LOGIC ---
def process_pdf(file_path, filename):
    with pdfplumber.open(file_path) as pdf:
        full_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        invoice_json = {
            "fileName": filename,
            "invoiceNumber": re.search(r"Number\s*[|:]?\s*(\d+)", full_text).group(1) if re.search(r"Number\s*[|:]?\s*(\d+)", full_text) else "Not found",
            "totalAmount": re.search(r"Total amount:\s*[|:]?\s*([\d.]+)", full_text).group(1) if re.search(r"Total amount:\s*[|:]?\s*([\d.]+)", full_text) else "0.00",
        }
    return invoice_json

uploaded_files = st.file_uploader("Upload Invoices", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    all_extracted_data = []
    with tempfile.TemporaryDirectory() as temp_dir:
        for uploaded_file in uploaded_files:
            temp_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            all_extracted_data.append(process_pdf(temp_path, uploaded_file.name))

    # --- SEND TO CELIGO & LOG ---
    if st.button("Send to Celigo"):
        log_file = "invoice_history.csv"
        file_exists = os.path.isfile(log_file)
        with open(log_file, mode='a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "User", "FileName", "InvoiceNumber", "TotalAmount", "Status"])
            
            for item in all_extracted_data:
                writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name, item['fileName'], item['invoiceNumber'], item['totalAmount'], "Sent"])
        
        st.success("Data sent and logged!")

# Logout Button
if st.button("Logout"):
    st.session_state["password_correct"] = False
    st.rerun()
