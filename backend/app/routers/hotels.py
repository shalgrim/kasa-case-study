from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session, joinedload

from ..auth import get_current_user
from ..database import get_db
from ..models import Hotel, HotelGroupMembership, ReviewSnapshot, User
from ..services.csv_import import import_csv

router = APIRouter()


def _escape_like(term: str) -> str:
    """Escape %, _, and \\ so they are treated as literals in LIKE/ILIKE."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class HotelCreate(BaseModel):
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    website: Optional[str] = None
    booking_name: Optional[str] = None
    expedia_name: Optional[str] = None
    tripadvisor_name: Optional[str] = None


class HotelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    keys: Optional[int] = None
    kind: Optional[str] = None
    brand: Optional[str] = None
    parent: Optional[str] = None
    website: Optional[str] = None
    booking_name: Optional[str] = None
    expedia_name: Optional[str] = None
    tripadvisor_name: Optional[str] = None


class SnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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

    @classmethod
    def from_model(cls, snapshot: "ReviewSnapshot") -> "SnapshotOut":
        return cls(
            id=snapshot.id,
            hotel_id=snapshot.hotel_id,
            collected_at=snapshot.collected_at.isoformat(),
            source=snapshot.source,
            google_score=snapshot.google_score,
            google_count=snapshot.google_count,
            booking_score=snapshot.booking_score,
            booking_count=snapshot.booking_count,
            expedia_score=snapshot.expedia_score,
            expedia_count=snapshot.expedia_count,
            tripadvisor_score=snapshot.tripadvisor_score,
            tripadvisor_count=snapshot.tripadvisor_count,
            google_normalized=snapshot.google_normalized,
            booking_normalized=snapshot.booking_normalized,
            expedia_normalized=snapshot.expedia_normalized,
            tripadvisor_normalized=snapshot.tripadvisor_normalized,
            weighted_average=snapshot.weighted_average,
        )


class HotelDetail(HotelOut):
    latest_snapshot: Optional[SnapshotOut] = None


@router.post("", response_model=HotelDetail)
def create_hotel(
    payload: HotelCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    hotel = Hotel(
        name=payload.name,
        city=payload.city,
        state=payload.state,
        website=payload.website,
        booking_name=payload.booking_name,
        expedia_name=payload.expedia_name,
        tripadvisor_name=payload.tripadvisor_name,
    )
    db.add(hotel)
    db.commit()
    db.refresh(hotel)
    return HotelDetail.model_validate(hotel)


@router.post("/import-csv")
def import_csv_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    content = file.file.read().decode("utf-8")
    count = import_csv(content, db)
    return {"imported": count}


@router.get("")
def list_hotels(
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("name"),
    sort_dir: Optional[str] = Query("asc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Hotel).options(joinedload(Hotel.snapshots))
    if search:
        term = f"%{_escape_like(search)}%"
        query = query.filter(
            Hotel.name.ilike(term, escape="\\")
            | Hotel.city.ilike(term, escape="\\")
            | Hotel.state.ilike(term, escape="\\")
        )

    # Sort
    ALLOWED_SORT_FIELDS = {"name", "city", "state", "keys", "kind", "brand", "parent"}
    sort_column = (
        getattr(Hotel, sort_by) if sort_by in ALLOWED_SORT_FIELDS else Hotel.name
    )
    if sort_dir == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    total = query.count()
    hotels = query.offset((page - 1) * page_size).limit(page_size).all()
    results = []
    for hotel in hotels:
        latest = hotel.snapshots[0] if hotel.snapshots else None
        detail = HotelDetail.model_validate(hotel)
        if latest:
            detail.latest_snapshot = SnapshotOut.from_model(latest)
        results.append(detail)
    return {"items": results, "total": total, "page": page, "page_size": page_size}


@router.get("/{hotel_id}", response_model=HotelDetail)
def get_hotel(
    hotel_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    latest = hotel.snapshots[0] if hotel.snapshots else None
    detail = HotelDetail.model_validate(hotel)
    if latest:
        detail.latest_snapshot = SnapshotOut.from_model(latest)
    return detail


# TODO: Restrict deletion to admins (or hotel creator). The confirm param
# prevents accidental calls but any authenticated user can still delete.
# Deferring to cleanup phase in the interest of time.
@router.delete("/{hotel_id}")
def delete_hotel(
    hotel_id: int,
    confirm: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not confirm:
        raise HTTPException(status_code=400, detail="Pass ?confirm=true to delete")
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    db.query(HotelGroupMembership).filter(
        HotelGroupMembership.hotel_id == hotel_id
    ).delete()
    db.delete(hotel)
    db.commit()
    return {"deleted": True}


@router.get("/{hotel_id}/history", response_model=list[SnapshotOut])
def get_hotel_history(
    hotel_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    return [SnapshotOut.from_model(s) for s in hotel.snapshots]
