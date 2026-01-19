# 认证相关的API端点
from fastapi import APIRouter, HTTPException, status, Form, Request, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import timedelta, datetime
import os
import logging

from user_manager import user_manager
from database import get_db_cursor

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/auth", tags=["authentication"])

# JWT配置
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2密码流
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# 认证相关的Pydantic模型
class UserLogin(BaseModel):
    username: str
    password: str


class UserRegister(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    role: str


# 工具函数
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = user_manager.get_user_by_username(username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not current_user.get("is_active", True):
        raise HTTPException(status_code=400, detail="用户账户已停用")
    return current_user


async def get_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    if not user_manager.is_admin(current_user["id"]):
        raise HTTPException(status_code=403, detail="权限不足")
    return current_user


async def get_super_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    if not user_manager.is_super_admin(current_user["id"]):
        raise HTTPException(status_code=403, detail="需要超级管理员权限")
    return current_user


async def get_regular_user(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    if current_user["role"] != "user":
        raise HTTPException(status_code=403, detail="只有普通用户可以使用系统功能")
    return current_user


# 认证相关的API端点
@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegister):
    """用户注册"""
    existing_user = user_manager.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user_id = user_manager.create_user(
        username=user_data.username,
        password=user_data.password,
        email=user_data.email,
        role="user",
    )

    if user_id is None:
        raise HTTPException(status_code=500, detail="注册失败")

    user = user_manager.get_user_by_id(user_id)
    return UserResponse(**user)


@router.post("/login", response_model=Token)
async def login(username: str = Form(...), password: str = Form(...)):
    """用户登录"""
    user = user_manager.authenticate_user(username=username, password=password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer", user=user)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Dict[str, Any] = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return UserResponse(**current_user)
