#!/usr/bin/env python3
"""
直接测试grading_tasks字典管理
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

def test_task_dict_management():
    """测试任务字典管理"""
    print("测试任务字典管理...")
    
    # 获取认证令牌
    token = get_auth_token()
    if not token:
        print("无法获取认证令牌")
        return
    
    print("认证令牌获取成功")
    
    # 创建测试目录
    test_dir = "student_reports/2/test_task_dict_dir"
    os.makedirs(test_dir, exist_ok=True)
    
    # 创建一个文件
    with open(f"{test_dir}/test.pdf", "w") as f:
        f.write("测试文件")
    
    # 设置认证头
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 模拟批量请求来测试任务管理
    print("启动多个批阅任务...")
    
    payloads = []
    for i in range(3):
        payload = {
            "directory": f"test_task_dict_dir{i}",
            "add_markings": False,
            "ai_review": False,
            "auto_grading": False,
            "selected_model": "Qwen/QwQ-32B"
        }
        # 为每个目录创建文件
        os.makedirs(f"student_reports/2/test_task_dict_dir{i}", exist_ok=True)
        with open(f"student_reports/2/test_task_dict_dir{i}/test{i}.pdf", "w") as f:
            f.write(f"测试文件{i}")
        payloads.append(payload)
    
    # 快速启动多个任务
    results = []
    threads = []
    
    def run_grading(payload, index):
        try:
            response = requests.post(
                f"{BASE_URL}/api/annotate",
                json=payload,
                headers=headers,
                verify=False,
                timeout=60
            )
            results.append((index, response.status_code, response.json()))
        except Exception as e:
            results.append((index, "error", str(e)))
    
    # 启动所有任务
    for i, payload in enumerate(payloads):
        thread = threading.Thread(target=run_grading, args=(payload, i))
        threads.append(thread)
        thread.start()
        time.sleep(0.1)  # 短暂延迟
    
    # 等待一下让任务开始
    time.sleep(1)
    
    # 尝试中止所有任务
    for i in range(3):
        abort_headers = {
            "Authorization": f"Bearer {token}"
        }
        abort_payload = {"directory": f"test_task_dict_dir{i}"}
        
        response = requests.post(
            f"{BASE_URL}/api/abort-grading",
            data=abort_payload,
            headers=abort_headers,
            verify=False
        )
        print(f"任务{i}中止状态码: {response.status_code}")
        print(f"任务{i}中止响应: {response.json()}")
    
    # 等待所有任务完成
    for thread in threads:
        thread.join(timeout=30)
    
    print("所有任务结果:")
    for index, status, result in results:
        print(f"任务{index}: 状态码={status}, 结果={result}")
    
    print("测试完成！")

def main():
    print("=" * 60)
    print("直接测试grading_tasks字典管理")
    print("=" * 60)
    
    test_task_dict_management()

if __name__ == "__main__":
    main()
