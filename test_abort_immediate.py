#!/usr/bin/env python3
"""
立即中止批阅功能测试
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

def create_large_test_directory():
    """创建包含大量文件的测试目录以延长处理时间"""
    test_dir = "student_reports/2/test_abort_large_dir"
    os.makedirs(test_dir, exist_ok=True)
    
    # 创建多个较大的测试PDF文件
    for i in range(10):
        with open(f"{test_dir}/large_test{i}.pdf", "w") as f:
            f.write(f"这是大型测试PDF文件 {i}\n" * 1000)  # 更大的文件
        print(f"创建大型测试文件: {test_dir}/large_test{i}.pdf")
    
    return test_dir

def test_abort_immediately():
    """立即测试中止批阅功能"""
    print("立即中止批阅功能测试...")
    
    # 获取认证令牌
    token = get_auth_token()
    if not token:
        print("无法获取认证令牌")
        return
    
    print("认证令牌获取成功")
    
    # 创建大型测试目录
    test_dir = create_large_test_directory()
    
    # 设置认证头
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 启动批阅任务（启用所有功能以最大化处理时间）
    print("启动批阅任务...")
    payload = {
        "directory": "test_abort_large_dir",
        "add_markings": True,
        "ai_review": True,
        "auto_grading": True,
        "selected_model": "Qwen/QwQ-32B"
    }
    
    # 使用异步方式启动批阅任务
    grading_started = threading.Event()
    grading_result = {"completed": False, "response": None, "error": None}
    abort_called = threading.Event()
    
    def run_grading():
        try:
            grading_started.set()
            response = requests.post(
                f"{BASE_URL}/api/annotate",
                json=payload,
                headers=headers,
                verify=False,
                timeout=600  # 超长超时时间
            )
            grading_result["response"] = response
            grading_result["completed"] = True
        except Exception as e:
            grading_result["error"] = str(e)
            grading_result["completed"] = True
    
    def call_abort():
        """等待一段时间后调用中止"""
        abort_called.wait(timeout=2)  # 等待中止调用信号
        time.sleep(1)  # 确保批阅已经开始
        
        print("立即中止批阅任务...")
        abort_headers = {
            "Authorization": f"Bearer {token}"
        }
        abort_payload = {"directory": "test_abort_large_dir"}
        
        response = requests.post(
            f"{BASE_URL}/api/abort-grading",
            data=abort_payload,
            headers=abort_headers,
            verify=False
        )
        print(f"中止批阅状态码: {response.status_code}")
        print(f"中止批阅响应: {response.json()}")
    
    grading_thread = threading.Thread(target=run_grading)
    abort_thread = threading.Thread(target=call_abort)
    
    # 启动线程
    grading_thread.start()
    grading_started.wait(timeout=5)
    abort_called.set()  # 信号中止线程可以开始
    abort_thread.start()
    
    # 等待批阅线程结束
    grading_thread.join(timeout=60)
    abort_thread.join(timeout=10)
    
    if grading_result["completed"]:
        if "response" in grading_result and grading_result["response"]:
            print(f"批阅任务响应状态码: {grading_result['response'].status_code}")
            if grading_result["response"].status_code == 200:
                result = grading_result["response"].json()
                print(f"批阅完成，处理文档数: {len(result.get('documents', []))}")
                # 检查是否有中断标记
                for doc in result.get('documents', []):
                    print(f"文档: {doc.get('filename', 'unknown')}, 状态: {doc.get('status', 'unknown')}")
            else:
                print(f"批阅响应: {grading_result['response'].text}")
        elif "error" in grading_result:
            print(f"批阅任务出错: {grading_result['error']}")
    else:
        print("批阅任务未在超时时间内完成")
    
    print("测试完成！")

def main():
    print("=" * 60)
    print("立即中止批阅功能测试")
    print("=" * 60)
    
    test_abort_immediately()

if __name__ == "__main__":
    main()
