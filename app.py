import os
import re
import csv
import pdfplumber

def classify_document(filename, text):
    """Dynamically classifies Credit vs Standard vs PO invoices."""
    name_lower = filename.lower()
    
    # 1. Identify Credit Invoices[cite: 1]
    if "credit" in name_lower:
        return "Credit Invoice"
    
    # 2. Identify PO Invoices[cite: 1]
    # Checks for 'po' in filename or if it ends in an 8-digit sequence
    if "po" in name_lower or re.search(r'\d{8}$', os.path.splitext(filename)[0]):
        return "Invoice (with PO)"
        
    # 3. Default to Standard Invoice
    return "Invoice"

def extract_details(text):
    """Extracts Invoice #, PO #, and Total using regex."""
    data = {"invoice_number": "N/A", "po_number": "N/A", "total_amount": "N/A"}
    
    # Dynamic regex patterns for extraction
    inv_match = re.search(r"(?:Invoice|Credit Note)\s*[:#]?\s*(\d{10})", text, re.IGNORECASE)
    po_match = re.search(r"(?:PO|Purchase Order|P\.O\.)\s*[:#]?\s*(\d{8,})", text, re.IGNORECASE)
    total_match = re.search(r"(?:Total|Amount Due)\s*[:\$\s]*([\d,\.]+)", text, re.IGNORECASE)
    
    if inv_match: data["invoice_number"] = inv_match.group(1)
    if po_match: data["po_number"] = po_match.group(1)
    if total_match: data["total_amount"] = total_match.group(1)
    
    return data

def process_nilfisk_invoices(input_folder="./invoices", output_file="processed_invoices.csv"):
    """Main function to loop through files and process data."""
    results = []
    
    # Ensure directory exists
    if not os.path.exists(input_folder):
        print(f"Directory {input_folder} not found.")
        return

    for filename in os.listdir(input_folder):
        if filename.endswith(".pdf"):
            file_path = os.path.join(input_folder, filename)
            
            # Read text from PDF
            full_text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    full_text += page.extract_text() or ""
            
            # Classify and Extract data
            doc_type = classify_document(filename, full_text)
            details = extract_details(full_text)
            
            results.append({
                "Filename": filename,
                "Document Type": doc_type,
                "Invoice #": details["invoice_number"],
                "PO #": details["po_number"],
                "Total": details["total_amount"]
            })
            
    # Save the consolidated results to CSV
    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Filename", "Document Type", "Invoice #", "PO #", "Total"])
        writer.writeheader()
        writer.writerows(results)
    
    print(f"Success! Processed {len(results)} files. Saved to {output_file}.")

# You can trigger the processing by calling this function:
# process_nilfisk_invoices(input_folder="./your_invoice_folder")
