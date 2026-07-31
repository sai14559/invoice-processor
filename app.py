import re
import pdfplumber
import streamlit as st
import pandas as pd

# --- Configuration ---
st.set_page_config(page_title="Invoice Processor", layout="wide")

# --- UI Header ---
# Ensure "logo.jfif.jfif" matches the exact filename in your GitHub repository
try:
    st.image("logo.jfif.jfif", width=200)
except Exception:
    st.warning("Logo file not found. Ensure 'logo.jfif.jfif' exists in your repo.")

st.title("Bulk Invoice Processor")
st.write("Upload multiple PDF invoices to extract data.")

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
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            # Extract text from all pages
            full_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

            # Extract fields
            invoice_num = find_field(full_text, [
                r"(?:Invoice|Credit Note|Document)\s*Number\s*[|:]?\s*([\w-]+)",
                r"Number\s*[|:]?\s*([\w-]+)"
            ])

            total_str = find_field(full_text, [
                r"(?:Total|Credit)\s*amount\s*[|:]?\s*([\d,.]+)",
                r"Total\s*Due\s*[|:]?\s*([\d,.]+)"
            ])
            # Clean amount: remove commas
            total_val = total_str.replace(",", "") if total_str != "Not found" else "0.00"

            return {
                "File Name": uploaded_file.name,
                "Invoice Number": invoice_num,
                "Total Amount": total_val
            }
    except Exception as e:
        return {"File Name": uploaded_file.name, "Error": str(e)}

# --- UI Logic ---
uploaded_files = st.file_uploader("Upload PDF invoices", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    if st.button("Process All Files"):
        results = []
        with st.spinner("Processing files..."):
            for file in uploaded_files:
                data = process_pdf(file)
                results.append(data)

        st.success("Extraction Complete!")
        df = pd.DataFrame(results)

        # Display table
        st.dataframe(df, use_container_width=True)

        # CSV Download
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Results as CSV",
            data=csv,
            file_name="invoice_data.csv",
            mime="text/csv"
        )
