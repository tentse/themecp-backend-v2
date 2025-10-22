from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from starlette import status

from api.user.user_service import (
    get_user_info,
    update_codeforces_handle_service
)
from api.user.user_response_models import (
    UserInfoResponse
)

user_router = APIRouter(
    prefix="/users",
    tags=["Users Profile"]
)

@user_router.get("/info", status_code=status.HTTP_200_OK)
def get_user_information(
    authentication_credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> UserInfoResponse:
    return get_user_info(token=authentication_credentials.credentials)

@user_router.put("/codeforce_handle", status_code=status.HTTP_201_CREATED)
def update_codeforces_handle(codeforces_handle: str, authentication_credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> bool:
    return update_codeforces_handle_service(
        codeforces_handle = codeforces_handle,
        token = authentication_credentials.credentials
    )