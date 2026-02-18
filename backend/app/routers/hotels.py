import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Hotel, ReviewSnapshot, User
from ..services.csv_import import import_csv
from ..services.scoring import compute_scores

router = APIRouter()


class HotelOut(BaseModel):
    id: int
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    keys: Optional[int] = None
    kind: Optional[str] = None
    brand: Optional[str] = None
    parent: Optional[str] = None
    booking_name: Optional[str] = None
    expedia_name: Optional[str] = None
    tripadvisor_name: Optional[str] = None

    class Config:
        from_attributes = True


class SnapshotOut(BaseModel):
    id: int
    hotel_id: int
    collected_at: str
    source: str
    google_score: Optional[float] = None
    google_count: Optional[int] = None
    booking_score: Optional[float] = None
    booking_count: Optional[int] = None
    expedia_score: Optional[float] = None
    expedia_count: Optional[int] = None
    tripadvisor_score: Optional[float] = None
    tripadvisor_count: Optional[int] = None
    google_normalized: Optional[float] = None
    booking_normalized: Optional[float] = None
    expedia_normalized: Optional[float] = None
    tripadvisor_normalized: Optional[float] = None
    weighted_average: Optional[float] = None

    class Config:
        from_attributes = True


class HotelDetail(HotelOut):
    latest_snapshot: Optional[SnapshotOut] = None


@router.post("/import-csv")
def import_csv_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    content = file.file.read().decode("utf-8")
    count = import_csv(content, db)
    return {"imported": count}


@router.get("", response_model=list[HotelDetail])
def list_hotels(
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("name"),
    sort_dir: Optional[str] = Query("asc"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Hotel)
    if search:
        query = query.filter(
            Hotel.name.ilike(f"%{search}%")
            | Hotel.city.ilike(f"%{search}%")
            | Hotel.state.ilike(f"%{search}%")
        )

    # Sort
    sort_column = getattr(Hotel, sort_by, Hotel.name)
    if sort_dir == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    hotels = query.all()
    results = []
    for hotel in hotels:
        latest = hotel.snapshots[0] if hotel.snapshots else None
        detail = HotelDetail.model_validate(hotel)
        if latest:
            detail.latest_snapshot = SnapshotOut(
                id=latest.id,
                hotel_id=latest.hotel_id,
                collected_at=latest.collected_at.isoformat(),
                source=latest.source,
                google_score=latest.google_score,
                google_count=latest.google_count,
                booking_score=latest.booking_score,
                booking_count=latest.booking_count,
                expedia_score=latest.expedia_score,
                expedia_count=latest.expedia_count,
                tripadvisor_score=latest.tripadvisor_score,
                tripadvisor_count=latest.tripadvisor_count,
                google_normalized=latest.google_normalized,
                booking_normalized=latest.booking_normalized,
                expedia_normalized=latest.expedia_normalized,
                tripadvisor_normalized=latest.tripadvisor_normalized,
                weighted_average=latest.weighted_average,
            )
        results.append(detail)
    return results


@router.get("/{hotel_id}", response_model=HotelDetail)
def get_hotel(hotel_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    latest = hotel.snapshots[0] if hotel.snapshots else None
    detail = HotelDetail.model_validate(hotel)
    if latest:
        detail.latest_snapshot = SnapshotOut(
            id=latest.id,
            hotel_id=latest.hotel_id,
            collected_at=latest.collected_at.isoformat(),
            source=latest.source,
            google_score=latest.google_score,
            google_count=latest.google_count,
            booking_score=latest.booking_score,
            booking_count=latest.booking_count,
            expedia_score=latest.expedia_score,
            expedia_count=latest.expedia_count,
            tripadvisor_score=latest.tripadvisor_score,
            tripadvisor_count=latest.tripadvisor_count,
            google_normalized=latest.google_normalized,
            booking_normalized=latest.booking_normalized,
            expedia_normalized=latest.expedia_normalized,
            tripadvisor_normalized=latest.tripadvisor_normalized,
            weighted_average=latest.weighted_average,
        )
    return detail


@router.get("/{hotel_id}/history", response_model=list[SnapshotOut])
def get_hotel_history(hotel_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    return [
        SnapshotOut(
            id=s.id,
            hotel_id=s.hotel_id,
            collected_at=s.collected_at.isoformat(),
            source=s.source,
            google_score=s.google_score,
            google_count=s.google_count,
            booking_score=s.booking_score,
            booking_count=s.booking_count,
            expedia_score=s.expedia_score,
            expedia_count=s.expedia_count,
            tripadvisor_score=s.tripadvisor_score,
            tripadvisor_count=s.tripadvisor_count,
            google_normalized=s.google_normalized,
            booking_normalized=s.booking_normalized,
            expedia_normalized=s.expedia_normalized,
            tripadvisor_normalized=s.tripadvisor_normalized,
            weighted_average=s.weighted_average,
        )
        for s in hotel.snapshots
    ]
