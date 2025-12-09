import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db, SessionLocal
from app.core.auth import get_current_user
from app.models.models import Paystub
from app.schemas.schemas import UserContext, PaystubOut
from app.services.ocr_service import run_ocr_and_parse

router = APIRouter()

@router.post("", response_model=PaystubOut)
def upload_paystub(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Save file locally for now; replace with Supabase storage / S3.
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_id = str(uuid.uuid4())
    file_path = os.path.join(upload_dir, f"{file_id}_{file.filename}")

    with open(file_path, "wb") as f:
        f.write(file.file.read())

    paystub = Paystub(
        user_id=current_user.user_id,
        file_url=file_path,  # in prod, use public URL
        status="processing",
    )
    db.add(paystub)
    db.commit()
    db.refresh(paystub)

    # Kick off OCR in background
    background_tasks.add_task(run_ocr_and_parse, paystub.id, file_path, SessionLocal())

    return paystub

@router.get("", response_model=List[PaystubOut])
def list_paystubs(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    paystubs = (
        db.query(Paystub)
        .filter(Paystub.user_id == current_user.user_id)
        .order_by(Paystub.upload_date.desc())
        .all()
    )
    return paystubs

@router.get("/{paystub_id}", response_model=PaystubOut)
def get_paystub(
    paystub_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    paystub = (
        db.query(Paystub)
        .filter(Paystub.id == paystub_id, Paystub.user_id == current_user.user_id)
        .first()
    )
    if not paystub:
        raise HTTPException(404, "Paystub not found")
    return paystub

@router.delete("/{paystub_id}", status_code=204)
def delete_paystub(
    paystub_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    paystub = (
        db.query(Paystub)
        .filter(Paystub.id == paystub_id, Paystub.user_id == current_user.user_id)
        .first()
    )
    if not paystub:
        raise HTTPException(404, "Paystub not found")
    db.delete(paystub)
    db.commit()
    return None
