import re
import pdfplumber
import json

def find_field(text, patterns):
    """
    Helper function that iterates through a list of regex patterns 
    until it finds a match.
    """
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return "Not found"

def process_pdf(file_path, filename):
    """
    Parses a PDF file and returns a structured JSON object.
    """
    invoice_json = {
        "fileName": filename,
        "fileType": "PDF",
        "documentType": "Credit Note" if "credit" in filename.lower() else "Invoice",
        "invoiceNumber": None,
        "poNumber": None,
        "totalAmount": "0.00",
        "items": []
    }

    with pdfplumber.open(file_path) as pdf:
        # 1. Extract full text for field searching
        full_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

        # 2. Extract Header Fields using flexible patterns
        invoice_json["invoiceNumber"] = find_field(full_text, [
            r"(?:Invoice|Credit Note|Document)\s*Number\s*[|:]?\s*([\w-]+)",
            r"Number\s*[|:]?\s*([\w-]+)"
        ])
        
        invoice_json["poNumber"] = find_field(full_text, [
            r"PO\s*Number\s*[|:]?\s*([\w-]+)",
            r"Purchase Order\s*[|:]?\s*([\w-]+)"
        ])
        
        # Extract total/credit amount and remove commas
        total_str = find_field(full_text, [
            r"(?:Total|Credit)\s*amount\s*[|:]?\s*([\d,.]+)",
            r"Total\s*Due\s*[|:]?\s*([\d,.]+)"
        ])
        invoice_json["totalAmount"] = total_str.replace(",", "") if total_str != "Not found" else "0.00"

        # 3. Extract Table Items
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                for row in table:
                    # Filter empty cells and convert to string for processing
                    clean_row = [str(cell) for cell in row if cell is not None]
                    row_str = " ".join(clean_row)
                    
                    # Pattern for identifying Material Codes (e.g., 8-digit numbers or XX-12345)
                    material_match = re.search(r"([A-Z]{2}\s?\d{5}|\d{8,})", row_str)
                    
                    if material_match:
                        invoice_json["items"].append({
                            "materialCode": material_match.group(0),
                            "rawRow": row_str
                        })
                        
    return invoice_json

# --- Example Usage ---
# result = process_pdf("path/to/your/invoice.pdf", "invoice_001.pdf")
# print(json.dumps(result, indent=4))
