import bcrypt
from typing import Optional, Dict, Any
from database import get_db_cursor
from log_manager import log_manager

class UserManager:
    def __init__(self):
        pass
    
    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def create_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        role: str = 'user'
    ) -> Optional[int]:
        try:
            hashed_password = self.hash_password(password)
            from database import get_db_connection
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO users (username, password, email, role)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (username, hashed_password, email, role)
                )
                user_id = cursor.fetchone()[0]
                conn.commit()
                cursor.close()
            
            log_manager.log_action(
                user_id=user_id,
                action="create_user",
                details=f"创建用户: {username}, 角色: {role}"
            )
            return user_id
        except Exception as e:
            print(f"创建用户失败: {e}")
            return None
    
    def authenticate_user(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, username, password, email, role, is_active
                    FROM users
                    WHERE username = %s
                    """,
                    (username,)
                )
                user = cursor.fetchone()
                
                if not user:
                    return None
                
                user_id, db_username, db_password, email, role, is_active = user
                
                if not is_active:
                    return None
                
                if not self.verify_password(password, db_password):
                    return None
                
                log_manager.log_user_login(
                    user_id=user_id,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                return {
                    'id': user_id,
                    'username': db_username,
                    'email': email,
                    'role': role
                }
        except Exception as e:
            print(f"用户认证失败: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, username, email, role, is_active, created_at
                    FROM users
                    WHERE id = %s
                    """,
                    (user_id,)
                )
                user = cursor.fetchone()
                
                if not user:
                    return None
                
                return {
                    'id': user[0],
                    'username': user[1],
                    'email': user[2],
                    'role': user[3],
                    'is_active': user[4],
                    'created_at': user[5]
                }
        except Exception as e:
            print(f"获取用户信息失败: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, username, email, role, is_active, created_at
                    FROM users
                    WHERE username = %s
                    """,
                    (username,)
                )
                user = cursor.fetchone()
                
                if not user:
                    return None
                
                return {
                    'id': user[0],
                    'username': user[1],
                    'email': user[2],
                    'role': user[3],
                    'is_active': user[4],
                    'created_at': user[5]
                }
        except Exception as e:
            print(f"获取用户信息失败: {e}")
            return None
    
    def update_user_role(self, user_id: int, new_role: str) -> bool:
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users
                    SET role = %s
                    WHERE id = %s
                    """,
                    (new_role, user_id)
                )
                log_manager.log_action(
                    user_id=user_id,
                    action="update_user",
                    details=f"更新用户角色为: {new_role}"
                )
                return True
        except Exception as e:
            print(f"更新用户角色失败: {e}")
            return False
    
    def deactivate_user(self, user_id: int) -> bool:
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users
                    SET is_active = FALSE
                    WHERE id = %s
                    """,
                    (user_id,)
                )
                log_manager.log_action(
                    user_id=user_id,
                    action="delete",
                    details="停用用户账户"
                )
                return True
        except Exception as e:
            print(f"停用用户失败: {e}")
            return False
    
    def activate_user(self, user_id: int) -> bool:
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users
                    SET is_active = TRUE
                    WHERE id = %s
                    """,
                    (user_id,)
                )
                log_manager.log_action(
                    user_id=user_id,
                    action="update_user",
                    details="激活用户账户"
                )
                return True
        except Exception as e:
            print(f"激活用户失败: {e}")
            return False
    
    def get_all_users(self) -> list:
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, username, email, role, is_active, created_at
                    FROM users
                    ORDER BY created_at DESC
                    """
                )
                users = cursor.fetchall()
                return [
                    {
                        'id': user[0],
                        'username': user[1],
                        'email': user[2],
                        'role': user[3],
                        'is_active': user[4],
                        'created_at': user[5]
                    }
                    for user in users
                ]
        except Exception as e:
            print(f"获取所有用户失败: {e}")
            return []
    
    def is_admin(self, user_id: int) -> bool:
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        return user['role'] in ['admin', 'super_admin']
    
    def is_super_admin(self, user_id: int) -> bool:
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        return user['role'] == 'super_admin'
    
    def update_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        email: Optional[str] = None,
        role: Optional[str] = None,
        password: Optional[str] = None
    ) -> bool:
        try:
            updates = []
            params = []
            
            if username:
                updates.append("username = %s")
                params.append(username)
            
            if email is not None:
                updates.append("email = %s")
                params.append(email)
            
            if role:
                updates.append("role = %s")
                params.append(role)
            
            if password:
                hashed_password = self.hash_password(password)
                updates.append("password = %s")
                params.append(hashed_password)
            
            if not updates:
                return False
            
            params.append(user_id)
            
            with get_db_cursor() as cursor:
                cursor.execute(
                    f"""
                    UPDATE users
                    SET {', '.join(updates)}
                    WHERE id = %s
                    """,
                    params
                )
                log_manager.log_action(
                    user_id=user_id,
                    action="update_user",
                    details=f"更新用户信息: {', '.join(updates)}"
                )
                return True
        except Exception as e:
            print(f"更新用户失败: {e}")
            return False
    
    def delete_user(self, user_id: int) -> bool:
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM users
                    WHERE id = %s
                    """,
                    (user_id,)
                )
                log_manager.log_action(
                    user_id=user_id,
                    action="delete_user",
                    details=f"删除用户ID: {user_id}"
                )
                return True
        except Exception as e:
            print(f"删除用户失败: {e}")
            return False

user_manager = UserManager()
