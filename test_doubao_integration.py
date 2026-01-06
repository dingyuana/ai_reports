"""
测试豆包模型集成
验证豆包AI模型是否能够正常工作
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_grader import AIGrader
from config import API_CONFIG

def test_doubao_integration():
    """测试豆包模型集成"""
    print("=" * 60)
    print("测试豆包模型集成")
    print("=" * 60)
    
    # 检查配置
    print(f"\n当前AI提供商: {API_CONFIG.get('provider', 'unknown')}")
    print(f"当前模型: {API_CONFIG.get('model', 'unknown')}")
    print(f"API端点: {API_CONFIG.get('api_endpoint', 'unknown')}")
    
    if API_CONFIG.get('provider') != 'doubao':
        print("\n警告: 当前配置不是豆包模型")
        print("请检查 .env 文件中的 AI_PROVIDER 设置")
        return False
    
    # 创建AI批阅器
    print("\n初始化AI批阅器...")
    grader = AIGrader(API_CONFIG)
    
    # 测试报告文本
    test_report = """
实验名称：物理实验 - 测量重力加速度

实验目的：
1. 学习使用单摆测量重力加速度的方法
2. 掌握数据处理和误差分析的基本方法

实验原理：
单摆的周期公式为 T = 2π√(L/g)，其中T为周期，L为摆长，g为重力加速度。
通过测量单摆的周期和摆长，可以计算出重力加速度 g = 4π²L/T²。

实验步骤：
1. 组装单摆装置，调整摆长为1.0米
2. 用秒表测量单摆摆动50个周期的时间
3. 重复测量5次，取平均值
4. 记录数据并进行计算

实验结果：
测量数据如下：
- 摆长 L = 1.00 m
- 50个周期时间 t = 100.2 s
- 周期 T = 2.004 s
- 计算得到重力加速度 g = 9.85 m/s²

数据分析：
实验测得的重力加速度为 9.85 m/s²，与标准值 9.80 m/s² 相比，相对误差为 0.51%。
误差来源可能包括：空气阻力、摆长测量误差、时间测量误差等。

结论：
通过单摆实验成功测量了重力加速度，实验结果与理论值吻合良好，实验方法可靠。
"""
    
    # 测试批阅标准
    test_criteria = """
评分标准（满分100分）：
1. 实验目的（10分）：明确说明实验目的
2. 实验原理（20分）：正确阐述实验原理和公式
3. 实验步骤（20分）：步骤清晰、完整、可操作
4. 实验结果（20分）：数据记录完整、计算正确
5. 数据分析（20分）：误差分析合理、结论正确
6. 格式规范（10分）：格式规范、语言通顺
"""
    
    print("\n开始批阅测试报告...")
    print(f"报告长度: {len(test_report)} 字符")
    print(f"批阅标准长度: {len(test_criteria)} 字符")
    
    try:
        # 调用AI批阅
        result = grader.grade_report(test_report, test_criteria)
        
        print("\n" + "=" * 60)
        print("批阅结果")
        print("=" * 60)
        print(f"\n得分: {result['score']} 分")
        print(f"\n评语:\n{result['comments']}")
        
        # 验证结果
        if result['score'] and isinstance(result['score'], int):
            print("\n" + "=" * 60)
            print("✓ 豆包模型集成测试成功！")
            print("=" * 60)
            return True
        else:
            print("\n" + "=" * 60)
            print("✗ 豆包模型集成测试失败：分数格式不正确")
            print("=" * 60)
            return False
            
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"✗ 豆包模型集成测试失败：{str(e)}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_doubao_integration()
    sys.exit(0 if success else 1)