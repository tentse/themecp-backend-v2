from pydantic import BaseModel

class SignUpRequest(BaseModel):
    username: str
    password: str

class SignUpResponse(BaseModel):
    user_id: str
    username: str
    access_token: str