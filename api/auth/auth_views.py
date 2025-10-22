from fastapi import APIRouter, Depends

from starlette import status

from api.auth.auth_response_models import (
    SignUpRequest, 
    SignUpResponse,
    SignInRequest,
    SignInResponse
)

from api.auth.auth_service import (
    sign_up_user_service,
    sign_in_user_service,
)

auth_router = APIRouter(
    prefix="/auth",
    tags=["Authentications"]
)

@auth_router.post("/sign_in", status_code=status.HTTP_200_OK)
def sign_in_user(user: SignInRequest) -> SignInResponse:
    return sign_in_user_service(
        username = user.username,
        password = user.password
    )

@auth_router.post("/sign_up", status_code=status.HTTP_201_CREATED)
def sign_up_user(user: SignUpRequest) -> SignUpResponse:
    return sign_up_user_service(
        user_info = user,
    )


