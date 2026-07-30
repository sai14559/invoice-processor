import streamlit as st

st.set_page_config(page_title="Invoice Processor", page_icon="📄")
st.title("📄 Invoice Processor")

# Simple File Uploader
uploaded_file = st.file_uploader("Choose a PDF invoice", type="pdf")

if uploaded_file is not None:
    st.success(f"File '{uploaded_file.name}' uploaded successfully!")
    st.write("Ready for parsing step.")