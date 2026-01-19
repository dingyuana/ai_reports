# 管理员相关的API端点
from fastapi import APIRouter, HTTPException, status, Request, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

from user_manager import user_manager
from log_manager import log_manager
from database import get_db_cursor
from api.auth.endpoints import get_admin_user, get_super_admin_user

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
async def admin_get_users(current_user: Dict[str, Any] = Depends(get_admin_user)):
    """获取所有用户列表（管理员）"""
    users = user_manager.get_all_users()
    return users


@router.post("/users")
async def admin_create_user(
    user_data: dict, current_user: Dict[str, Any] = Depends(get_admin_user)
):
    """创建新用户（管理员）"""
    username = user_data.get("username")
    password = user_data.get("password")
    email = user_data.get("email")
    role = user_data.get("role", "user")

    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    if role not in ["user", "admin", "super_admin"]:
        raise HTTPException(status_code=400, detail="无效的角色")

    existing_user = user_manager.get_user_by_username(username)
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user_id = user_manager.create_user(
        username=username, password=password, email=email, role=role
    )

    if user_id is None:
        raise HTTPException(status_code=500, detail="创建用户失败")

    user = user_manager.get_user_by_id(user_id)
    return user


@router.put("/users/{user_id}")
async def admin_update_user(
    user_id: int,
    user_data: dict,
    current_user: Dict[str, Any] = Depends(get_admin_user)
):
    """更新用户信息（管理员）"""
    username = user_data.get("username")
    email = user_data.get("email")
    role = user_data.get("role")
    password = user_data.get("password")

    user = user_manager.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if role and role not in ["user", "admin", "super_admin"]:
        raise HTTPException(status_code=400, detail="无效的角色")

    if role and current_user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="只有超级管理员可以修改角色")

    success = user_manager.update_user(
        user_id=user_id, username=username, email=email, role=role, password=password
    )

    if not success:
        raise HTTPException(status_code=500, detail="更新用户失败")

    updated_user = user_manager.get_user_by_id(user_id)
    return updated_user


@router.delete("/users/{user_id}")
async def admin_delete_user(
    user_id: int, current_user: Dict[str, Any] = Depends(get_admin_user)
):
    """删除用户（管理员）"""
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="不能删除自己")

    user = user_manager.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user["role"] == "super_admin" and current_user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="不能删除超级管理员")

    success = user_manager.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除用户失败")

    return {"message": "用户删除成功"}


@router.get("/logs")
async def admin_get_logs(
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    date: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: Dict[str, Any] = Depends(get_admin_user),
):
    """获取日志列表（管理员，支持筛选和分页）"""
    offset = (page - 1) * page_size

    try:
        with get_db_cursor() as cursor:
            query = """
                SELECT l.id, l.user_id, l.action, l.details, l.ip_address, l.created_at, u.username
                FROM logs l
                LEFT JOIN users u ON l.user_id = u.id
                WHERE 1=1
            """
            params = []

            if action:
                query += " AND l.action = %s"
                params.append(action)

            if user_id:
                query += " AND l.user_id = %s"
                params.append(user_id)

            if date:
                query += " AND DATE(l.created_at) = %s"
                params.append(date)

            if search:
                query += " AND (l.details ILIKE %s OR u.username ILIKE %s)"
                params.extend([f"%{search}%", f"%{search}%"])

            query += " ORDER BY l.created_at DESC LIMIT %s OFFSET %s"
            params.extend([page_size, offset])

            cursor.execute(query, params)
            logs = cursor.fetchall()

            count_query = """
                SELECT COUNT(*)
                FROM logs l
                LEFT JOIN users u ON l.user_id = u.id
                WHERE 1=1
            """
            count_params = []

            if action:
                count_query += " AND l.action = %s"
                count_params.append(action)

            if user_id:
                count_query += " AND l.user_id = %s"
                count_params.append(user_id)

            if date:
                count_query += " AND DATE(l.created_at) = %s"
                count_params.append(date)

            if search:
                count_query += " AND (l.details ILIKE %s OR u.username ILIKE %s)"
                count_params.extend([f"%{search}%", f"%{search}%"])

            cursor.execute(count_query, count_params)
            total = cursor.fetchone()[0]

            log_list = []
            for log in logs:
                log_list.append(
                    {
                        "id": log[0],
                        "user_id": log[1],
                        "action": log[2],
                        "details": log[3],
                        "ip_address": log[4],
                        "created_at": log[5],
                        "username": log[6],
                    }
                )

            return {
                "logs": log_list,
                "total": total,
                "page": page,
                "page_size": page_size,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日志失败: {str(e)}")


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    new_role: str,
    current_user: Dict[str, Any] = Depends(get_super_admin_user),
):
    """更新用户角色（仅超级管理员）"""
    if new_role not in ["user", "admin", "super_admin"]:
        raise HTTPException(status_code=400, detail="无效的角色")

    success = user_manager.update_user_role(user_id, new_role)
    if not success:
        raise HTTPException(status_code=500, detail="更新用户角色失败")

    return {"message": "用户角色更新成功"}


@router.put("/users/{user_id}/activate")
async def activate_user(
    user_id: int, current_user: Dict[str, Any] = Depends(get_admin_user)
):
    """激活用户（仅管理员）"""
    success = user_manager.activate_user(user_id)
    if not success:
        raise HTTPException(status_code=500, detail="激活用户失败")

    return {"message": "用户激活成功"}


@router.put("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int, current_user: Dict[str, Any] = Depends(get_admin_user)
):
    """停用用户（仅管理员）"""
    success = user_manager.deactivate_user(user_id)
    if not success:
        raise HTTPException(status_code=500, detail="停用用户失败")

    return {"message": "用户停用成功"}
