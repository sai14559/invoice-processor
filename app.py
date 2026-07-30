import streamlit as st
import pdfplumber
import json

st.set_page_config(page_title="Invoice Processor", page_icon="📄")
st.title("📄 Invoice Processor")

uploaded_file = st.file_uploader("Choose a PDF invoice", type="pdf")

if uploaded_file is not None:
    st.write("Processing PDF...")
    
    # We create a dictionary to hold all our data
    invoice_data = {}
    
    with pdfplumber.open(uploaded_file) as pdf:
        # Loop through every single page
        for i, page in enumerate(pdf.pages):
            # Extract text and keep the lines intact
            text = page.extract_text()
            # Store in our dictionary with the page number
            invoice_data[f"page_{i+1}"] = text
            
    # Convert our data into a clean JSON format
    json_output = json.dumps(invoice_data, indent=4)
    
    st.subheader("JSON Output:")
    # This displays it as a code block so it's easy to copy
    st.code(json_output, language="json")