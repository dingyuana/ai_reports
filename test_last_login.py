#!/usr/bin/env python3
"""
测试最后登录时间功能
"""

import sys
import os
import requests
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE_URL = "http://localhost:8000"

def test_last_login():
    """测试最后登录时间功能"""
    print("=" * 60)
    print("测试最后登录时间功能")
    print("=" * 60)
    
    # 1. 管理员登录
    print("\n[步骤1] 管理员登录...")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/login", data=login_data)
    if response.status_code != 200:
        print(f"✗ 管理员登录失败: {response.status_code}")
        print(response.text)
        return False
    
    admin_token = response.json()["access_token"]
    print("✓ 管理员登录成功")
    
    # 2. 获取所有用户信息（包含最后登录时间）
    print("\n[步骤2] 获取所有用户信息...")
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
    
    if response.status_code != 200:
        print(f"✗ 获取用户列表失败: {response.status_code}")
        print(response.text)
        return False
    
    users = response.json()
    print(f"✓ 成功获取 {len(users)} 个用户")
    
    # 3. 显示每个用户的最后登录时间
    print("\n[步骤3] 显示用户最后登录时间...")
    print("-" * 60)
    print(f"{'用户名':<20} {'邮箱':<30} {'最后登录时间':<25}")
    print("-" * 60)
    
    for user in users:
        username = user.get('username', 'N/A')
        email = user.get('email', 'N/A') or 'N/A'
        last_login = user.get('last_login', None)
        
        if last_login:
            from datetime import datetime
            login_time = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
            login_str = login_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            login_str = '从未登录'
        
        print(f"{username:<20} {email:<30} {login_str:<25}")
    
    print("-" * 60)
    
    # 4. 创建测试用户
    print("\n[步骤4] 创建测试用户...")
    import time
    timestamp = int(time.time())
    test_username = f"test_login_{timestamp}"
    test_email = f"test_login_{timestamp}@example.com"
    
    create_data = {
        "username": test_username,
        "password": "test123",
        "email": test_email,
        "role": "user"
    }
    
    response = requests.post(f"{BASE_URL}/api/admin/users", json=create_data, headers=headers)
    if response.status_code != 200:
        print(f"✗ 创建测试用户失败: {response.status_code}")
        print(response.text)
        return False
    
    test_user = response.json()
    test_user_id = test_user["id"]
    print(f"✓ 成功创建测试用户: {test_username} (ID: {test_user_id})")
    
    # 5. 检查新用户的最后登录时间（应该为空）
    print("\n[步骤5] 检查新用户的最后登录时间...")
    response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
    users = response.json()
    
    new_user = next((u for u in users if u['id'] == test_user_id), None)
    if new_user:
        last_login = new_user.get('last_login', None)
        if last_login:
            print(f"✗ 新用户的最后登录时间不应为空: {last_login}")
            return False
        else:
            print(f"✓ 新用户的最后登录时间为空（符合预期）")
    else:
        print("✗ 未找到新创建的用户")
        return False
    
    # 6. 测试用户登录
    print("\n[步骤6] 测试用户登录...")
    login_data = {
        "username": test_username,
        "password": "test123"
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/login", data=login_data)
    if response.status_code != 200:
        print(f"✗ 测试用户登录失败: {response.status_code}")
        print(response.text)
        return False
    
    test_token = response.json()["access_token"]
    print("✓ 测试用户登录成功")
    
    # 7. 检查登录后的最后登录时间
    print("\n[步骤7] 检查登录后的最后登录时间...")
    response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
    users = response.json()
    
    new_user = next((u for u in users if u['id'] == test_user_id), None)
    if new_user:
        last_login = new_user.get('last_login', None)
        if last_login:
            from datetime import datetime
            login_time = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
            login_str = login_time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"✓ 最后登录时间已更新: {login_str}")
        else:
            print("✗ 最后登录时间未更新")
            return False
    else:
        print("✗ 未找到测试用户")
        return False
    
    # 8. 再次登录，验证时间更新
    print("\n[步骤8] 再次登录，验证时间更新...")
    import time
    time.sleep(2)
    
    response = requests.post(f"{BASE_URL}/api/auth/login", data=login_data)
    if response.status_code != 200:
        print(f"✗ 测试用户再次登录失败: {response.status_code}")
        return False
    
    response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
    users = response.json()
    
    new_user = next((u for u in users if u['id'] == test_user_id), None)
    if new_user:
        last_login = new_user.get('last_login', None)
        if last_login:
            from datetime import datetime
            login_time = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
            login_str = login_time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"✓ 最后登录时间已更新: {login_str}")
        else:
            print("✗ 最后登录时间未更新")
            return False
    else:
        print("✗ 未找到测试用户")
        return False
    
    # 9. 清理测试用户
    print("\n[步骤9] 清理测试用户...")
    response = requests.delete(f"{BASE_URL}/api/admin/users/{test_user_id}", headers=headers)
    if response.status_code == 200:
        print(f"✓ 成功删除测试用户")
    else:
        print(f"⚠ 删除测试用户失败: {response.status_code}")
    
    print("\n" + "=" * 60)
    print("✓ 所有测试通过！")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        if test_last_login():
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
