from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlmodel import Session, select
from schema.mih.schema_mih import Patients, PatientsPublic, PatientsCreate, PatientsUpdate, PatientsPublicWithMih
from db.manager import Database
from auth.auth_service import AuthService
from fastapi import Request


mih_patients_router = APIRouter(
    # dependencies=[Depends(AuthService.get_current_user)]
)
BASE_URL_PATIENTS = "/patients/"

# Criar um paciente associado a um usuário específico
@mih_patients_router.post("/users" + BASE_URL_PATIENTS, response_model=PatientsPublic)
def create_patient(
    *,
    request: Request,
    session: Session = Depends(Database.get_session),
    patient: PatientsCreate,
):
    """Create a new patient associated with a specific user"""
    user_id = request.session.get("id")  # Obtém o ID do usuário da sessão

    # Adiciona os valores ao modelo
    dates = {"created_at": datetime.now(), "updated_at": datetime.now()}
    db_patient = Patients.model_validate(patient, update=dates)
    db_patient.user_id = user_id  # Define o ID do usuário no paciente
    session.add(db_patient)
    session.commit()
    session.refresh(db_patient)
    return db_patient

# Atualizar paciente
@mih_patients_router.patch(BASE_URL_PATIENTS + "{patient_id}", response_model=PatientsPublic)
def update_patient(
        *,
        session: Session = Depends(Database.get_session),
        patient_id: int,
        patient: PatientsUpdate
):
    """Update patient"""
    db_patient = session.get(Patients, patient_id)
    if not db_patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient_data = patient.model_dump(exclude_unset=True)
    updated_at = {"updated_at": datetime.now()}
    db_patient.sqlmodel_update(patient_data, update=updated_at)
    session.add(db_patient)
    session.commit()
    session.refresh(db_patient)
    return db_patient

# Obter paciente por ID
@mih_patients_router.get(BASE_URL_PATIENTS + "{patient_id}", response_model=PatientsPublic)
def get_patient_by_id(
        *,
        session: Session = Depends(Database.get_session),
        patient_id: int
):
    """Get specific patient"""
    patient = session.get(Patients, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

# Obter todos os pacientes de um dado user_id
@mih_patients_router.get("/users"+ BASE_URL_PATIENTS, response_model=list[PatientsPublic])
def get_all_patients(
        *,
        request:Request,
        session: Session = Depends(Database.get_session),
):
    """Get all patients for a specific user"""
    patients = session.exec(
        select(Patients).where(Patients.user_id == request.session.get("id"))
    ).all()
    return patients

# Obter todos os pacientes
@mih_patients_router.get(BASE_URL_PATIENTS, response_model=list[PatientsPublic])
def get_all_patients(
        *,
        session: Session = Depends(Database.get_session),
        offset: int = 0,
        limit: int = Query(default=100, le=100)
):
    """Get all patients"""
    patients = session.exec(select(Patients).offset(offset).limit(limit)).all()
    return patients

# Obter paciente e suas feridas (MIH)
@mih_patients_router.get(BASE_URL_PATIENTS + "{patient_id}" + "/mih", response_model=PatientsPublicWithMih)
def get_patient_mih(
        *,
        session: Session = Depends(Database.get_session),
        patient_id: int
):
    patient = session.get(Patients, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

# Deletar paciente (e remover feridas associadas)
@mih_patients_router.delete(BASE_URL_PATIENTS + "{patient_id}")
def delete_patient(
        *,
        session: Session = Depends(Database.get_session),
        patient_id: int
):
    """Delete patient"""
    patient = session.get(Patients, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    session.delete(patient)
    session.commit()
    return {"ok": True}
