#!/usr/bin/env python3
"""
文件名: test_fix_verification.py
作用: 验证修复后的功能是否正常工作
"""

import os
import sys
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from document_processor import WordProcessor, PDFProcessor

def test_word_to_pdf_and_pdf_processing():
    """测试Word到PDF的转换以及PDF批阅处理"""
    try:
        # 测试文件路径
        input_word_path = os.path.join("student_reports", "test_report.docx")
        converted_pdf_path = os.path.join("test_output", "test_report_converted.pdf")
        processed_pdf_path = os.path.join("test_output", "test_report_processed.pdf")
        
        # 确保输出目录存在
        os.makedirs("test_output", exist_ok=True)
        
        # 测试1: Word到PDF的转换
        logger.info(f"开始测试Word到PDF的转换: {input_word_path} -> {converted_pdf_path}")
        word_processor = WordProcessor()
        conversion_success = word_processor.convert_to_pdf(input_word_path, converted_pdf_path)
        
        if not conversion_success or not os.path.exists(converted_pdf_path):
            logger.error("Word到PDF的转换失败！")
            return False
        
        logger.info("Word到PDF的转换成功！")
        
        # 测试2: PDF批阅处理
        logger.info(f"开始测试PDF批阅处理: {converted_pdf_path} -> {processed_pdf_path}")
        pdf_processor = PDFProcessor()
        
        # 生成一个长评语来测试宽度控制
        long_comment = "这是一个非常长的测试评语，用于验证修复后的评语宽度控制功能是否正常工作。" * 10
        score = 95
        
        pdf_processor.add_comments_and_score(converted_pdf_path, long_comment, score, processed_pdf_path)
        
        if not os.path.exists(processed_pdf_path):
            logger.error("PDF批阅处理失败！")
            return False
        
        logger.info("PDF批阅处理成功！")
        
        # 测试3: 添加对号标注
        final_pdf_path = os.path.join("test_output", "test_report_final.pdf")
        pdf_processor.add_checkmarks(processed_pdf_path, final_pdf_path)
        
        if not os.path.exists(final_pdf_path):
            logger.error("添加对号标注失败！")
            return False
        
        logger.info("添加对号标注成功！")
        
        logger.info("所有测试通过！")
        return True
        
    except Exception as e:
        logger.error(f"测试过程中出现错误: {e}", exc_info=True)
        return False

def main():
    """主函数"""
    try:
        success = test_word_to_pdf_and_pdf_processing()
        if success:
            logger.info("修复验证成功！")
            return 0
        else:
            logger.error("修复验证失败！")
            return 1
    except Exception as e:
        logger.error(f"主函数执行出错: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())