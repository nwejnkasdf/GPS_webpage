from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from auth import require_admin_api
from database import get_db
from models.club_image import ClubImage
from schemas.club_image import ClubImageRead, ClubImageUpdate

router = APIRouter()

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB


@router.get("/club-images", response_model=list[ClubImageRead])
def list_images(db: Session = Depends(get_db)):
    return db.query(ClubImage).order_by(ClubImage.sort_order.asc(), ClubImage.id.asc()).all()


@router.post("/club-images", response_model=ClubImageRead, status_code=201, dependencies=[Depends(require_admin_api)])
async def upload_image(
    file: UploadFile = File(...),
    caption: str = Form(default=""),
    sort_order: int = Form(default=0),
    db: Session = Depends(get_db),
):
    data = await file.read()
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="이미지 크기가 10MB를 초과합니다.")

    content_type = file.content_type or "image/jpeg"
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드할 수 있습니다.")

    img = ClubImage(
        filename=file.filename or "image",
        content_type=content_type,
        data=data,
        caption=caption,
        sort_order=sort_order,
    )
    db.add(img)
    db.commit()
    db.refresh(img)
    return img


@router.put("/club-images/{image_id}", response_model=ClubImageRead, dependencies=[Depends(require_admin_api)])
def update_image(image_id: int, data: ClubImageUpdate, db: Session = Depends(get_db)):
    img = db.query(ClubImage).filter(ClubImage.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(img, field, value)
    db.commit()
    db.refresh(img)
    return img


@router.delete("/club-images/{image_id}", status_code=204, dependencies=[Depends(require_admin_api)])
def delete_image(image_id: int, db: Session = Depends(get_db)):
    img = db.query(ClubImage).filter(ClubImage.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    db.delete(img)
    db.commit()
