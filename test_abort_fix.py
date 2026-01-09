#!/usr/bin/env python3
"""
测试修复后的中止批阅功能
"""

import requests
import time
import threading
import json

BASE_URL = "http://localhost:8000"


def test_abort_functionality():
    print("测试修复后的中止批阅功能...")

    # 创建测试用户并获取token
    login_data = {"username": "test_user", "password": "test_password"}

    try:
        # 尝试登录
        response = requests.post(f"{BASE_URL}/token", data=login_data)
        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get("access_token")
            headers = {"Authorization": f"Bearer {token}"}

            print("✓ 用户登录成功")

            # 模拟开始一个批阅任务（这需要实际的测试数据）
            print("注意: 需要实际的测试数据才能完整测试中止功能")

            # 测试中止API响应
            test_directory = "test_directory"
            response = requests.post(
                f"{BASE_URL}/api/abort-grading",
                data={"directory": test_directory},
                headers=headers,
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ 中止API响应正常: {result.get('message', 'Unknown')}")
            else:
                print(f"✗ 中止API响应异常: {response.status_code}")

        else:
            print(f"✗ 登录失败: {response.status_code}")
            print("响应内容:", response.text)

    except Exception as e:
        print(f"✗ 测试过程中出错: {e}")


if __name__ == "__main__":
    test_abort_functionality()
