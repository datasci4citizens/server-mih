from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlmodel import Session, select
from sqlalchemy.orm import joinedload

from schema.mih.schema_mih import Mih
from schema.mih.schema_mih import MihPublic
from schema.mih.schema_mih import MihCreate
from schema.mih.schema_mih import MihUpdate
from schema.mih.schema_mih import MihPublicWithPatient
from schema.mih.schema_mih import MihPublicWithTrackingRecords
from db.manager import Database

mih_router = APIRouter()
BASE_URL_MIH = "/mih/"

@mih_router.post("/"+"{patient_id}" + BASE_URL_MIH, response_model=MihPublic)
def create_mih(
        *,
        session: Session = Depends(Database.get_session),
        mih: MihCreate,
        patient_id: int
):
    """Create a new mih"""
    dates = {"created_at": datetime.now(), "updated_at": datetime.now()}
    if mih.start_date == None:
        dates.update({"start_date": datetime.now})
    db_mih = Mih.model_validate(mih, update=dates)
    db_mih.patient_id = patient_id
    session.add(db_mih)
    session.commit()
    session.refresh(db_mih)
    return db_mih

@mih_router.patch(BASE_URL_MIH + "{mih_id}", response_model=MihPublic)
def update_mih(
        *,
        session: Session = Depends(Database.get_session),
        mih_id: int,
        update_data: MihUpdate  # Recebe apenas o diagnóstico
):
    """Update mih diagnosis"""
    db_mih = session.get(Mih, mih_id)
    if not db_mih:
        raise HTTPException(status_code=404, detail="Mih not found")
    
    # Atualiza apenas o campo diagnosis
    db_mih.diagnosis = update_data.diagnosis
    db_mih.updated_at = datetime.now()  # Atualiza a data de modificação

    # Salva no banco de dados
    session.add(db_mih)
    session.commit()
    session.refresh(db_mih)
    return db_mih

@mih_router.get("/" + "{patient_id}" + BASE_URL_MIH + "{mih_id}", response_model=MihPublicWithPatient)
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


# Novo endpoint para listar MIH não diagnosticados para especialistas
@mih_router.get(BASE_URL_MIH + "undiagnosed", response_model=list[MihPublic])
def get_undiagnosed_mih(
        *,
        session: Session = Depends(Database.get_session),
        limit: int = Query(10, ge=1),  # Número máximo de registros a retornar
        offset: int = Query(0, ge=0),  # Ponto de partida nos registros
):
    """Get undiagnosed MIH (accessible only to specialists)"""
    
    # Busca apenas os MIH não diagnosticados com paginação
    undiagnosed_mih = session.exec(
        select(Mih)
        .where(Mih.diagnosis.is_(None))
        .offset(offset)  # Pular registros iniciais
        .limit(limit)    # Limitar o número de registros retornados
    ).all()
    
    return undiagnosed_mih