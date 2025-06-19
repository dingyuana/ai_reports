import os
import pandas as pd
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class FileManager:
    """文件管理模块：负责文件的存储、检索和组织"""

    def __init__(self, reports_dir: str, output_dir: str):
        self.reports_dir = reports_dir
        self.output_dir = output_dir
        os.makedirs(reports_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

    def get_student_reports(self) -> List[str]:
        """获取所有学生报告文件路径"""
        report_extensions = ['.pdf', '.doc', '.docx']
        return [os.path.join(self.reports_dir, f)
                for f in os.listdir(self.reports_dir)
                if os.path.isfile(os.path.join(self.reports_dir, f))
                and os.path.splitext(f)[1].lower() in report_extensions]

    def save_excel_summary(self, scores: List[Dict[str, Any]], filename: str = 'grading_summary.xlsx'):
        """保存评分汇总表到Excel"""
        df = pd.DataFrame(scores)
        excel_path = os.path.join(self.output_dir, filename)
        df.to_excel(excel_path, index=False)
        logger.info(f"评分汇总表已保存到 {excel_path}")
        return excel_path