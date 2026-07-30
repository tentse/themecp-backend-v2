from pydantic import BaseModel, EmailStr

class Credentials(BaseModel):
    email: EmailStr

class AuthResponseModel(BaseModel):
    token: str