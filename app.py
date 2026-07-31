import streamlit as st
import pdfplumber
import json
import requests
import re
import csv
import os
import zipfile
import tempfile
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
# Using an emoji for the tab icon, and your URL for the main logo
st.set_page_config(page_title="Vincent Cloud", page_icon="☁️")
st.image("https://media.licdn.com/dms/image/v2/D4D0BAQFJviu2NEE-Sw/company-logo_200_200/company-logo_200_200/0/1667374445161/vincent_clouds_logo?e=2147483647&v=beta&t=Jhv9ka9lcSdISkUbqyYaQ36SesJSXP0Br7xNAeEoR_k", width=150)
st.title("📄 Vincent Cloud (Nilfisk Invoice Parser)")

# --- CLEANING HELPERS ---
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
            "fileType": "PDF",
            "documentType": "Invoice",
            "invoiceNumber": re.search(r"Number\s*[|:]?\s*(\d+)", full_text).group(1) if re.search(r"Number\s*[|:]?\s*(\d+)", full_text) else "Not found",
            "poNumber": re.search(r"PO\s*Number\s*[|:]?\s*([\w-]+)", full_text).group(1) if re.search(r"PO\s*Number\s*[|:]?\s*([\w-]+)", full_text) else "Not found",
            "orderNumber": re.search(r"Order\s*Number\s*[|:]?\s*([\w-]+)", full_text).group(1) if re.search(r"Order\s*Number\s*[|:]?\s*([\w-]+)", full_text) else "Not found",
            "customerNumber": re.search(r"Customer\s*Number\s*[|:]?\s*([\w-]+)", full_text).group(1) if re.search(r"Customer\s*Number\s*[|:]?\s*([\w-]+)", full_text) else "Not found",
            "invoiceDate": re.search(r"Date\s*[|:]?\s*([A-Za-z]+\s+\d+,\s+\d+)", full_text).group(1) if re.search(r"Date\s*[|:]?\s*([A-Za-z]+\s+\d+,\s+\d+)", full_text) else "Not found",
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
                        current_item = {
                            "item": clean_row[0] if len(clean_row) > 0 else "N/A",
                            "material": material_match.group(0),
                            "description": clean_description(row_str, material_match.group(0)),
                            "quantity": "1",
                            "uom": "PC",
                            "publicPrice": "0.00",
                            "discount": "0.00",
                            "subtotal": "0.00"
                        }
                        invoice_json["items"].append(current_item)
                    elif current_item:
                        if any(label in row_str for label in ["Public price", "Net Pricelist price"]):
                            current_item["publicPrice"] = get_price_from_row(clean_row)
                        elif "Discount" in row_str:
                            current_item["discount"] = get_price_from_row(clean_row)
                        elif "Subtotal" in row_str:
                            current_item["subtotal"] = get_price_from_row(clean_row)
    return invoice_json

# --- MAIN APP ---
uploaded_files = st.file_uploader("Upload Invoices (PDF or ZIP)", type=["pdf", "zip"], accept_multiple_files=True)

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

        my_bar = st.progress(0, text="Starting processing...")

        for i, (path, name) in enumerate(files_to_process):
            all_extracted_data.append(process_pdf(path, name))
            percent_complete = int(((i + 1) / len(files_to_process)) * 100)
            my_bar.progress(percent_complete, text=f"Processing {name} ({i+1}/{len(files_to_process)})")

    st.success(f"Processed {len(all_extracted_data)} files!")

    # --- REVIEW TABLE ---
    st.subheader("Batch Review")
    review_data = []
    for entry in all_extracted_data:
        for item in entry.get("items", []):
            review_data.append({
                "File": entry["fileName"],
                "Invoice #": entry["invoiceNumber"],
                "PO #": entry["poNumber"],
                "Order #": entry["orderNumber"],
                "Cust #": entry["customerNumber"],
                "Date": entry["invoiceDate"],
                "Material": item["material"],
                "Description": item["description"],
                "Qty": item["quantity"],
                "UoM": item["uom"],
                "Public Price": item["publicPrice"],
                "Discount": item["discount"],
                "Subtotal": item["subtotal"],
                "Total": entry["totalAmount"]
            })

    df = pd.DataFrame(review_data)
    if not df.empty:
        st.dataframe(df)
        st.write(f"Total items ready to send: {len(df)}")

    # --- CELIGO INTEGRATION & LOGGING ---
    if st.button("Send All to Celigo"):
        webhook_url = "https://api.integrator.io/v1/exports/6a3e22e548c8b4a733fbeb15/KVk2DW2JtJkffDcxDfAx0o2S0mwcSyXP/data"
        log_file = "invoice_history.csv"
        file_exists = os.path.isfile(log_file)

        with open(log_file, mode='a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "FileName", "InvoiceNumber", "TotalAmount", "Status"])

            for item in all_extracted_data:
                try:
                    response = requests.post(webhook_url, json=item)
                    if response.status_code in [200, 201, 202, 204]:
                        st.success(f"Successfully sent {item['fileName']}!")
                        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), item['fileName'], item['invoiceNumber'], item['totalAmount'], "Success"])
                    else:
                        st.error(f"Failed {item['fileName']}: {response.status_code}")
                        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), item['fileName'], item['invoiceNumber'], item['totalAmount'], f"Failed: {response.status_code}"])
                except Exception as e:
                    st.error(f"Error: {e}")
                    writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), item['fileName'], "N/A", "N/A", f"Error: {e}"])
        st.info("Log updated: check 'invoice_history.csv' for your records.")
