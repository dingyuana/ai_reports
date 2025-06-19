"""
文件名: file_manager.py
作用: 管理学生报告文件的存储、检索和组织，以及处理评分结果的导出
实现路径:
    1. 初始化文件管理器，创建必要的目录结构
    2. 提供文件检索功能，支持按目录和文件类型筛选
    3. 实现评分结果的Excel导出功能
功能:
    - 管理学生报告文件的存储目录
    - 检索指定目录下的学生报告文件
    - 支持多种文件格式（PDF、DOC、DOCX）
    - 导出评分结果到Excel文件
使用方式:
    - 在grading_system.py中被实例化
    - 用于获取待处理的报告文件列表
    - 用于保存评分结果汇总
依赖:
    - pandas: 用于Excel文件的处理
    - os: 用于文件系统操作
"""

import os
import pandas as pd
from typing import List, Dict, Any
import logging

# 配置日志记录器
logger = logging.getLogger(__name__)


class FileManager:
    """文件管理模块：负责文件的存储、检索和组织"""

    def __init__(self, reports_dir: str, output_dir: str):
        self.reports_dir = reports_dir
        self.output_dir = output_dir
        os.makedirs(reports_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

    def get_student_reports(self, directory: str = None) -> List[str]:
        """获取指定目录下的所有学生报告文件路径
        
        Args:
            directory: 可选的子目录名称，如果提供则在该子目录下搜索报告
            
        Returns:
            List[str]: 报告文件的完整路径列表
        """
        report_extensions = ['.pdf', '.doc', '.docx']
        search_dir = self.reports_dir if directory is None else os.path.join(self.reports_dir, directory)
        
        # 确保目录存在
        if not os.path.exists(search_dir):
            logger.warning(f"目录不存在: {search_dir}")
            return []
            
        return [os.path.join(search_dir, f)
                for f in os.listdir(search_dir)
                if os.path.isfile(os.path.join(search_dir, f))
                and os.path.splitext(f)[1].lower() in report_extensions]

    def save_excel_summary(self, scores: List[Dict[str, Any]], filename: str = 'grading_summary.xlsx'):
        """保存评分汇总表到Excel"""
        df = pd.DataFrame(scores)
        excel_path = os.path.join(self.output_dir, filename)
        df.to_excel(excel_path, index=False)
        logger.info(f"评分汇总表已保存到 {excel_path}")
        return excel_path