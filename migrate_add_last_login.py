#!/usr/bin/env python3
"""
数据库迁移脚本：添加 last_login 列到 users 表
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_cursor

def migrate_add_last_login():
    """添加 last_login 列到 users 表"""
    try:
        with get_db_cursor() as cursor:
            # 检查列是否已存在
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'last_login'
            """)
            if cursor.fetchone():
                print("✓ last_login 列已存在，无需迁移")
                return True
            
            # 添加 last_login 列
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN last_login TIMESTAMP
            """)
            print("✓ 成功添加 last_login 列到 users 表")
            return True
    except Exception as e:
        print(f"✗ 迁移失败: {e}")
        return False

if __name__ == "__main__":
    print("开始数据库迁移...")
    if migrate_add_last_login():
        print("迁移完成！")
    else:
        print("迁移失败！")
        sys.exit(1)
