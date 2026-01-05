#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:8000"

def test_login():
    print("测试登录API...")
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

def test_get_users(token):
    print("\n测试获取所有用户API...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_get_logs(token):
    print("\n测试获取所有日志API...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/admin/logs", headers=headers)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def main():
    print("开始测试API端点...")
    
    token = test_login()
    if token:
        print(f"\n登录成功！Token: {token}")
        test_get_users(token)
        test_get_logs(token)
    else:
        print("登录失败！")

if __name__ == "__main__":
    main()
