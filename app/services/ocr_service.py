import uuid
from sqlalchemy.orm import Session
from app.models.models import Paystub

def run_ocr_and_parse(paystub_id: uuid.UUID, file_path: str, db: Session):
    """
    TODO: replace with real PaddleOCR and heuristic parsing.
    """
    paystub = db.query(Paystub).filter(Paystub.id == paystub_id).first()
    if not paystub:
        return

    try:
        # Fake OCR text
        ocr_text = f"FAKE OCR TEXT for file {file_path}"
        parsed_data = {
            "gross_pay": 5000,
            "net_pay": 3800,
            "pto_hours": 40,
            "hsa_balance": 1200,
            "fsa_balance": 500,
        }

        paystub.ocr_text = ocr_text
        paystub.parsed_data = parsed_data
        paystub.status = "done"
        db.commit()
    except Exception as e:
        paystub.status = "error"
        paystub.error_message = str(e)
        db.commit()
