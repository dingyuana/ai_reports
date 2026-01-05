#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:8000"

def test_delete_user():
    print("=" * 60)
    print("测试删除用户功能")
    print("=" * 60)
    
    # 先登录管理员账户
    print("\n[步骤1] 管理员登录...")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            data=login_data
        )
        
        if response.status_code != 200:
            print(f"  ✗ 登录失败: {response.status_code}")
            print(f"    响应: {response.text}")
            return False
        
        data = response.json()
        print(f"  ✓ 登录成功")
        token = data['access_token']
        
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        # 创建一个测试用户
        print("\n[步骤2] 创建测试用户...")
        import time
        timestamp = int(time.time())
        create_data = {
            "username": f"test_delete_user_{timestamp}",
            "password": "test123",
            "email": f"test_delete_{timestamp}@example.com"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/admin/users",
            headers=headers,
            json=create_data
        )
        
        if response.status_code == 200:
            user_data = response.json()
            user_id = user_data['id']
            print(f"  ✓ 创建测试用户成功，ID: {user_id}")
        else:
            print(f"  ✗ 创建测试用户失败: {response.status_code}")
            print(f"    响应: {response.text}")
            return False
        
        # 获取用户列表，确认用户存在
        print("\n[步骤3] 获取用户列表...")
        response = requests.get(
            f"{BASE_URL}/api/admin/users",
            headers=headers
        )
        
        if response.status_code == 200:
            users = response.json()
            test_user = next((u for u in users if u['username'] == 'test_delete_user'), None)
            if test_user:
                print(f"  ✓ 测试用户存在，ID: {test_user['id']}")
            else:
                print(f"  ✗ 测试用户不存在")
                return False
        else:
            print(f"  ✗ 获取用户列表失败: {response.status_code}")
            return False
        
        # 删除用户
        print(f"\n[步骤4] 删除用户 (ID: {user_id})...")
        response = requests.delete(
            f"{BASE_URL}/api/admin/users/{user_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            print(f"  ✓ 删除用户成功")
            print(f"    响应: {response.json()}")
        else:
            print(f"  ✗ 删除用户失败: {response.status_code}")
            print(f"    响应: {response.text}")
            return False
        
        # 验证用户已被删除
        print("\n[步骤5] 验证用户已被删除...")
        response = requests.get(
            f"{BASE_URL}/api/admin/users",
            headers=headers
        )
        
        if response.status_code == 200:
            users = response.json()
            test_user = next((u for u in users if u['username'] == create_data['username']), None)
            if not test_user:
                print(f"  ✓ 用户已被成功删除")
            else:
                print(f"  ✗ 用户仍然存在")
                return False
        else:
            print(f"  ✗ 获取用户列表失败: {response.status_code}")
            return False
        
        print("\n" + "=" * 60)
        print("✓ 所有测试通过！删除用户功能正常")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_delete_user()
    exit(0 if success else 1)