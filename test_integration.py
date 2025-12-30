#!/usr/bin/env python3
"""
测试Word到PDF转换与报告处理的集成
"""

import os
import logging
from datetime import datetime
from grading_system import GradingSystem
from document_processor import PDFProcessor, WordProcessor

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_word_to_pdf_integration():
    """测试Word到PDF转换与报告处理的集成"""
    
    # 设置测试目录
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    REPORTS_DIR = os.path.join(BASE_DIR, "student_reports")
    OUTPUT_DIR = os.path.join(BASE_DIR, "test_output")
    
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 测试文档路径
    test_word_path = os.path.join(REPORTS_DIR, "test_report.docx")
    
    # 检查测试文档是否存在
    if not os.path.exists(test_word_path):
        logger.error(f"测试文档不存在: {test_word_path}")
        return False
    
    try:
        # 创建模拟API配置
        mock_api_config = {
            "api_key": "mock-key",
            "api_endpoint": "http://mock-endpoint",
            "model": "mock-model",
            "timeout": 30,
            "max_retries": 3,
            "temperature": 0.7
        }
        
        # 创建GradingSystem实例
        system = GradingSystem(REPORTS_DIR, OUTPUT_DIR, mock_api_config)
        
        # 设置批阅标准
        criteria = """
        1. 实验目的明确性 (20分): 学生是否清晰阐述了实验目的?
        2. 实验方法合理性 (20分): 实验步骤是否完整且合理?
        3. 实验数据准确性 (20分): 数据记录是否准确，图表是否清晰?
        4. 数据分析深度 (20分): 是否对实验结果进行了深入分析?
        5. 结论合理性 (20分): 结论是否与实验结果一致，是否有适当的讨论?
        """
        system.set_grading_criteria(criteria)
        
        # 模拟AI评分结果
        mock_result = {
            "score": 85,
            "comments": "测试评语：报告整体质量良好，实验目的明确，方法合理，数据分析深入，但结论可以更加详细。"
        }
        
        # 提取报告文本
        word_processor = WordProcessor()
        report_text = word_processor.extract_text(test_word_path)
        logger.info(f"成功提取报告文本，长度: {len(report_text)} 字符")
        
        # 转换为PDF
        pdf_path = os.path.join(OUTPUT_DIR, "test_report_converted.pdf")
        conversion_success = word_processor.convert_to_pdf(test_word_path, pdf_path)
        
        if not conversion_success:
            logger.error("Word到PDF转换失败")
            return False
        
        logger.info(f"成功将Word转换为PDF: {pdf_path}")
        
        # 使用PDFProcessor处理转换后的PDF
        pdf_processor = PDFProcessor()
        
        # 提取PDF文本（验证转换质量）
        pdf_text = pdf_processor.extract_text(pdf_path)
        logger.info(f"成功从PDF提取文本，长度: {len(pdf_text)} 字符")
        
        # 添加评语和分数
        annotated_pdf_path = os.path.join(OUTPUT_DIR, "test_report_annotated.pdf")
        pdf_processor.add_comments_and_score(pdf_path, mock_result["comments"], mock_result["score"], annotated_pdf_path)
        logger.info(f"成功添加评语和分数: {annotated_pdf_path}")
        
        # 添加对号标注
        final_pdf_path = os.path.join(OUTPUT_DIR, "test_report_final.pdf")
        pdf_processor.add_checkmarks(annotated_pdf_path, final_pdf_path)
        logger.info(f"成功添加对号标注: {final_pdf_path}")
        
        # 检查最终文件是否存在
        if os.path.exists(final_pdf_path):
            logger.info(f"测试完成！最终输出文件: {final_pdf_path}, 大小: {os.path.getsize(final_pdf_path)} 字节")
            return True
        else:
            logger.error("最终输出文件不存在")
            return False
            
    except Exception as e:
        logger.error(f"集成测试过程中出错: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    test_word_to_pdf_integration()
