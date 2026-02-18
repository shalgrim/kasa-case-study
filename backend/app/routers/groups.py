from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Hotel, HotelGroup, HotelGroupMembership, User

router = APIRouter()


class GroupCreate(BaseModel):
    name: str
    hotel_ids: list[int] = []


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    hotel_ids: Optional[list[int]] = None


class GroupOut(BaseModel):
    id: int
    name: str
    hotel_count: int

    class Config:
        from_attributes = True


class GroupDetail(BaseModel):
    id: int
    name: str
    hotels: list[dict]


@router.post("", response_model=GroupOut)
def create_group(req: GroupCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group = HotelGroup(name=req.name, user_id=user.id)
    db.add(group)
    db.flush()
    for hid in req.hotel_ids:
        db.add(HotelGroupMembership(group_id=group.id, hotel_id=hid))
    db.commit()
    db.refresh(group)
    return GroupOut(id=group.id, name=group.name, hotel_count=len(group.memberships))


@router.get("", response_model=list[GroupOut])
def list_groups(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    groups = db.query(HotelGroup).filter(HotelGroup.user_id == user.id).all()
    return [GroupOut(id=g.id, name=g.name, hotel_count=len(g.memberships)) for g in groups]


@router.get("/{group_id}", response_model=GroupDetail)
def get_group(group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group = db.query(HotelGroup).filter(HotelGroup.id == group_id, HotelGroup.user_id == user.id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    hotels = []
    for m in group.memberships:
        hotel = m.hotel
        latest = hotel.snapshots[0] if hotel.snapshots else None
        hotels.append({
            "id": hotel.id,
            "name": hotel.name,
            "city": hotel.city,
            "state": hotel.state,
            "google_normalized": latest.google_normalized if latest else None,
            "booking_normalized": latest.booking_normalized if latest else None,
            "expedia_normalized": latest.expedia_normalized if latest else None,
            "tripadvisor_normalized": latest.tripadvisor_normalized if latest else None,
            "weighted_average": latest.weighted_average if latest else None,
        })
    return GroupDetail(id=group.id, name=group.name, hotels=hotels)


@router.put("/{group_id}", response_model=GroupOut)
def update_group(group_id: int, req: GroupUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group = db.query(HotelGroup).filter(HotelGroup.id == group_id, HotelGroup.user_id == user.id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if req.name is not None:
        group.name = req.name
    if req.hotel_ids is not None:
        db.query(HotelGroupMembership).filter(HotelGroupMembership.group_id == group.id).delete()
        for hid in req.hotel_ids:
            db.add(HotelGroupMembership(group_id=group.id, hotel_id=hid))
    db.commit()
    db.refresh(group)
    return GroupOut(id=group.id, name=group.name, hotel_count=len(group.memberships))


@router.delete("/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group = db.query(HotelGroup).filter(HotelGroup.id == group_id, HotelGroup.user_id == user.id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    db.delete(group)
    db.commit()
    return {"deleted": True}
