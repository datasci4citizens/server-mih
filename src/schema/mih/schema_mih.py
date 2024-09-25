from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from sqlmodel import SQLModel, Field
from typing import Optional



""" USER TABLES """

class UserBase(SQLModel):
    name: str
    email: str
    phone_number: str
    accept_tcle: bool

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: int

class UserUpdate(SQLModel):
    name: Optional[str] = None
    email: Optional[str] = None







""" SPECIALISTS TABLES """
class SpecialistsBase(SQLModel):
    email: str
    name: str
    phone_number: str
    is_allowed: bool

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

    tracking_records: list["TrackingRecords"] = Relationship(back_populates="specialist")

""" PATIENTS TABLES """
class PatientsBase(SQLModel):
    name: str
    birthday: datetime | None = None
    observations: str | None = None
    

class PatientsCreate(PatientsBase):
    pass

class PatientsUpdate(SQLModel):
    name: str | None = None
    birthday: datetime | None = None
    observations: str | None = None

class PatientsPublic(PatientsBase):
    patient_id: int
    created_at: datetime
    updated_at: datetime

class Patients(PatientsBase, table=True):
    patient_id: int = Field(default=None, primary_key=True)
    created_at: datetime
    updated_at: datetime

    mih: list["Mih"] = Relationship(back_populates="patient")
    tracking_records: list["TrackingRecords"] = Relationship(back_populates="patient")



""" Mih TABLES """
""" no tutorial do sqlmodel, mih é o hero e patient e mih_type é o team"""
class MihBase(SQLModel):
    mih_location: str
    start_date: datetime
    end_date: datetime | None = None
    patient_id: int = Field(foreign_key="patients.patient_id")

class MihCreate(MihBase):
    pass

class MihUpdate(SQLModel):
    # mih_location: str | None = None # acho que não deveria da pra mudar a localização da ferida
    # start_date: datetime | None = None
    end_date: datetime | None = None
    # mih_type_id: int | None = None

class MihPublic(MihBase):
    mih_id: int

class Mih(MihBase, table = True):
    mih_id: int = Field(default=None, primary_key=True)
    created_at: datetime
    updated_at: datetime
    patient: Patients = Relationship(back_populates="mih")

    tracking_records: list["TrackingRecords"] = Relationship(back_populates="mih")

""" TRACKING RECORDS TABLES"""
class TrackingRecordsBase(SQLModel):
    image_id: int
    observations: str | None = None
    patient_id: int = Field(foreign_key="patients.patient_id")
    mih_id: int = Field(foreign_key="mih.mih_id")
    specialist_id: int = Field(foreign_key="specialists.specialist_id")

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
    patient: Patients = Relationship(back_populates="tracking_records")
    mih: Mih = Relationship(back_populates="tracking_records")
    specialist: Specialists = Relationship(back_populates="tracking_records")

""" DATA MODELS FOR RELATIONSHIPS """
class PatientsPublicWithMih(PatientsPublic):
    mih: list[MihPublic] = []

class MihPublicWithPatient(MihPublic):
    patient: PatientsPublic | None = None

class MihPublicWithTrackingRecords(MihPublic):
    tracking_records: list[TrackingRecordsPublic] = []

class SpecialistsPublicWithTrackingRecords(SpecialistsPublic):
    pass
