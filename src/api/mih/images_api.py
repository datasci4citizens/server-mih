from auth.auth_service import AuthService
from db.manager import Database
from fastapi import APIRouter, Depends, Request
from images.images import Images
from pydantic import BaseModel
from schema.mih.schema_mih import(
    Images as ImagesSchema,
    ImagesCreate,
) # Seus modelos


from sqlmodel import Session

class ImageUploadResponse(BaseModel):
    image_id: int
    upload_url: str


images_router = APIRouter(dependencies=[Depends(AuthService.get_current_user)])
BASE_URL_IMAGES = "/images/"


@images_router.post(BASE_URL_IMAGES, response_model=ImageUploadResponse)
def create_image(
    *,
    request: Request,
    session: Session = Depends(Database.get_session),
    images: Images = Depends(Images.instance),
    image: ImagesCreate,
):
    """Create a new image"""
    # TODO: SUBSTITUIR CREATED BY PELO ID DO USUARIO
    db_img = ImagesSchema.model_validate(image, update={"user_id": request.session.get("id")})
    session.add(db_img)
    session.commit()
    session.refresh(db_img)

    url = images.get_upload_url(db_img.image_id, db_img.extension)
    return ImageUploadResponse(image_id=db_img.image_id, upload_url=url)
