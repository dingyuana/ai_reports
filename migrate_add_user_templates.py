#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_cursor

def migrate_add_user_templates():
    """添加用户模板表"""
    try:
        with get_db_cursor() as cursor:
            print("开始创建用户模板表...")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_templates (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    criteria TEXT NOT NULL,
                    min_score INTEGER DEFAULT 60,
                    max_score INTEGER DEFAULT 95,
                    is_default BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, name)
                )
            """)
            print("✓ 用户模板表创建成功")
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_templates_user_id 
                ON user_templates(user_id)
            """)
            print("✓ 索引创建成功")
            
            cursor.execute("""
                CREATE TRIGGER update_user_templates_updated_at 
                BEFORE UPDATE ON user_templates
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
            """)
            print("✓ 触发器创建成功")
            
        print("\n" + "=" * 60)
        print("✓ 用户模板表迁移完成！")
        print("=" * 60)
        return True
    except Exception as e:
        print(f"✗ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("开始数据库迁移...")
    if migrate_add_user_templates():
        print("迁移完成！")
    else:
        print("迁移失败！")
        sys.exit(1)
