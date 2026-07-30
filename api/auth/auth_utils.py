from jose import JWTError, jwt
from fastapi import HTTPException
from api.config import get
from api.error_constants import ErrorConstants

class AuthUtils:

    @staticmethod
    def verify_token(token: str) -> str:
        """Verify and decode JWT token"""
        
        try:
            SECRET_KEY = get("SECRET_KEY")
            ALGORITHM = get("ALGORITHM")
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("email")
            
            if email is None:
                raise HTTPException(status_code=401, detail=ErrorConstants.INVALID_TOKEN)
            
            return email
        
        except JWTError:
            raise HTTPException(status_code=401, detail=ErrorConstants.INVALID_TOKEN)