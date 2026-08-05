from pydantic import BaseModel, EmailStr

class RegisterRequest(BaseModel):
    tenant_name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: str
    tenant_id: str
    email: str
    role: str
