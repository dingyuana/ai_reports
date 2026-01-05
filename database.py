import psycopg2
from psycopg2 import pool
from psycopg2 import errors
import os
from contextlib import contextmanager

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://ai_report_user:ai_report_password@localhost:5432/ai_report_db"
)

connection_pool = None

def init_db_pool():
    global connection_pool
    try:
        connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=DATABASE_URL
        )
        print("数据库连接池初始化成功")
    except Exception as e:
        print(f"数据库连接池初始化失败: {e}")
        raise

def init_database():
    """初始化数据库表结构"""
    try:
        sql_file_path = os.path.join(os.path.dirname(__file__), "database", "init.sql")
        if os.path.exists(sql_file_path):
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    cursor.execute(sql_script)
                    conn.commit()
                    print("数据库表结构初始化成功")
                except errors.InsufficientPrivilege as e:
                    print(f"表已存在，跳过创建: {e}")
                    conn.rollback()
                    
                    try:
                        cursor.execute("SELECT 1 FROM users WHERE username = 'admin'")
                        admin_exists = cursor.fetchone()
                        
                        if not admin_exists:
                            hashed_password = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzW5W5W5W5'
                            cursor.execute(
                                "INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)",
                                ('admin', hashed_password, 'admin@example.com', 'super_admin')
                            )
                            conn.commit()
                            print("默认管理员账户创建成功")
                        else:
                            print("默认管理员账户已存在")
                    except Exception as insert_error:
                        print(f"创建默认管理员账户失败: {insert_error}")
                        conn.rollback()
                
                cursor.close()
        else:
            print(f"SQL文件不存在: {sql_file_path}")
    except Exception as e:
        print(f"数据库表结构初始化失败: {e}")
        raise

@contextmanager
def get_db_connection():
    if connection_pool is None:
        init_db_pool()
    
    conn = None
    try:
        conn = connection_pool.getconn()
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            connection_pool.putconn(conn)

@contextmanager
def get_db_cursor():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()

def close_db_pool():
    global connection_pool
    if connection_pool:
        connection_pool.closeall()
        connection_pool = None
        print("数据库连接池已关闭")
