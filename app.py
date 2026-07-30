import streamlit as st
import pdfplumber
import json
import requests
import re

st.set_page_config(page_title="Dynamic Parser", page_icon="📄")
st.title("📄 Dynamic Parser (Cleaned)")

# --- CLEANING HELPERS ---
def clean_description(text, material_code):
    # 1. Remove the material code (case insensitive)
    text = re.sub(re.escape(material_code), "", text, flags=re.IGNORECASE)
    # 2. Remove specific noise patterns
    noise = [r"COO: [A-Z]{2}", r"Customer Material:", r"\d+\s+Material:", r"Material:", r"Quantity:.*", r"Prices:.*", r"UoM", r"Rate", r"per"]
    for pattern in noise:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    # 3. Final cleanup: remove extra spaces and any leading/trailing delimiters
    return " ".join(text.split()).strip()

def get_price_from_row(row_list):
    # Searches from right-to-left to grab the first valid number found (the price)
    for item in reversed(row_list):
        if item and re.search(r"[-+]?\d*\.\d+|\d+", str(item)):
            return str(item).replace("USD", "").strip()
    return "0.00"

# --- MAIN PARSING LOGIC ---
uploaded_files = st.file_uploader("Upload Invoices", type="pdf", accept_multiple_files=True)

if uploaded_files:
    all_extracted_data = []
    
    for uploaded_file in uploaded_files:
        with pdfplumber.open(uploaded_file) as pdf:
            full_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
            
            # --- EXTRACTING HEADER DATA ---
            invoice_json = {
                "fileName": uploaded_file.name,
                "fileType": "PDF",
                "documentType": "Invoice", # Hardcoded based on your usage, or use re.search if varied
                "invoiceNumber": re.search(r"Number\s*[|:]?\s*(\d+)", full_text).group(1) if re.search(r"Number\s*[|:]?\s*(\d+)", full_text) else "Not found",
                "invoiceDate": re.search(r"Date\s*[|:]?\s*([A-Za-z]+\s+\d+,\s+\d+)", full_text).group(1) if re.search(r"Date\s*[|:]?\s*([A-Za-z]+\s+\d+,\s+\d+)", full_text) else "Not found",
                "totalAmount": re.search(r"Total amount:\s*[|:]?\s*([\d.]+)", full_text).group(1) if re.search(r"Total amount:\s*[|:]?\s*([\d.]+)", full_text) else "0.00",
                "items": []
            }
            
            current_item = None
            
            # --- POSITIONAL TABLE EXTRACTION ---
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    for row in table:
                        clean_row = [str(cell) for cell in row if cell is not None]
                        row_str = " ".join(clean_row)
                        
                        # 1. Identify Material Row
                        material_match = re.search(r"[A-Z]{2}\d{5}", row_str)
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
                        
                        # 2. Identify Price Rows
                        elif current_item:
                            if "Public price" in row_str:
                                current_item["publicPrice"] = get_price_from_row(clean_row)
                            elif "Discount" in row_str:
                                current_item["discount"] = get_price_from_row(clean_row)
                            elif "Subtotal" in row_str:
                                current_item["subtotal"] = get_price_from_row(clean_row)

            all_extracted_data.append(invoice_json)

    st.json(all_extracted_data)
