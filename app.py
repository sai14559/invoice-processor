import streamlit as st
import pdfplumber
import json
import requests
import re

st.set_page_config(page_title="Dynamic Invoice Parser", page_icon="📄")
st.title("📄 Dynamic Invoice Parser (Professional)")

# --- CLEANING HELPERS ---
def extract_money(text, label):
    # This looks for the label (e.g., 'Discount') and grabs the number immediately following it
    pattern = rf"{label}.*?(-?[\d]+\.[\d]+)"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1) if match else "0.00"

def clean_description(text, material_code):
    text = text.replace(material_code, "")
    # Remove noise and specific "Customer" leftovers
    noise_patterns = [r"\d+\s+Material:", r"Material:", r"COO:.*", r"Customer Material:.*", r"Customer", r"Quantity:.*", r"Prices:.*"]
    for pattern in noise_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return " ".join(text.split()).strip()

PATTERNS = {
    "invoiceNumber": [r"Number\s*[|:]?\s*(\d+)", r"Document\s*[|:]?\s*(\d+)", r"Invoice\s*#\s*(\d+)"],
    "poNumber": [r"PO Number\s*[|:]?\s*(\d+)", r"Purchase Order\s*[:|]?\s*(\d+)", r"PO#\s*(\d+)"],
    "orderNumber": [r"Order Number\s*[|:]?\s*(\d+)", r"Order #\s*(\d+)"],
    "customerNumber": [r"Customer Number\s*[|:]?\s*(\d+)", r"Cust #\s*(\d+)"],
    "totalAmount": [r"Total amount:\s*[|:]?\s*([\d.]+)", r"Total:\s*[\$]?\s*([\d.]+)", r"Grand Total\s*[:|]?\s*([\d.]+)"]
}

def find_dynamic(text, pattern_list):
    for pattern in pattern_list:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return "Not found"

uploaded_files = st.file_uploader("Upload Invoices", type="pdf", accept_multiple_files=True)

all_extracted_data = []

if uploaded_files:
    for uploaded_file in uploaded_files:
        with pdfplumber.open(uploaded_file) as pdf:
            full_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
            
            invoice_json = {
                "fileName": uploaded_file.name,
                "fileType": "PDF",
                "documentType": "Invoice",
                "invoiceNumber": find_dynamic(full_text, PATTERNS["invoiceNumber"]),
                "invoiceDate": find_dynamic(full_text, [r"Date\s*[|:]?\s*([A-Za-z]+\s+\d+,\s+\d+)"]),
                "poNumber": find_dynamic(full_text, PATTERNS["poNumber"]),
                "orderNumber": find_dynamic(full_text, PATTERNS["orderNumber"]),
                "customerNumber": find_dynamic(full_text, PATTERNS["customerNumber"]),
                "currency": "USD",
                "totalAmount": find_dynamic(full_text, PATTERNS["totalAmount"]),
                "billTo": {"company": "SWEEPSCRUB - COMMERCIAL", "line1": "4007 RICHARDS RD", "cityStateZip": "NORTH LITTLE ROCK AR 72117"},
                "shipTo": {"company": "Gregory McNeil", "line1": "PO Box 424", "cityStateZip": "Higley AZ 85236"},
                "items": []
            }
            
            # --- TABLE EXTRACTION WITH PRICE PARSING ---
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    for row in table:
                        row_str = " ".join([str(cell) for cell in row if cell])
                        material_match = re.search(r"[A-Z]{2}\d{5}", row_str)
                        
                        if material_match:
                            invoice_json["items"].append({
                                "item": row[0] if len(row) > 0 else "N/A",
                                "material": material_match.group(0),
                                "description": clean_description(row_str, material_match.group(0)),
                                "quantity": "1",
                                "uom": "PC",
                                "publicPrice": extract_money(row_str, "Public price"),
                                "discount": extract_money(row_str, "Discount"),
                                "subtotal": extract_money(row_str, "Subtotal")
                            })
            
            all_extracted_data.append(invoice_json)

    st.json(all_extracted_data)

    if st.button("Send All to Celigo"):
        webhook_url = "https://api.integrator.io/v1/exports/6a3e22e548c8b4a733fbeb15/KVk2DW2JtJkffDcxDfAx0o2S0mwcSyXP/data"
        for item in all_extracted_data:
            try:
                response = requests.post(webhook_url, json=item)
                if response.status_code in [200, 201, 202, 204]:
                    st.success(f"Successfully sent {item['fileName']}!")
                else:
                    st.error(f"Failed {item['fileName']}: {response.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")
