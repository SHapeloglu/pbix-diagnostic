import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import (
    get_password_hash, 
    verify_password, 
    create_access_token,
    generate_verification_token,
    get_verification_token_expiry
)
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse, ResendVerificationRequest
from app.api.deps import get_current_user
from app.utils.emails import send_email

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register new user with email verification"""
    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create tenant
    tenant = Tenant(id=str(uuid.uuid4()), name=req.tenant_name)
    db.add(tenant)
    await db.flush()
    
    # Generate verification token
    verification_token = generate_verification_token()
    verification_token_expires = get_verification_token_expiry()
    
    # Create user (NOT verified yet)
    user = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        email=req.email,
        password_hash=get_password_hash(req.password),
        role="admin",
        is_verified=False,
        verification_token=verification_token,
        verification_token_expires=verification_token_expires
    )
    db.add(user)
    await db.commit()
    
    # Send verification email
    verification_url = f"https://pbixdia.powerbi.com.tr/auth/verify-email?token={verification_token}"
    send_email(
        to_email=req.email,
        subject="Verify your email - pbix-diagnostic",
        template_name="verify_email",
        context={"verification_url": verification_url}
    )
    
    return {
        "status": "pending_verification",
        "message": f"Registration successful! Check your email ({req.email}) to verify your account.",
        "email": req.email
    }

@router.get("/verify-email", response_class=HTMLResponse)
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    """Verify user email via token link"""
    # Find user by verification token
    result = await db.execute(
        select(User).where(User.verification_token == token)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return """
        <html>
            <head><title>Verification Failed</title></head>
            <body style="font-family: Arial; text-align: center; margin-top: 50px;">
                <h2>❌ Verification Failed</h2>
                <p>Invalid verification token.</p>
                <p><a href="https://pbixdia.powerbi.com.tr">Back to Home</a></p>
            </body>
        </html>
        """
    
    # Check if token expired
    if user.verification_token_expires < datetime.utcnow():
        return """
        <html>
            <head><title>Verification Expired</title></head>
            <body style="font-family: Arial; text-align: center; margin-top: 50px;">
                <h2>⏰ Verification Link Expired</h2>
                <p>Your verification link has expired (24 hours).</p>
                <p><a href="https://pbixdia.powerbi.com.tr/auth/resend-verification">Request new verification link</a></p>
            </body>
        </html>
        """
    
    # Mark user as verified
    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    await db.commit()
    
    return f"""
    <html>
        <head><title>Email Verified</title></head>
        <body style="font-family: Arial; text-align: center; margin-top: 50px;">
            <h2>✅ Email Verified!</h2>
            <p>Your email has been successfully verified.</p>
            <p>You can now <a href="https://pbixdia.powerbi.com.tr">log in</a> to your account.</p>
        </body>
    </html>
    """

@router.post("/resend-verification")
async def resend_verification(req: ResendVerificationRequest, db: AsyncSession = Depends(get_db)):
    """Resend verification email if user is not yet verified"""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    # Aynı yanıtı hem var olan hem olmayan email için döneriz (email enumeration önlemi)
    generic_response = {
        "status": "ok",
        "message": "If an account with that email exists and is not yet verified, a new verification email has been sent."
    }

    if not user or user.is_verified:
        return generic_response

    # Yeni token üret
    user.verification_token = generate_verification_token()
    user.verification_token_expires = get_verification_token_expiry()
    await db.commit()

    verification_url = f"https://pbixdia.powerbi.com.tr/auth/verify-email?token={user.verification_token}"
    send_email(
        to_email=user.email,
        subject="Verify your email - pbix-diagnostic",
        template_name="verify_email",
        context={"verification_url": verification_url}
    )

    return generic_response

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login user (requires verified email)"""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if email is verified
    if not user.is_verified:
        raise HTTPException(
            status_code=403, 
            detail="Email not verified. Check your inbox for verification link."
        )
    
    user.last_login = datetime.utcnow()
    await db.commit()
    
    token = create_access_token({"sub": user.id, "tenant_id": user.tenant_id, "role": user.role})
    return TokenResponse(access_token=token)

@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return UserResponse(
        id=current_user.id, 
        tenant_id=current_user.tenant_id,
        email=current_user.email, 
        role=current_user.role
    )
