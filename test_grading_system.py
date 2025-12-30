#!/usr/bin/env python3
"""
文件名: test_grading_system.py
作用: 测试GradingSystem的process_all_reports方法
"""

import os
import sys
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from grading_system import GradingSystem

def test_process_all_reports():
    """测试GradingSystem的process_all_reports方法"""
    try:
        # 创建GradingSystem实例
        reports_dir = "student_reports"
        output_dir = "graded_reports"
        api_config = {
            "api_key": "test_key",
            "api_url": "http://localhost:7654"
        }
        
        grading_system = GradingSystem(reports_dir, output_dir, api_config)
        
        # 设置批阅标准
        grading_criteria = "测试批阅标准：1. 内容完整性（50分）；2. 逻辑清晰性（30分）；3. 格式规范性（20分）"
        grading_system.set_grading_criteria(grading_criteria)
        
        # 处理所有报告
        logger.info("开始处理所有报告...")
        result = grading_system.process_all_reports()
        
        if result:
            logger.info(f"处理完成，生成了评分汇总表：{result}")
            return True
        else:
            logger.error("处理失败或没有处理任何报告！")
            return False
            
    except Exception as e:
        logger.error(f"测试过程中出现错误: {e}", exc_info=True)
        return False

def main():
    """主函数"""
    try:
        success = test_process_all_reports()
        if success:
            logger.info("GradingSystem测试通过！")
            return 0
        else:
            logger.error("GradingSystem测试失败！")
            return 1
    except Exception as e:
        logger.error(f"主函数执行出错: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())