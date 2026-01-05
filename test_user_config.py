#!/usr/bin/env python3
"""
测试用户配置管理功能
验证不同用户可以保存和使用自己的配置
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from config_manager import config_manager
from user_manager import user_manager

def test_user_config():
    print("=" * 60)
    print("开始测试用户配置管理功能")
    print("=" * 60)
    
    # 测试1: 清理并创建两个测试用户
    print("\n[测试1] 清理并创建测试用户...")
    try:
        # 先删除可能存在的测试用户
        for username in ["test_user1", "test_user2", "test_user3"]:
            try:
                user_manager.delete_user_by_username(username)
                print(f"  已删除旧用户: {username}")
            except:
                pass
        
        # 使用不同的email确保唯一性
        import time
        timestamp = int(time.time())
        
        user1_id = user_manager.create_user(
            username="test_user1",
            password="test123",
            email=f"test1_{timestamp}@example.com",
            role="user"
        )
        print(f"✓ 用户1创建成功，ID: {user1_id}")
        
        user2_id = user_manager.create_user(
            username="test_user2",
            password="test123",
            email=f"test2_{timestamp}@example.com",
            role="user"
        )
        print(f"✓ 用户2创建成功，ID: {user2_id}")
    except Exception as e:
        print(f"✗ 创建用户失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 测试2: 为用户1设置自定义配置
    print("\n[测试2] 为用户1设置自定义配置...")
    user1_criteria = """
    请依据以下评分标准对学生提交的大学实训报告进行客观、公正的批阅打分。
    
    评分标准
    总分100分，实际得分范围要在70分到90分之间。评分需兼顾标准要求与分数正态分布特性，避免集中出现逢五、逢十的整数分数。
    
    1. 内容完整性（34分）
    - 实验目的清晰明确（8分）
    - 实验步骤完整详细（10分）
    - 实验结果真实可信（8分）
    - 结果目的相符（8分）
    
    2. 实验规范性（33分）
    - 格式规范整洁（10分）
    - 数据记录准确（8分）
    - 图表清晰规范（8分）
    - 引用规范合理（7分）
    
    3. 分析与结论（33分）
    - 结果分析深入（11分）
    - 结论总结准确（11分）
    - 思考与建议合理（11分）
    """
    
    try:
        success = config_manager.update_user_config(
            user_id=user1_id,
            criteria=user1_criteria,
            min_score=70,
            max_score=90
        )
        if success:
            print("✓ 用户1配置保存成功")
        else:
            print("✗ 用户1配置保存失败")
            return False
    except Exception as e:
        print(f"✗ 保存用户1配置失败: {e}")
        return False
    
    # 测试3: 为用户2设置不同的配置
    print("\n[测试3] 为用户2设置不同的配置...")
    user2_criteria = """
    请依据以下评分标准对学生提交的大学实训报告进行客观、公正的批阅打分。
    
    评分标准
    总分100分，实际得分范围要在50分到85分之间。评分需兼顾标准要求与分数正态分布特性，避免集中出现逢五、逢十的整数分数。
    
    1. 内容完整性（40分）
    - 实验目的清晰明确（10分）
    - 实验步骤完整详细（12分）
    - 实验结果真实可信（9分）
    - 结果目的相符（9分）
    
    2. 实验规范性（30分）
    - 格式规范整洁（10分）
    - 数据记录准确（8分）
    - 图表清晰规范（6分）
    - 引用规范合理（6分）
    
    3. 分析与结论（30分）
    - 结果分析深入（10分）
    - 结论总结准确（10分）
    - 思考与建议合理（10分）
    """
    
    try:
        success = config_manager.update_user_config(
            user_id=user2_id,
            criteria=user2_criteria,
            min_score=50,
            max_score=85
        )
        if success:
            print("✓ 用户2配置保存成功")
        else:
            print("✗ 用户2配置保存失败")
            return False
    except Exception as e:
        print(f"✗ 保存用户2配置失败: {e}")
        return False
    
    # 测试4: 获取用户1的配置
    print("\n[测试4] 获取用户1的配置...")
    try:
        user1_config = config_manager.get_user_config(user1_id)
        if user1_config:
            print(f"✓ 用户1配置获取成功")
            print(f"  - 分数范围: {user1_config['min_score']}-{user1_config['max_score']}")
            print(f"  - 评分标准长度: {len(user1_config['criteria'])} 字符")
            
            if user1_config['min_score'] == 70 and user1_config['max_score'] == 90:
                print("✓ 用户1分数范围验证正确")
            else:
                print(f"✗ 用户1分数范围错误: 期望70-90，实际{user1_config['min_score']}-{user1_config['max_score']}")
                return False
        else:
            print("✗ 用户1配置获取失败")
            return False
    except Exception as e:
        print(f"✗ 获取用户1配置失败: {e}")
        return False
    
    # 测试5: 获取用户2的配置
    print("\n[测试5] 获取用户2的配置...")
    try:
        user2_config = config_manager.get_user_config(user2_id)
        if user2_config:
            print(f"✓ 用户2配置获取成功")
            print(f"  - 分数范围: {user2_config['min_score']}-{user2_config['max_score']}")
            print(f"  - 评分标准长度: {len(user2_config['criteria'])} 字符")
            
            if user2_config['min_score'] == 50 and user2_config['max_score'] == 85:
                print("✓ 用户2分数范围验证正确")
            else:
                print(f"✗ 用户2分数范围错误: 期望50-85，实际{user2_config['min_score']}-{user2_config['max_score']}")
                return False
        else:
            print("✗ 用户2配置获取失败")
            return False
    except Exception as e:
        print(f"✗ 获取用户2配置失败: {e}")
        return False
    
    # 测试6: 验证两个用户的配置不同
    print("\n[测试6] 验证两个用户的配置不同...")
    if user1_config['min_score'] != user2_config['min_score'] or \
       user1_config['max_score'] != user2_config['max_score'] or \
       user1_config['criteria'] != user2_config['criteria']:
        print("✓ 两个用户的配置确实不同")
    else:
        print("✗ 两个用户的配置相同，测试失败")
        return False
    
    # 测试7: 获取包含分数范围的提示词
    print("\n[测试7] 获取包含分数范围的提示词...")
    try:
        user1_criteria_with_range = config_manager.get_criteria_with_score_range(user1_id)
        if "70分到90分之间" in user1_criteria_with_range:
            print("✓ 用户1提示词包含正确的分数范围")
        else:
            print("✗ 用户1提示词不包含正确的分数范围")
            return False
        
        user2_criteria_with_range = config_manager.get_criteria_with_score_range(user2_id)
        if "50分到85分之间" in user2_criteria_with_range:
            print("✓ 用户2提示词包含正确的分数范围")
        else:
            print("✗ 用户2提示词不包含正确的分数范围")
            return False
    except Exception as e:
        print(f"✗ 获取包含分数范围的提示词失败: {e}")
        return False
    
    # 测试8: 测试新用户获取默认配置
    print("\n[测试8] 测试新用户获取默认配置...")
    try:
        user3_id = user_manager.create_user(
            username="test_user3",
            password="test123",
            email=f"test3_{timestamp}@example.com",
            role="user"
        )
        print(f"✓ 用户3创建成功，ID: {user3_id}")
        
        user3_config = config_manager.get_or_create_user_config(user3_id)
        if user3_config:
            print(f"✓ 用户3默认配置获取成功")
            print(f"  - 分数范围: {user3_config['min_score']}-{user3_config['max_score']}")
            
            if user3_config['min_score'] == 60 and user3_config['max_score'] == 95:
                print("✓ 用户3默认分数范围验证正确")
            else:
                print(f"✗ 用户3默认分数范围错误: 期望60-95，实际{user3_config['min_score']}-{user3_config['max_score']}")
                return False
        else:
            print("✗ 用户3默认配置获取失败")
            return False
    except Exception as e:
        print(f"✗ 测试新用户默认配置失败: {e}")
        return False
    
    # 测试9: 测试配置更新
    print("\n[测试9] 测试配置更新...")
    try:
        success = config_manager.update_user_config(
            user_id=user1_id,
            criteria=user1_criteria,
            min_score=65,
            max_score=88
        )
        if success:
            print("✓ 用户1配置更新成功")
            
            updated_config = config_manager.get_user_config(user1_id)
            if updated_config['min_score'] == 65 and updated_config['max_score'] == 88:
                print("✓ 用户1更新后的配置验证正确")
            else:
                print(f"✗ 用户1更新后的配置错误: 期望65-88，实际{updated_config['min_score']}-{updated_config['max_score']}")
                return False
        else:
            print("✗ 用户1配置更新失败")
            return False
    except Exception as e:
        print(f"✗ 更新用户1配置失败: {e}")
        return False
    
    # 测试10: 验证用户2的配置未受影响
    print("\n[测试10] 验证用户2的配置未受影响...")
    try:
        user2_config_after = config_manager.get_user_config(user2_id)
        if user2_config_after['min_score'] == 50 and user2_config_after['max_score'] == 85:
            print("✓ 用户2的配置未受影响")
        else:
            print(f"✗ 用户2的配置被意外修改")
            return False
    except Exception as e:
        print(f"✗ 验证用户2配置失败: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("所有测试通过！✓")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        success = test_user_config()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)