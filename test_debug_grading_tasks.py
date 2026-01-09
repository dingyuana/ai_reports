#!/usr/bin/env python3
"""
调试grading_tasks字典状态
"""
import requests
import json
import time
import threading
import os
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://localhost:8000"

def get_auth_token():
    """获取认证令牌"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        data={"username": "testuser", "password": "test123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        verify=False
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

def test_debug_grading_tasks():
    """调试grading_tasks字典状态"""
    print("调试grading_tasks字典状态...")
    
    # 获取认证令牌
    token = get_auth_token()
    if not token:
        print("无法获取认证令牌")
        return
    
    print("认证令牌获取成功")
    
    # 设置认证头
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 创建一个非常慢的测试目录
    test_dir = "student_reports/2/test_debug_dir"
    os.makedirs(test_dir, exist_ok=True)
    
    # 创建一个简单的小文件，但我们会模拟慢处理
    with open(f"{test_dir}/slow.pdf", "w") as f:
        f.write("这是一个慢处理测试文件")
    
    # 启动批阅任务（关闭AI处理，但我们可以看是否任务被记录）
    print("启动批阅任务...")
    payload = {
        "directory": "test_debug_dir",
        "add_markings": False,
        "ai_review": False,
        "auto_grading": False,
        "selected_model": "Qwen/QwQ-32B"
    }
    
    # 立即调用中止，看看任务是否在字典中
    print("立即尝试中止批阅任务...")
    abort_headers = {
        "Authorization": f"Bearer {token}"
    }
    abort_payload = {"directory": "test_debug_dir"}
    
    response = requests.post(
        f"{BASE_URL}/api/abort-grading",
        data=abort_payload,
        headers=abort_headers,
        verify=False
    )
    print(f"立即中止状态码: {response.status_code}")
    print(f"立即中止响应: {response.json()}")
    
    # 现在启动批阅任务
    response = requests.post(
        f"{BASE_URL}/api/annotate",
        json=payload,
        headers=headers,
        verify=False,
        timeout=60
    )
    
    print(f"批阅任务状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"批阅完成，处理文档数: {len(result.get('documents', []))}")
        for doc in result.get('documents', []):
            print(f"文档: {doc.get('filename', 'unknown')}, 状态: {doc.get('status', 'unknown')}")
    
    # 批阅完成后再次尝试中止
    print("批阅完成后尝试中止...")
    response = requests.post(
        f"{BASE_URL}/api/abort-grading",
        data=abort_payload,
        headers=abort_headers,
        verify=False
    )
    print(f"完成后中止状态码: {response.status_code}")
    print(f"完成后中止响应: {response.json()}")
    
    print("测试完成！")

def main():
    print("=" * 60)
    print("调试grading_tasks字典状态")
    print("=" * 60)
    
    test_debug_grading_tasks()

if __name__ == "__main__":
    main()
