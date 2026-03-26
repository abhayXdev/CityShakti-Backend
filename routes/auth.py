"""
Authentication & Authorization API Routes.
Manages user registration, JWT lifecycle, role verification, and secure OTP flows.
"""
import random
import string
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models import EmailOTP, User
from rate_limiter import limiter
from schemas import (RefreshTokenRequest, TokenResponse, UserLogin, UserOut,
                     UserRegister)
from security import (create_access_token, create_refresh_token, decode_token,
                      hash_password, verify_password)
from services.notifications import send_otp_email

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, payload: UserRegister, db: Session = Depends(get_db)):
    """
    Registers a new Citizen or Officer.
    For Officers, it enforces PIN code logic and restricts creation to 
    1 administrative officer per department per ward.
    """
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    # Enforce Pincode uniqueness for Officers (1 per department per pincode)
    if payload.role == "officer":
        if not payload.ward:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="PIN Code is required for officers"
            )
        if not payload.department:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned Department is required for officers"
            )
        
        existing_admin = db.query(User).filter(
            User.role == "officer",
            User.ward == payload.ward,
            User.department == payload.department
        ).first()

        if existing_admin:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail=f"An officer for '{payload.department}' already exists in PIN code {payload.ward}."
            )

    user = User(
        full_name=payload.full_name,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        ward=payload.ward,
        department=payload.department,
        phone=payload.phone,
        is_active=False if payload.role == "officer" else True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, payload: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticates a user via email and password.
    Returns short-lived Access Tokens and long-lived Refresh Tokens.
    Blocks login if the account is suspended or awaiting Super Admin approval.
    """
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    if getattr(user, "is_suspended", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="your account has been suspended"
        )

    if not user.is_active:
        if user.role == "officer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Account pending Super Admin approval"
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled"
        )

    # Reject if the requested login role doesn't match the user's actual role
    if payload.role and payload.role != user.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This account is registered as '{user.role}'. Please use the correct login tab.",
        )

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id, user.role),
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
def refresh_token(
    request: Request, payload: RefreshTokenRequest, db: Session = Depends(get_db)
):
    claims = decode_token(payload.refresh_token)
    if claims.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    user_id = claims.get("sub")
    role = claims.get("role")
    if not user_id or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload",
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token user",
        )

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id, user.role),
    )


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


# ─────────────────────────────────────────────────────────
# EMAIL OTP ENDPOINTS
# ─────────────────────────────────────────────────────────

from pydantic import BaseModel, EmailStr, Field

class OTPRequest(BaseModel):
    email: EmailStr

class OTPVerify(BaseModel):
    email: EmailStr
    otp_code: str


@router.post("/send-email-otp", status_code=status.HTTP_200_OK)
@limiter.limit("3/minute")
def send_email_otp(request: Request, payload: OTPRequest, db: Session = Depends(get_db)):
    """
    Generates a secure 6-digit OTP, stores it with a 5-minute expiration,
    and dispatches it via the configured Email provider (e.g., Brevo API).
    Overrides any previous unverified OTP for the given email to prevent spam.
    """
    email = payload.email
    # Invalidate any previous unused OTPs for this email
    db.query(EmailOTP).filter(
        EmailOTP.email == email.lower(),
        EmailOTP.is_used == False,
    ).delete(synchronize_session=False)

    # Generate a fresh 6-digit code
    code = "".join(random.choices(string.digits, k=6))
    expires = datetime.now(timezone.utc) + timedelta(minutes=5)

    otp_record = EmailOTP(
        email=payload.email.lower(),
        otp_code=code,
        expires_at=expires,
    )
    db.add(otp_record)
    db.commit()

    # Send via Gmail SMTP
    send_otp_email(payload.email, code)

    return {"message": "OTP sent successfully. Valid for 5 minutes."}


@router.post("/verify-email-otp", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
def verify_email_otp(request: Request, payload: OTPVerify, db: Session = Depends(get_db)):
    """
    Validate the OTP code and mark it as used.
    Returns a one-time verification token that the frontend passes to /register.
    """
    record = db.query(EmailOTP).filter(
        EmailOTP.email == payload.email.lower(),
        EmailOTP.otp_code == payload.otp_code,
        EmailOTP.is_used == False,
    ).order_by(EmailOTP.created_at.desc()).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP code. Please try again.",
        )

    if datetime.now(timezone.utc) > record.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new one.",
        )

    # Mark as used so it can't be replayed
    record.is_used = True
    db.commit()

    return {"verified": True, "email": payload.email}


# ─────────────────────────────────────────────────────────
# FORGOT PASSWORD ENDPOINTS (works for both Citizens & Officers)
# ─────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp_code: str
    new_password: str = Field(min_length=8, max_length=128)


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
@limiter.limit("3/minute")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Sends a password-reset OTP to the registered email.
    Works for Citizens AND Officers.
    Always returns success (to prevent user enumeration attacks).
    """
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user and user.is_active:
        # Invalidate any previous OTPs for this email
        db.query(EmailOTP).filter(
            EmailOTP.email == payload.email.lower(),
            EmailOTP.is_used == False,
        ).delete(synchronize_session=False)

        code = "".join(random.choices(string.digits, k=6))
        expires = datetime.now(timezone.utc) + timedelta(minutes=10)
        otp_record = EmailOTP(
            email=payload.email.lower(),
            otp_code=code,
            expires_at=expires,
        )
        db.add(otp_record)
        db.commit()
        send_otp_email(payload.email, code)

    # Always return 200 to prevent email enumeration
    return {"message": "If that email is registered, an OTP has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
def reset_password(request: Request, payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Validates OTP and sets a new password for the account.
    """
    record = db.query(EmailOTP).filter(
        EmailOTP.email == payload.email.lower(),
        EmailOTP.otp_code == payload.otp_code,
        EmailOTP.is_used == False,
    ).order_by(EmailOTP.created_at.desc()).first()

    if not record or datetime.now(timezone.utc) > record.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP.",
        )

    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.password_hash = hash_password(payload.new_password)
    record.is_used = True
    db.commit()

    return {"message": "Password reset successfully. You may now log in."}
