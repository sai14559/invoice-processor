import streamlit as st
import pdfplumber

st.set_page_config(page_title="Invoice Processor", page_icon="📄")
st.title("📄 Invoice Processor")

# File Uploader
uploaded_file = st.file_uploader("Choose a PDF invoice", type="pdf")

if uploaded_file is not None:
    st.write("Processing PDF...")
    
    # This part "opens" the PDF and reads the text
    with pdfplumber.open(uploaded_file) as pdf:
        first_page = pdf.pages[0]  # This reads the first page
        text = first_page.extract_text()
        
    st.subheader("Extracted Text:")
    st.text(text)