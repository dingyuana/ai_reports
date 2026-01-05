import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from user_manager import user_manager
from log_manager import log_manager
from database import init_db_pool, init_database, get_db_cursor
from datetime import datetime, timedelta

async def test_admin_dashboard():
    """测试后台管理功能"""
    
    print("=" * 60)
    print("测试后台管理功能")
    print("=" * 60)
    
    try:
        init_db_pool()
        init_database()
        
        print("\n[步骤1] 创建测试管理员用户...")
        try:
            admin_username = "test_admin"
            admin_password = "admin123"
            
            existing_admin = user_manager.get_user_by_username(admin_username)
            if existing_admin:
                print(f"  管理员用户已存在: {admin_username}")
                admin_id = existing_admin['id']
            else:
                admin_id = user_manager.create_user(
                    username=admin_username,
                    password=admin_password,
                    email="admin@test.com",
                    role="admin"
                )
                print(f"  ✓ 管理员用户创建成功: {admin_username} (ID: {admin_id})")
        except Exception as e:
            print(f"  ✗ 创建管理员用户失败: {e}")
            return False
        
        print("\n[步骤2] 创建测试普通用户...")
        try:
            test_username = "test_user"
            test_password = "user123"
            
            existing_user = user_manager.get_user_by_username(test_username)
            if existing_user:
                print(f"  普通用户已存在: {test_username}")
                user_id = existing_user['id']
            else:
                user_id = user_manager.create_user(
                    username=test_username,
                    password=test_password,
                    email="user@test.com",
                    role="user"
                )
                print(f"  ✓ 普通用户创建成功: {test_username} (ID: {user_id})")
        except Exception as e:
            print(f"  ✗ 创建普通用户失败: {e}")
            return False
        
        print("\n[步骤3] 生成测试日志数据...")
        try:
            actions = ['login', 'logout', 'upload', 'download', 'grade', 'annotate']
            
            for i in range(50):
                action = actions[i % len(actions)]
                details = f"测试操作 {i+1}: {action}"
                
                log_manager.log_action(
                    user_id=user_id,
                    action=action,
                    details=details,
                    ip_address="127.0.0.1"
                )
            
            print(f"  ✓ 已生成50条测试日志")
        except Exception as e:
            print(f"  ✗ 生成测试日志失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\n[步骤4] 验证统计数据...")
        try:
            with get_db_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = true")
                total_users = cursor.fetchone()[0]
                print(f"  ✓ 总用户数: {total_users}")
                
                cursor.execute("SELECT COUNT(*) FROM logs WHERE created_at >= CURRENT_DATE")
                today_logs = cursor.fetchone()[0]
                print(f"  ✓ 今日日志数: {today_logs}")
                
                cursor.execute("SELECT COUNT(*) FROM logs")
                total_logs = cursor.fetchone()[0]
                print(f"  ✓ 总日志数: {total_logs}")
                
                cursor.execute("""
                    SELECT COUNT(DISTINCT user_id) FROM logs WHERE created_at >= CURRENT_DATE
                """)
                active_users_today = cursor.fetchone()[0]
                print(f"  ✓ 今日活跃用户: {active_users_today}")
        except Exception as e:
            print(f"  ✗ 验证统计数据失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\n[步骤5] 验证用户工作统计...")
        try:
            with get_db_cursor() as cursor:
                query = """
                    SELECT 
                        u.username,
                        COUNT(l.id) as total_actions,
                        COUNT(CASE WHEN l.action = 'upload' THEN 1 END) as upload_count,
                        COUNT(CASE WHEN l.action = 'download' THEN 1 END) as download_count,
                        COUNT(CASE WHEN l.action = 'grade' THEN 1 END) as grade_count
                    FROM users u
                    LEFT JOIN logs l ON u.id = l.user_id
                    WHERE u.is_active = true
                    GROUP BY u.id, u.username
                    ORDER BY total_actions DESC
                """
                cursor.execute(query)
                results = cursor.fetchall()
                
                print(f"  ✓ 用户工作统计:")
                for row in results:
                    username, total, upload, download, grade = row
                    print(f"    - {username}: 总操作={total}, 上传={upload}, 下载={download}, 批阅={grade}")
        except Exception as e:
            print(f"  ✗ 验证用户工作统计失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\n[步骤6] 验证操作分布统计...")
        try:
            with get_db_cursor() as cursor:
                query = """
                    SELECT 
                        action,
                        COUNT(*) as count
                    FROM logs
                    GROUP BY action
                    ORDER BY count DESC
                """
                cursor.execute(query)
                results = cursor.fetchall()
                
                print(f"  ✓ 操作分布统计:")
                for row in results:
                    action, count = row
                    print(f"    - {action}: {count}次")
        except Exception as e:
            print(f"  ✗ 验证操作分布统计失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        print("\n测试账户信息:")
        print(f"  管理员账户: {admin_username} / {admin_password}")
        print(f"  普通用户: {test_username} / {test_password}")
        print("\n访问后台管理页面:")
        print(f"  http://localhost:8000/admin_dashboard.html")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_admin_dashboard())
    sys.exit(0 if success else 1)