from fastapi import FastAPI

from db.manager import Database
from api.common.users_api import router
from api.mih.mih_specialist_api import mih_specialist_router
from api.mih.mih_patients_api import mih_patients_router
from api.mih.mih_api import mih_router
from api.mih.mih_tracking_records_api import mih_tracking_records_router
#from api.medications.medication_users import medications_user_router

Database.db_engine()

app = FastAPI()

app.include_router(router)
app.include_router(mih_specialist_router)
app.include_router(mih_patients_router)
app.include_router(mih_router)
app.include_router(mih_tracking_records_router)
#app.include_router(medications_user_router)
