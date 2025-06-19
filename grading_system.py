from typing import List, Dict, Any
import logging
import os
from file_manager import FileManager
from ai_grader import AIGrader
from document_processor import PDFProcessor, WordProcessor

logger = logging.getLogger(__name__)


class GradingSystem:
    """实验报告自动批阅系统主类"""

    def __init__(self, reports_dir: str, output_dir: str, api_config: Dict[str, str]):
        self.file_manager = FileManager(reports_dir, output_dir)
        self.ai_grader = AIGrader(api_config)
        self.document_processors = {
            '.pdf': PDFProcessor(),
            '.docx': WordProcessor(),
            '.doc': WordProcessor()
        }
        self.grading_criteria = ""

    def set_grading_criteria(self, criteria: str):
        """设置批阅标准"""
        self.grading_criteria = criteria
        logger.info("批阅标准已设置")

    def process_all_reports(self) -> str:
        """处理所有学生报告"""
        if not self.grading_criteria:
            raise ValueError("请先设置批阅标准")

        student_reports = self.file_manager.get_student_reports()
        if not student_reports:
            logger.warning("未找到学生报告")
            return None

        scores = []

        for report_path in student_reports:
            try:
                logger.info(f"正在处理报告: {report_path}")
                file_ext = os.path.splitext(report_path)[1].lower()

                if file_ext not in self.document_processors:
                    logger.warning(f"不支持的文件格式: {file_ext}")
                    continue

                processor = self.document_processors[file_ext]

                # 提取报告文本
                report_text = processor.extract_text(report_path)

                # AI批阅
                result = self.ai_grader.grade_report(report_text, self.grading_criteria)

                # 构建输出文件名
                base_name = os.path.basename(report_path)
                file_name, _ = os.path.splitext(base_name)
                output_pdf_path = os.path.join(
                    self.file_manager.output_dir,
                    f"{file_name}_annotated.pdf"
                )

                # 添加评语和分数
                processor.add_comments_and_score(
                    report_path, result["comments"], result["score"], output_pdf_path
                )

                # 添加对号标注
                final_output_path = os.path.join(
                    self.file_manager.output_dir,
                    f"{file_name}_final.pdf"
                )
                processor.add_checkmarks(output_pdf_path, final_output_path)

                # 记录评分结果
                student_name = file_name.split('_')[0]  # 假设文件名格式为"学生姓名_报告标题"
                scores.append({
                    "student_name": student_name,
                    "filename": base_name,
                    "score": result["score"],
                    "comments": result["comments"],
                    "annotated_report_path": final_output_path
                })

                logger.info(f"报告处理完成: {student_name}, 分数: {result['score']}")

            except Exception as e:
                logger.error(f"处理报告时出错: {e}", exc_info=True)

        # 保存评分汇总表
        if scores:
            return self.file_manager.save_excel_summary(scores)
        else:
            logger.warning("没有成功处理任何报告")
            return None