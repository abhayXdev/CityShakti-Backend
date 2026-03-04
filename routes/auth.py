from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models import User
from rate_limiter import limiter
from schemas import (RefreshTokenRequest, TokenResponse, UserLogin, UserOut,
                     UserRegister)
from security import (create_access_token, create_refresh_token, decode_token,
                      hash_password, verify_password)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, payload: UserRegister, db: Session = Depends(get_db)):
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
