from typing import List  # Adicione esta linha para corrigir o erro
from sqlalchemy.orm import relationship  # Importação correta do SQLAlchemy
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from sqlmodel import SQLModel, Field
from typing import Optional



""" USER TABLES """

class UserBase(SQLModel):
    personInCharge: Optional[str] = None  # Permite nulo
    city: Optional[str] = None  # Permite nulo
    state: Optional[str] = None  # Permite nulo
    neighborhood: Optional[str] = None  # Permite nulo
    phone_number: Optional[str] = None  # Permite nulo
    accept_tcle: Optional[bool] = None  # Permite nulo

class UserCreate(UserBase):
    pass
class UserRead(UserBase):
    id: int

class UserUpdate(SQLModel):
    city: Optional[str] = None  # Permite nulo
    state: Optional[str] = None  # Permite nulo
    neighborhood: Optional[str] = None  # Permite nulo

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # Relacionamento com a tabela Patients
    patients: List["Patients"] = Relationship(back_populates="user", cascade_delete=True)








""" SPECIALISTS TABLES """
class SpecialistsBase(SQLModel):
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
    updated_at: datetime


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

class SpecialistsPublicWithTrackingRecords(SpecialistsPublic):
    pass
