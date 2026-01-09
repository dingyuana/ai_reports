#!/usr/bin/env python3
"""
使用真实AI调用的中止批阅功能测试
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

def create_real_test_directory():
    """创建真实的测试目录"""
    test_dir = "student_reports/2/test_real_abort_dir"
    os.makedirs(test_dir, exist_ok=True)
    
    # 创建一个具有实际内容的PDF文件
    content = """
    实验报告：机器学习算法实现与分析
    
    一、实验目的
    本实验旨在实现并分析常见的机器学习算法，包括线性回归、逻辑回归和决策树。
    
    二、实验环境
    编程语言：Python 3.8
    主要库：scikit-learn, pandas, numpy, matplotlib
    开发环境：Jupyter Notebook
    
    三、实验内容
    1. 线性回归算法实现
       实现了最小二乘法求解线性回归问题
       使用梯度下降法进行参数优化
       实现了正则化防止过拟合
    
    2. 逻辑回归算法实现
       实现了二分类逻辑回归
       使用交叉验证评估模型性能
       实现了多分类扩展
    
    3. 决策树算法实现
       实现了ID3和C4.5算法
       实现了剪枝策略防止过拟合
       实现了特征重要性评估
    
    四、实验结果
    在多个数据集上测试了算法性能，结果如下：
    
    1. 波士顿房价数据集（线性回归）
       - 均方误差：12.5
       - R²分数：0.78
    
    2. 鸢尾花数据集（逻辑回归）
       - 准确率：95.3%
       - F1分数：0.95
    
    3. 泰坦尼克号数据集（决策树）
       - 准确率：81.2%
       - 召回率：0.79
    
    五、实验分析
    通过本次实验，我深入理解了机器学习算法的原理和实现细节。
    不同算法在相同数据集上的表现差异较大，需要根据具体问题选择合适的算法。
    
    六、结论
    本实验成功实现了三种主要的机器学习算法，并通过实验验证了算法的有效性。
    """ * 5  # 重复5次以增加内容长度
    
    with open(f"{test_dir}/ml_experiment_report.pdf", "w") as f:
        f.write(content)
    
    print(f"创建真实测试文件: {test_dir}/ml_experiment_report.pdf")
    return test_dir

def test_real_abort():
    """使用真实AI调用测试中止功能"""
    print("使用真实AI调用测试中止功能...")
    
    # 获取认证令牌
    token = get_auth_token()
    if not token:
        print("无法获取认证令牌")
        return
    
    print("认证令牌获取成功")
    
    # 创建真实测试目录
    test_dir = create_real_test_directory()
    
    # 设置认证头
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 启动批阅任务（启用AI处理）
    print("启动批阅任务...")
    payload = {
        "directory": "test_real_abort_dir",
        "add_markings": False,  # 关闭PDF处理以加快速度
        "ai_review": True,      # 启用AI评语以增加处理时间
        "auto_grading": True,    # 启用自动批分以增加处理时间
        "selected_model": "Qwen/QwQ-32B"
    }
    
    # 使用异步方式启动批阅任务
    grading_started = threading.Event()
    grading_result = {"completed": False, "response": None, "error": None}
    
    def run_grading():
        try:
            grading_started.set()
            response = requests.post(
                f"{BASE_URL}/api/annotate",
                json=payload,
                headers=headers,
                verify=False,
                timeout=300
            )
            grading_result["response"] = response
            grading_result["completed"] = True
        except Exception as e:
            grading_result["error"] = str(e)
            grading_result["completed"] = True
    
    def call_abort():
        """等待一段时间后调用中止"""
        grading_started.wait(timeout=5)
        time.sleep(3)  # 等待3秒让AI调用开始
        
        print("调用中止批阅任务...")
        abort_headers = {
            "Authorization": f"Bearer {token}"
        }
        abort_payload = {"directory": "test_real_abort_dir"}
        
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
    abort_thread.start()
    
    # 等待线程完成
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
                    status = doc.get('status', 'unknown')
                    print(f"文档: {doc.get('filename', 'unknown')}, 状态: {status}")
                    if status == '中断':
                        print("✓ 中止功能正常工作！")
                    elif status == '已取消':
                        print("✓ 文件处理被取消！")
        elif "error" in grading_result:
            print(f"批阅任务出错: {grading_result['error']}")
    else:
        print("批阅任务未在超时时间内完成")
    
    print("测试完成！")

def main():
    print("=" * 60)
    print("使用真实AI调用的中止批阅功能测试")
    print("=" * 60)
    
    test_real_abort()

if __name__ == "__main__":
    main()
