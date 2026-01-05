#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:8000"

def test_admin_login():
    print("=" * 60)
    print("测试管理员登录和后台管理功能")
    print("=" * 60)
    
    # 测试登录
    print("\n[步骤1] 测试管理员登录...")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            data=login_data
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ 登录成功")
            print(f"  - 用户名: {data['user']['username']}")
            print(f"  - 角色: {data['user']['role']}")
            print(f"  - Token: {data['access_token'][:50]}...")
            
            token = data['access_token']
            
            # 测试访问后台管理API
            print("\n[步骤2] 测试访问后台管理API...")
            
            headers = {
                "Authorization": f"Bearer {token}"
            }
            
            # 测试概览统计
            print("  - 测试概览统计...")
            response = requests.get(
                f"{BASE_URL}/api/admin/stats/overview",
                headers=headers
            )
            
            if response.status_code == 200:
                stats = response.json()
                print(f"    ✓ 成功获取统计数据")
                print(f"      总用户数: {stats.get('total_users', 0)}")
                print(f"      今日活跃用户: {stats.get('active_users_today', 0)}")
                print(f"      今日日志: {stats.get('today_logs', 0)}")
                print(f"      总日志数: {stats.get('total_logs', 0)}")
            else:
                print(f"    ✗ 获取统计数据失败: {response.status_code}")
                print(f"      响应: {response.text}")
                return False
            
            # 测试用户活动统计
            print("  - 测试用户活动统计...")
            response = requests.get(
                f"{BASE_URL}/api/admin/stats/user-activity?days=30",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"    ✓ 成功获取用户活动数据")
                print(f"      数据点数量: {len(data)}")
            else:
                print(f"    ✗ 获取用户活动数据失败: {response.status_code}")
                print(f"      响应: {response.text}")
                return False
            
            # 测试操作分布统计
            print("  - 测试操作分布统计...")
            response = requests.get(
                f"{BASE_URL}/api/admin/stats/action-distribution",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"    ✓ 成功获取操作分布数据")
                print(f"      操作类型数量: {len(data)}")
            else:
                print(f"    ✗ 获取操作分布数据失败: {response.status_code}")
                print(f"      响应: {response.text}")
                return False
            
            # 测试访问后台管理页面
            print("\n[步骤3] 测试访问后台管理页面...")
            
            # 测试 admin_dashboard.html
            response = requests.get(f"{BASE_URL}/admin_dashboard.html")
            if response.status_code == 200:
                print(f"  ✓ 成功访问 admin_dashboard.html")
            else:
                print(f"  ✗ 访问 admin_dashboard.html 失败: {response.status_code}")
                return False
            
            # 测试 admin.css
            response = requests.get(f"{BASE_URL}/admin.css")
            if response.status_code == 200:
                print(f"  ✓ 成功访问 admin.css")
            else:
                print(f"  ✗ 访问 admin.css 失败: {response.status_code}")
                return False
            
            # 测试 admin_dashboard.js
            response = requests.get(f"{BASE_URL}/admin_dashboard.js")
            if response.status_code == 200:
                print(f"  ✓ 成功访问 admin_dashboard.js")
            else:
                print(f"  ✗ 访问 admin_dashboard.js 失败: {response.status_code}")
                return False
            
            print("\n" + "=" * 60)
            print("✓ 所有测试通过！管理员登录和后台管理功能正常")
            print("=" * 60)
            return True
            
        else:
            print(f"  ✗ 登录失败: {response.status_code}")
            print(f"    响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_admin_login()
    exit(0 if success else 1)