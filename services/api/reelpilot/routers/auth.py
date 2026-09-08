from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from reelpilot.config import Settings, get_settings
from reelpilot.database import get_db
from reelpilot.limits import enforce_api_limit, enforce_auth_limit
from reelpilot.models import User, Workspace
from reelpilot.schemas.auth import AuthResponse, LoginRequest, SignUpRequest, UserResponse
from reelpilot.security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/v1/auth", tags=["authentication"])


def user_response(user: User) -> UserResponse:
    assert user.workspace is not None
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        workspace_id=user.workspace.id,
        workspace_name=user.workspace.name,
        created_at=user.created_at,
    )


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(
    request: SignUpRequest,
    database: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[None, Depends(enforce_auth_limit)],
) -> AuthResponse:
    email = str(request.email).lower()
    if database.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    workspace = Workspace(name=request.workspace_name)
    user = User(email=email, password_hash=hash_password(request.password), display_name=request.display_name)
    user.workspace = workspace
    database.add(user)
    database.commit()
    database.refresh(user)
    return AuthResponse(access_token=create_access_token(user, settings), user=user_response(user))


@router.post("/login", response_model=AuthResponse)
def login(
    request: LoginRequest,
    database: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[None, Depends(enforce_auth_limit)],
) -> AuthResponse:
    user = database.scalar(select(User).where(User.email == str(request.email).lower()))
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return AuthResponse(access_token=create_access_token(user, settings), user=user_response(user))


@router.get("/me", response_model=UserResponse, dependencies=[Depends(enforce_api_limit)])
def me(user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return user_response(user)
