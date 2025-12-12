
import uuid
import logging
import os
import fitz  # PyMuPDF
import numpy as np
from PIL import Image
from sqlalchemy.orm import Session
from app.models.models import Paystub
import openai
import json
from dotenv import load_dotenv

load_dotenv()

# Setup OpenAI Client
client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)

# PaddleOCR Setup
try:
    from paddleocr import PaddleOCR
    # Initialize PaddleOCR
    # use_angle_cls=True allows detecting rotated text
    ocr_engine = PaddleOCR(use_angle_cls=True, lang='en')
    HAS_OCR = True
except ImportError:
    ocr_engine = None
    HAS_OCR = False
    logging.warning("PaddleOCR not installed.")

# Helper for PDF->Image conversion
def pdf_page_to_image(page):
    """Convert a PyMuPDF page to an image suitable for Pillow/Paddle."""
    # Increase resolution for better OCR. Standard is 72 DPI.
    # Zoom of 3.0 gives ~216 DPI.
    mat = fitz.Matrix(3, 3)
    pix = page.get_pixmap(matrix=mat)
    # PaddleOCR expects numpy array
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return np.array(img)

def extract_text_from_pdf(file_path):
    """Extracts raw text from PDF directly using PyMuPDF."""
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    return text

def run_ocr_and_parse(paystub_id: uuid.UUID, file_path: str, db: Session):
    """
    Extracts text (from PDF or OCR for images) and uses LLM to parse it into structured data.
    """
    paystub = db.query(Paystub).filter(Paystub.id == paystub_id).first()
    if not paystub:
        return

    try:
        extracted_text = ""
        is_scanned_or_image = False
        
        # 1. EXTRACT TEXT
        if file_path.lower().endswith(".pdf"):
            # Try direct text extraction first
            extracted_text = extract_text_from_pdf(file_path)
            
            # If text is too short, it implies a scanned PDF -> Use OCR
            if len(extracted_text.strip()) < 50:
                is_scanned_or_image = True
                if HAS_OCR and ocr_engine:
                    doc = fitz.open(file_path)
                    full_text = []
                    for page_num in range(len(doc)):
                        page = doc.load_page(page_num)
                        img_array = pdf_page_to_image(page)
                        result = ocr_engine.ocr(img_array)
                        
                        if result and result[0]:
                            page_text = "\n".join([line[1][0] for line in result[0] if line and line[1]])
                            full_text.append(page_text)
                    extracted_text = "\n".join(full_text)
        else:
            # Handle Images (JPG, PNG)
            is_scanned_or_image = True
            if HAS_OCR and ocr_engine:
                result = ocr_engine.ocr(file_path)
                if result and result[0]:
                    lines = [line[1][0] for line in result[0] if line and line[1]]
                    extracted_text = "\n".join(lines)

        paystub.ocr_text = extracted_text
        
        # 2. PARSE WITH LLM
        # Logic: Always parse if we have text.
        # But per user request: "call llm only in ocr method if that is image or we can't extract text"
        # Wait, I think the user meant: "Use LLM for parsing ONLY if we successfully extracted text (whether via PDF text layer OR via OCR)."
        # OR "If it is an image/scanned PDF, we MUST use LLM to parse the messy OCR text. If it was clean PDF text, maybe we don't need LLM?" 
        # Actually, raw PDF text is also messy (layout wise), so LLM is almost always needed to get STRUCTURED JSON.
        
        # Interpretation: The user wants to ensure we use the LLM to structure the data, REGARDLESS of source, 
        # but specifically mentioned the condition "if that is image or we can't extract text".
        # This sounds like robust handling: If direct extraction fails, use OCR, THEN use LLM.
        # I will stick to: Extract Text (Method A or Method B) -> If Text exists -> Parse with LLM.
        
        if extracted_text:
            prompt = f"""
            Extract the following fields from this paystub text into JSON format:
            - gross_pay (number)
            - net_pay (number)
            - pto_hours (number, total balance if available)
            - hsa_balance (number)
            - fsa_balance (number)
            
            Return ONLY the JSON. No markdown formatting.
            
            Paystub Text:
            {extracted_text[:4000]} 
            """
            
            chat_completion = client.chat.completions.create(
                model="gemma-3-27b-it", 
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            response_content = chat_completion.choices[0].message.content
            # Clean up potential markdown code blocks
            response_content = response_content.replace("```json", "").replace("```", "").strip()
            
            try:
                parsed_data = json.loads(response_content)
                paystub.parsed_data = parsed_data
            except json.JSONDecodeError:
                logging.error("Failed to decode LLM response")
                pass

        paystub.status = "done"
        db.commit()

    except Exception as e:
        logging.error(f"Processing failed: {e}")
        paystub.status = "error"
        paystub.error_message = str(e)
        db.commit()
