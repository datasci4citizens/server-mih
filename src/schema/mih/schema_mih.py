from typing import List  # Adicione esta linha para corrigir o erro
from sqlalchemy.orm import relationship  # Importação correta do SQLAlchemy
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from sqlmodel import SQLModel, Field
from typing import Optional
from enum import Enum


# Enum para os tipos de usuário
class UserRole(str, Enum):
    RESPONSIBLE = "responsible"
    SPECIALIST = "specialist"

# Base para as operações de CRUD
class UserBase(SQLModel):
    name: str  # Campo obrigatório
    email: str  # Campo obrigatório
    role: UserRole  # Define se é responsável ou especialista
    #personInCharge: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    neighborhood: Optional[str] = None
    phone_number: Optional[str] = None
    is_allowed: Optional[bool] = None
    accept_tcle: Optional[bool] = None

class UserCreate(UserBase):
    pass

class UserRead(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

class UserUpdate(SQLModel):
    email: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    neighborhood: Optional[str] = None

# Tabela principal de usuário
class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Relacionamento com a tabela de pacientes
    patients: Optional[List["Patients"]] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "passive_deletes": True}
    )








""" SPECIALISTS TABLES """
""" class SpecialistsBase(SQLModel):
    email: str
    name: str
    phone_number: str
    is_allowed: bool | None = None

class SpecialistsCreate(SpecialistsBase):
    pass

class SpecialistsPublic(SpecialistsBase):
    specialist_id: int
    created_at: datetime
    updated_at: datetime

class SpecialistsUpdate(SQLModel):
    email: str | None = None
    name: str | None = None
    phone_number: str | None = None

class Specialists(SpecialistsBase, table=True):
    specialist_id: int = Field(default=None, primary_key=True)
    created_at: datetime
    updated_at: datetime """


""" PATIENTS TABLES """
class PatientsBase(SQLModel):
    name: str
    birthday: datetime | None = None
    highFever: bool | None = None
    premature: bool | None = None
    deliveryProblems: bool | None = None
    lowWeight: bool | None = None
    deliveryType: str | None = None
    brothersNumber: int | None = None
    consultType: str | None = None
    deliveryProblemsTypes: str | None = None

class PatientsCreate(PatientsBase):
    pass 

class PatientsUpdate(SQLModel):
    name: str | None = None
    birthday: datetime | None = None
    highFever: bool | None = None
    premature: bool | None = None
    deliveryProblems: bool | None = None
    lowWeight: bool | None = None
    deliveryType: str | None = None
    brothersNumber: int | None = None
    consultType: str | None = None
class PatientsPublic(PatientsBase):
    patient_id: int
    created_at: datetime
    updated_at: datetime

class Patients(PatientsBase, table=True):
    patient_id: int = Field(default=None, primary_key=True)
    created_at: datetime
    updated_at: datetime
     # Chave estrangeira para referenciar o usuário
    user_id: int | None = Field(default=None, foreign_key="user.id")

    # Relacionamento com a tabela User
    user: User = Relationship(back_populates="patients")

    mih: List["Mih"] = Relationship(back_populates="patient", cascade_delete=True)


""" Mih TABLES """
""" no tutorial do sqlmodel, mih é o hero e patient e mih_type é o team"""
class MihBase(SQLModel):
    start_date: datetime
    end_date: datetime | None = None
    painLevel: int | None = None
    sensitivityField: bool | None = None
    stain: bool | None = None
    aestheticDiscomfort: bool | None = None
    userObservations: str | None = None
    specialistObservations: str | None = None
    diagnosis: str | None = None


class MihCreate(MihBase):
    pass

class MihUpdate(SQLModel):
    # mih_location: str | None = None # acho que não deveria da pra mudar a localização da ferida
    # start_date: datetime | None = None
    diagnosis: str | None = None
    specialistObservations: str | None = None

    # mih_type_id: int | None = None

class MihPublic(MihBase):
    mih_id: int

class Mih(MihBase, table = True):
    mih_id: int = Field(default=None, primary_key=True)
    created_at: datetime
    updated_at: datetime
    patient_id: int | None = Field(default=None, foreign_key="patients.patient_id")
    patient: Patients = Relationship(back_populates="mih")



""" TRACKING RECORDS TABLES"""
class TrackingRecordsBase(SQLModel):
    image_id: int
    observations: str | None = None
    
class TrackingRecordsCreate(TrackingRecordsBase):
    pass

class TrackingRecordsUpdate(SQLModel):
    image_id: int | None = None
    observations: str | None = None

class TrackingRecordsPublic(TrackingRecordsBase):
    tracking_record_id: int
    created_at: datetime

class TrackingRecords(TrackingRecordsBase, table = True):
    tracking_record_id: int = Field(default=None, primary_key=True)
    created_at: datetime
    updated_at: datetime
    
""" DATA MODELS FOR RELATIONSHIPS """
class PatientsPublicWithMih(PatientsPublic):
    mih: list[MihPublic] = []

class MihPublicWithPatient(MihPublic):
    patient: PatientsPublic | None = None

class MihPublicWithTrackingRecords(MihPublic):
    tracking_records: list[TrackingRecordsPublic] = []

""" class SpecialistsPublicWithTrackingRecords(SpecialistsPublic):
    pass """


""" IMAGES TABLES """
class ImagesBase(SQLModel):
    extension: str

class ImagesCreate(ImagesBase):
    pass

class Images(ImagesBase, table = True):
    image_id: int = Field(default=None, primary_key=True)
    created_at: datetime = Field(default=datetime.now())
    created_by: int = Field(foreign_key="user.id")