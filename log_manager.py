import logging
from datetime import datetime
from typing import Optional
from database import get_db_cursor

class LogManager:
    def __init__(self):
        pass
    
    def log_action(
        self,
        user_id: Optional[int],
        action: str,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO logs (user_id, action, details, ip_address, user_agent)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (user_id, action, details, ip_address, user_agent)
                )
        except Exception as e:
            print(f"记录日志失败: {e}")
    
    def log_user_login(self, user_id: int, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
        self.log_action(
            user_id=user_id,
            action="login",
            details="用户登录",
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_user_logout(self, user_id: int, ip_address: Optional[str] = None):
        self.log_action(
            user_id=user_id,
            action="logout",
            details="用户登出",
            ip_address=ip_address
        )
    
    def log_grading_start(
        self,
        user_id: int,
        directory_name: str,
        file_count: int,
        model_used: str,
        ip_address: Optional[str] = None
    ):
        self.log_action(
            user_id=user_id,
            action="annotate",
            details=f"开始批阅目录: {directory_name}, 文件数: {file_count}, 模型: {model_used}",
            ip_address=ip_address
        )
    
    def log_grading_complete(
        self,
        user_id: int,
        directory_name: str,
        qualified_count: int,
        unqualified_count: int,
        ip_address: Optional[str] = None
    ):
        self.log_action(
            user_id=user_id,
            action="annotate",
            details=f"批阅完成: {directory_name}, 合格: {qualified_count}, 不合格: {unqualified_count}",
            ip_address=ip_address
        )
    
    def log_criteria_update(
        self,
        user_id: int,
        ip_address: Optional[str] = None
    ):
        self.log_action(
            user_id=user_id,
            action="annotate",
            details="更新批阅标准",
            ip_address=ip_address
        )
    
    def log_file_upload(
        self,
        user_id: int,
        file_count: int,
        ip_address: Optional[str] = None
    ):
        self.log_action(
            user_id=user_id,
            action="upload",
            details=f"上传文件: {file_count}个",
            ip_address=ip_address
        )
    
    def log_file_download(
        self,
        user_id: int,
        file_name: str,
        ip_address: Optional[str] = None
    ):
        self.log_action(
            user_id=user_id,
            action="download",
            details=f"下载文件: {file_name}",
            ip_address=ip_address
        )
    
    def get_user_logs(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0
    ):
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, user_id, action, details, ip_address, created_at
                    FROM logs
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, limit, offset)
                )
                return cursor.fetchall()
        except Exception as e:
            print(f"获取用户日志失败: {e}")
            return []
    
    def get_logs(
        self,
        action: Optional[str] = None,
        user_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ):
        try:
            query = """
                SELECT id, user_id, action, details, ip_address, created_at
                FROM logs
                WHERE 1=1
            """
            params = []
            
            if action:
                query += " AND action = %s"
                params.append(action)
            
            if user_id:
                query += " AND user_id = %s"
                params.append(user_id)
                
            if start_date:
                query += " AND created_at >= %s"
                params.append(start_date)
                
            if end_date:
                query += " AND created_at <= %s"
                params.append(end_date)
                
            query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            with get_db_cursor() as cursor:
                cursor.execute(query, tuple(params))
                return cursor.fetchall()
        except Exception as e:
            print(f"获取日志失败: {e}")
            return []


log_manager = LogManager()
