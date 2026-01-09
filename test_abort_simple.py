#!/usr/bin/env python3
"""
简化的中止批阅功能测试 - 绕过认证
"""

import requests
import json
import time
import threading
import os

BASE_URL = "http://localhost:8000"


def create_test_directory():
    """创建测试目录和文件"""
    test_dir = "student_reports/1/test_abort_dir"
    os.makedirs(test_dir, exist_ok=True)

    # 创建一个测试PDF文件
    with open(f"{test_dir}/test.pdf", "w") as f:
        f.write("这是一个测试PDF文件")

    print(f"创建测试目录: {test_dir}")
    return test_dir


def test_abort_grading_direct():
    """直接测试中止批阅功能"""
    print("直接测试中止批阅功能...")

    # 创建测试目录
    create_test_directory()

    # 启动批阅任务（不等待完成）
    print("启动批阅任务...")
    payload = {
        "directory": "test_abort_dir",
        "add_markings": False,
        "ai_review": False,  # 关闭AI评语以加快速度
        "auto_grading": False,  # 关闭自动批分以加快速度
        "selected_model": "Qwen/QwQ-32B",
    }

    # 使用异步方式启动批阅任务
    grading_started = threading.Event()
    grading_result = {"completed": False, "response": None, "error": None}

    def run_grading():
        try:
            grading_started.set()
            response = requests.post(
                f"{BASE_URL}/api/annotate", json=payload, timeout=60
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
    print("中止批阅任务...")
    abort_payload = {"directory": "test_abort_dir"}
    response = requests.post(f"{BASE_URL}/api/abort-grading", data=abort_payload)
    print(f"中止批阅状态码: {response.status_code}")
    print(f"中止批阅响应: {response.json()}")

    # 等待批阅线程结束
    grading_thread.join(timeout=10)

    if grading_result["completed"]:
        if "response" in grading_result and grading_result["response"]:
            print(f"批阅任务响应状态码: {grading_result['response'].status_code}")
            if grading_result["response"].status_code == 200:
                result = grading_result["response"].json()
                print(f"批阅完成，处理文档数: {len(result.get('documents', []))}")
                # 检查是否有中断标记
                for doc in result.get("documents", []):
                    print(
                        f"文档: {doc.get('filename', 'unknown')}, 状态: {doc.get('status', 'unknown')}"
                    )
            else:
                print(f"批阅响应: {grading_result['response'].text}")
        elif "error" in grading_result:
            print(f"批阅任务出错: {grading_result['error']}")
    else:
        print("批阅任务未在超时时间内完成")

    print("测试完成！")


def main():
    print("=" * 60)
    print("简化的中止批阅功能测试")
    print("=" * 60)

    test_abort_grading_direct()


if __name__ == "__main__":
    main()
