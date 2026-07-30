import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import pdfplumber
import re
import csv
import os
import tempfile
import pandas as pd
from datetime import datetime

# --- AUTH CONFIGURATION ---
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# --- LOGIN GATEKEEPER ---
# Using location='main' tells the library exactly where to render the widget
name, authentication_status, username = authenticator.login(location='main')

if authentication_status == False:
    st.error('Username/password is incorrect')
elif authentication_status == None:
    st.warning('Please enter your username and password')

elif authentication_status:
    st.title("📄 Vincent Cloud")
    st.write(f'Welcome *{name}*')

    # --- ADMIN DASHBOARD ---
    if username == 'admin':
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

    st.divider()
    # Logout button
    authenticator.logout('Logout', location='main')
