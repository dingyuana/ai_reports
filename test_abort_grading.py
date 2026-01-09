#!/usr/bin/env python3
"""
测试中止批阅功能
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"


def test_register():
    print("测试注册API...")
    response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "username": "testuser",
            "password": "test123",
            "email": "test@example.com",
        },
    )
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"注册成功！用户ID: {response.json()['id']}")
        return True
    elif response.status_code == 400 and "用户名已存在" in response.json().get(
        "detail", ""
    ):
        print("用户已存在，跳过注册")
        return True
    else:
        print(f"注册失败: {response.text}")
        return False


def test_login():
    print("\n测试登录API...")
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        data={"username": "testuser", "password": "test123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"登录成功！Token: {response.json()['access_token'][:20]}...")
        return response.json()["access_token"]
    else:
        print(f"登录失败: {response.text}")
        return None


def test_abort_grading(token):
    print("\n测试中止批阅API...")
    headers = {"Authorization": f"Bearer {token}"}

    # 首先获取目录列表
    print("\n获取目录列表...")
    response = requests.get(f"{BASE_URL}/api/reports/", headers=headers)
    print(f"目录列表状态码: {response.status_code}")

    if response.status_code != 200 or not response.json():
        print("没有可用的目录，跳过测试")
        return

    directories = response.json()
    test_directory = directories[0]["name"]
    print(f"使用目录: {test_directory}")

    # 启动批阅任务（不等待完成）
    print("\n启动批阅任务...")
    payload = {
        "directory": test_directory,
        "add_markings": False,
        "ai_review": True,
        "auto_grading": True,
        "selected_model": "Qwen/QwQ-32B",
    }

    # 使用异步方式启动批阅任务
    import threading

    grading_started = threading.Event()
    grading_result = {"completed": False, "response": None}

    def run_grading():
        try:
            grading_started.set()
            response = requests.post(
                f"{BASE_URL}/api/annotate", headers=headers, json=payload, timeout=300
            )
            grading_result["response"] = response
            grading_result["completed"] = True
        except Exception as e:
            grading_result["error"] = str(e)
            grading_result["completed"] = True

    grading_thread = threading.Thread(target=run_grading)
    grading_thread.start()

    # 等待批阅任务启动
    grading_started.wait(timeout=5)
    time.sleep(2)  # 让批阅任务运行一会儿

    # 中止批阅任务
    print("\n中止批阅任务...")
    abort_payload = {"directory": test_directory}
    response = requests.post(
        f"{BASE_URL}/api/abort-grading", headers=headers, data=abort_payload
    )
    print(f"中止批阅状态码: {response.status_code}")
    print(f"中止批阅响应: {response.json()}")

    # 等待批阅线程结束
    grading_thread.join(timeout=10)

    if grading_result["completed"]:
        if "response" in grading_result and grading_result["response"]:
            print(f"\n批阅任务响应状态码: {grading_result['response'].status_code}")
            if grading_result["response"].status_code == 200:
                result = grading_result["response"].json()
                print(f"批阅完成，处理文档数: {len(result.get('documents', []))}")
                # 检查是否有中断标记
                has_interrupt = any(
                    doc.get("status") == "中断" for doc in result.get("documents", [])
                )
                print(f"是否有中断标记: {has_interrupt}")
        elif "error" in grading_result:
            print(f"批阅任务出错: {grading_result['error']}")
    else:
        print("批阅任务未在超时时间内完成")

    print("\n测试完成！")


def main():
    print("=" * 60)
    print("测试中止批阅功能")
    print("=" * 60)

    # 先注册用户（如果不存在）
    if not test_register():
        print("注册失败，无法继续测试")
        return

    # 登录获取token
    token = test_login()
    if token:
        test_abort_grading(token)
    else:
        print("登录失败，无法继续测试")


if __name__ == "__main__":
    main()
