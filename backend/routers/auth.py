from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
from auth.jwt_handler import get_password_hash, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register_user(user_in: schemas.UserRegister, db: Session = Depends(get_db)):
    """
    Registers a new user supporting both 'CLIENT' and 'LAWYER' roles.
    Bcrypt hashes the password and ensures email uniqueness.
    """
    # 1. Check existing email
    existing_user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists"
        )

    # 2. Hash password & create user
    hashed_pw = get_password_hash(user_in.password)
    db_user = models.User(
        email=user_in.email,
        password_hash=hashed_pw,
        full_name=user_in.full_name,
        role=user_in.role,
        phone=user_in.phone
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login", response_model=schemas.Token)
async def login_user(request: Request, db: Session = Depends(get_db)):
    """
    Authenticates user and returns JWT bearer token.
    Supports both JSON payloads ({"email": "...", "password": "..."})
    and OAuth2 form data (username=...&password=...) for Swagger UI /docs.
    Supports both 'CLIENT' and 'LAWYER' roles.
    """
    content_type = request.headers.get("content-type", "")
    username = None
    password = None

    if "application/json" in content_type:
        body = await request.json()
        username = body.get("email") or body.get("username")
        password = body.get("password")
    else:
        form = await request.form()
        username = form.get("username") or form.get("email")
        password = form.get("password")

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email/username and password are required"
        )

    # Authenticate credentials
    user = db.query(models.User).filter(models.User.email == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        data={"sub": user.email, "user_id": user.user_id, "role": user.role.value}
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role.value,
        "user_id": user.user_id,
        "email": user.email
    }

@router.get("/me", response_model=schemas.UserOut)
def get_current_user_profile(current_user: models.User = Depends(get_current_user)):
    """
    Returns profile of currently authenticated user using JWT bearer token.
    Rejects unauthenticated requests with HTTP 401.
    """
    return current_user
