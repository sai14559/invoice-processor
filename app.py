import re
import pdfplumber
import json
import streamlit as st

# --- Helper Functions ---
def find_field(text, patterns):
    """Iterates through regex patterns until it finds a match."""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return "Not found"

def process_pdf(uploaded_file):
    """Parses the PDF file uploaded via Streamlit."""
    invoice_json = {
        "fileName": uploaded_file.name,
        "documentType": "Credit Note" if "credit" in uploaded_file.name.lower() else "Invoice",
        "invoiceNumber": None,
        "poNumber": None,
        "totalAmount": "0.00",
        "items": []
    }

    try:
        with pdfplumber.open(uploaded_file) as pdf:
            # Extract text from all pages
            full_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

            # Extract fields
            invoice_json["invoiceNumber"] = find_field(full_text, [
                r"(?:Invoice|Credit Note|Document)\s*Number\s*[|:]?\s*([\w-]+)",
                r"Number\s*[|:]?\s*([\w-]+)"
            ])
            
            invoice_json["poNumber"] = find_field(full_text, [
                r"PO\s*Number\s*[|:]?\s*([\w-]+)",
                r"Purchase Order\s*[|:]?\s*([\w-]+)"
            ])
            
            total_str = find_field(full_text, [
                r"(?:Total|Credit)\s*amount\s*[|:]?\s*([\d,.]+)",
                r"Total\s*Due\s*[|:]?\s*([\d,.]+)"
            ])
            invoice_json["totalAmount"] = total_str.replace(",", "") if total_str != "Not found" else "0.00"

            # Table extraction
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    for row in table:
                        clean_row = [str(cell) for cell in row if cell is not None]
                        row_str = " ".join(clean_row)
                        material_match = re.search(r"([A-Z]{2}\s?\d{5}|\d{8,})", row_str)
                        if material_match:
                            invoice_json["items"].append({"materialCode": material_match.group(0)})
                            
    except Exception as e:
        return {"error": str(e)}

    return invoice_json

# --- Main Streamlit UI ---
st.title("Invoice Processor")
st.write("Upload your PDF to extract invoice data.")

uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

if uploaded_file is not None:
    if st.button("Process Invoice"):
        with st.spinner("Processing..."):
            result = process_pdf(uploaded_file)
            
            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                st.success("Extraction Complete!")
                st.json(result)
