from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from PIL import Image, ImageEnhance
import pytesseract
import io
import re
from datetime import datetime
from typing import Dict, List

app = FastAPI(
    title="Receipt Scanner API",
    description="API for scanning and parsing receipt images",
    version="1.0.0"
)

# Add custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Receipt Scanner API",
        version="1.0.0",
        description="API for scanning and parsing receipt images",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Keep existing CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Receipt Scanner API is running"}


def extract_total(text): 
    # First try to find the last total amount in the text
    lines = text.split('\n')
    total = None
    
    # Look for lines containing total from bottom up
    for line in reversed(lines):
        line = line.lower()
        if 'total' in line:
            matches = re.findall(r'(\d+\.\d{2})', line)
            if matches:
                try:
                    return float(matches[-1])
                except ValueError:
                    continue
    
    # If no total found with word "total", get the last number in receipt
    all_amounts = re.findall(r'(\d+\.\d{2})', text)
    if all_amounts:
        try:
            return float(all_amounts[-1])
        except ValueError:
            pass
    
    return None


def extract_date(text): 
    date_pattern = r'\d{2}/\d{2}/\d{2,4}'
    match = re.search(date_pattern, text)
    if match:
        date_str = match.group(0)
        try:
            return datetime.strptime(date_str, '%m/%d/%y').strftime('%Y-%m-%d')
        except:
            return None
    return None

def extract_items(text):
    items = []
    lines = text.split('\n')
    
    # Clean and combine lines that might be split
    current_item = ""
    for line in lines:
        # Look for lines with price patterns
        price_match = re.search(r'\$?(\d+\.\d{2})', line)
        
        if price_match and not any(x in line.lower() for x in ['total', 'sub', 'tax']):
            price = float(price_match.group(1))
            
            # Clean up the item name
            item_name = line.replace(price_match.group(0), '').strip()
            
            # If the previous line didn't have a price, it might be part of this item's name
            if current_item and not re.search(r'\d+\.\d{2}', current_item):
                item_name = f"{current_item} {item_name}".strip()
            
            # Clean up common OCR mistakes
            item_name = re.sub(r'\s+', ' ', item_name)  # Remove multiple spaces
            item_name = re.sub(r'[^\w\s]', '', item_name)  # Remove special characters
            
            # Capitalize words properly
            item_name = ' '.join(word.capitalize() for word in item_name.split())
            
            if item_name:
                items.append({
                    "name": item_name,
                    "price": price
                })
            current_item = ""
        else:
            current_item = line.strip()
    
    return items

# Add expense categories
EXPENSE_CATEGORIES = {
    'groceries': ['food', 'grocery', 'market', 'supermarket'],
    'dining': ['restaurant', 'cafe', 'dining', 'bar', 'coffee'],
    'utilities': ['electric', 'water', 'gas', 'internet', 'phone'],
    'shopping': ['mall', 'store', 'retail', 'clothing'],
    'transportation': ['gas', 'fuel', 'transit', 'parking'],
    'entertainment': ['movie', 'theatre', 'game', 'entertainment']
}

def categorize_expense(merchant: str) -> str:
    merchant_lower = merchant.lower()
    for category, keywords in EXPENSE_CATEGORIES.items():
        if any(keyword in merchant_lower for keyword in keywords):
            return category
    return 'other'

@app.post("/scan-receipt")
async def scan_receipt(file: UploadFile = File(...)):
    try:
        # Read the image
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Keep original color but enhance contrast and sharpness
        image = image.convert('RGB')  # Ensure RGB color mode
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)  # Increase contrast
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)  # Increase sharpness
        
        # Extract text with improved configuration for receipt format
        text = pytesseract.image_to_string(
            image,
            config='--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.:$-/ '
        )
        
        # Print raw text for debugging
        print("Extracted Text:", text)
        
        # Look specifically for total amount
        total = None
        lines = text.split('\n')
        for line in reversed(lines):
            if any(word in line.lower() for word in ['total', 'amount due', 'grand total']):
                numbers = re.findall(r'(\d+\.\d{2})', line)
                if numbers:
                    total = float(numbers[-1])
                    break
        
        structured_data = {
            "status": "success",
            "raw_text": text,
            "total": total,
            "date": extract_date(text),
            "items": extract_items(text),
            "merchant": text.split('\n')[0].strip(),
            "category": "other"  # Simplified category
        }
        
        return structured_data
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }