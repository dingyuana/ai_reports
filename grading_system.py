"""
文件名: grading_system.py
作用: 实验报告自动批阅系统的核心控制类，协调各个组件完成报告的自动批阅
实现路径:
    1. 初始化系统组件
       - 文件管理器（FileManager）：处理文件的读取和保存
       - AI批阅器（AIGrader）：进行智能评分
       - 文档处理器（DocumentProcessor）：处理不同格式的文档
    2. 设置批阅标准
    3. 批量处理学生报告
       - 读取报告文件
       - 提取文本内容
       - 进行AI评分
       - 添加评语和分数
       - 生成批阅后的文档
    4. 生成评分汇总
功能:
    - 管理和协调整个批阅流程
    - 支持多种文件格式（PDF、DOC、DOCX）
    - 自动添加评语、分数和对号标注
    - 生成评分汇总Excel表格
使用方式:
    1. 创建GradingSystem实例，提供必要的配置
    2. 设置批阅标准
    3. 调用process_all_reports()进行批量处理
依赖:
    - file_manager.py: 文件管理
    - ai_grader.py: AI评分
    - document_processor.py: 文档处理
"""

from typing import List, Dict, Any
import logging
import os
from file_manager import FileManager
from ai_grader import AIGrader
from document_processor import PDFProcessor, WordProcessor

# 配置日志记录器
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
        
    def annotate_report(self, file_path: str, output_path: str, annotations: List[Dict[str, Any]]) -> bool:
        """在报告上添加批注
        
        Args:
            file_path: 原始报告文件路径
            output_path: 输出文件路径
            annotations: 批注列表，每个批注包含页码、位置和内容
            
        Returns:
            bool: 处理是否成功
        """
        try:
            # 获取文件扩展名
            ext = os.path.splitext(file_path)[1].lower()
            
            # 选择合适的处理器
            if ext == '.pdf':
                processor = PDFProcessor()
                return processor.add_annotations(file_path, annotations, output_path)
            else:
                logger.error(f"不支持的文件类型: {ext}")
                return False
                
        except Exception as e:
            logger.error(f"添加批注时出错: {str(e)}", exc_info=True)
            return False

    def get_all_reports(self, directory: str = None) -> List[Dict[str, str]]:
        """获取指定目录下的所有报告列表
        
        Args:
            directory: 可选的子目录名称，如果提供则在该子目录下搜索报告
            
        Returns:
            List[Dict[str, str]]: 报告文件信息列表，每个报告包含文件名、路径和状态
        """
        try:
            reports = self.file_manager.get_student_reports(directory)
            return [
                {
                    "filename": os.path.basename(report_path),
                    "path": report_path,
                    "status": "未处理"  # 默认状态
                }
                for report_path in reports
            ]
        except Exception as e:
            logger.error(f"获取报告列表失败: {e}", exc_info=True)
            raise

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
                
                # 转换Word文件为PDF
                converted_pdf_path = None
                if file_ext in ['.doc', '.docx']:
                    logger.info(f"正在将Word文件转换为PDF: {report_path}")
                    word_processor = self.document_processors[file_ext]
                    
                    # 构建转换后的PDF路径
                    base_name = os.path.basename(report_path)
                    file_name, _ = os.path.splitext(base_name)
                    converted_pdf_path = os.path.join(
                        self.file_manager.output_dir,
                        f"{file_name}_converted.pdf"
                    )
                    
                    # 转换为PDF（带重试机制）
                    conversion_success = False
                    max_retries = 10
                    for attempt in range(max_retries):
                        if word_processor.convert_to_pdf(report_path, converted_pdf_path):
                            conversion_success = True
                            break
                        else:
                            if attempt < max_retries - 1:
                                wait_time = 1  # 移除指数退避，固定等待1秒
                                logger.warning(f"转换Word文件为PDF失败 (尝试 {attempt + 1}/{max_retries}): {report_path}，等待 {wait_time} 秒后重试...")
                                time.sleep(wait_time)
                            else:
                                logger.error(f"转换Word文件为PDF失败 (尝试 {attempt + 1}/{max_retries}): {report_path}")

                    if not conversion_success:
                        continue
                    
                    # 切换到PDF处理器
                    processor = self.document_processors['.pdf']
                    processing_path = converted_pdf_path
                else:
                    # 直接使用原文件路径
                    processor = self.document_processors[file_ext]
                    processing_path = report_path

                # 提取报告文本
                report_text = processor.extract_text(processing_path)

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
                    processing_path, result["comments"], result["score"], output_pdf_path
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

                # 清理临时文件
                if converted_pdf_path and os.path.exists(converted_pdf_path):
                    try:
                        os.remove(converted_pdf_path)
                        logger.info(f"已清理临时文件: {converted_pdf_path}")
                    except Exception as e:
                        logger.warning(f"清理临时文件失败: {e}")

                logger.info(f"报告处理完成: {student_name}, 分数: {result['score']}")

            except Exception as e:
                logger.error(f"处理报告时出错: {e}", exc_info=True)

        # 保存评分汇总表
        if scores:
            return self.file_manager.save_excel_summary(scores)
        else:
            logger.warning("没有成功处理任何报告")
            return None