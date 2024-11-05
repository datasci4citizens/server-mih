from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlmodel import Session
from schema.mih.schema_mih import Mih
from schema.mih.schema_mih import MihPublic
from schema.mih.schema_mih import MihCreate
from schema.mih.schema_mih import MihUpdate
from schema.mih.schema_mih import MihPublicWithPatient
from schema.mih.schema_mih import MihPublicWithTrackingRecords
from db.manager import Database

mih_router = APIRouter()
BASE_URL_MIH = "/mih/"

@mih_router.post(BASE_URL_MIH, response_model=MihPublic)
def create_mih(
        *,
        session: Session = Depends(Database.get_session),
        mih: MihCreate
):
    """Create a new mih"""
    dates = {"created_at": datetime.now(), "updated_at": datetime.now()}
    if mih.start_date == None:
        dates.update({"start_date": datetime.now})
    db_mih = Mih.model_validate(mih, update=dates)
    session.add(db_mih)
    session.commit()
    session.refresh(db_mih)
    return db_mih

@mih_router.patch(BASE_URL_MIH + "{mih_id}", response_model=MihPublic)
def update_mih(
        *,
        session: Session = Depends(Database.get_session),
        mih_id: int,
        mih: MihUpdate
):
    """Update mih end date"""
    db_mih = session.get(Mih, mih_id)
    if not db_mih:
        raise HTTPException(status_code=404, detail="Mih not found")
    mih_data = db_mih.model_dump(exclude_unset=True)
    updated_at = {"updated_at": datetime.now()}
    db_mih.sqlmodel_update(mih_data, update=updated_at)
    session.add(db_mih)
    session.commit()
    session.refresh(db_mih)
    return db_mih


@mih_router.get("/patient" + BASE_URL_MIH + "{mih_id}", response_model=MihPublicWithPatient)
def get_mih_with_patient(
        *,
        session: Session = Depends(Database.get_session),
        mih_id: int
):
    """Get specific mih"""
    mih = session.get(Mih, mih_id)
    if not mih:
        raise HTTPException(status_code=404, detail="Mih not found")
    return mih

@mih_router.get(BASE_URL_MIH + "{mih_id}" + "/tracking-records", response_model=MihPublicWithTrackingRecords)
def get_mih_tracking_records(
        *,
        session: Session = Depends(Database.get_session),
        offset: int = 0,
        limit: int = Query(default=100, le=100),
        mih_id: int
):
    """Get all tracking records from mih"""
    mih = session.get(Mih, mih_id)
    if not mih:
        raise HTTPException(status_code=404, detail="Mih not found")
    return mih

@mih_router.delete(BASE_URL_MIH + "{mih_id}")
def delete_mih(
        *,
        session: Session = Depends(Database.get_session),
        mih_id: int
):
    """Delete mih"""
    mih = session.get(Mih, mih_id)
    if not mih:
        raise HTTPException(status_code=404, detail="Mih not found")
    session.delete(mih)
    session.commit()
    return {"ok": True}