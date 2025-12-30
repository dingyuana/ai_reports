#!/usr/bin/env python3
"""
文件名: test_doc_processing.py
作用: 测试.doc文件的完整转换和批阅流程
"""

import os
import sys
import shutil
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from document_processor import WordProcessor, PDFProcessor
from grading_system import GradingSystem

def create_test_doc_file(doc_path):
    """创建一个简单的测试.doc文件"""
    try:
        # 使用win32com创建.doc文件（仅在Windows环境可用）
        # 在Linux环境下，我们可以直接使用LibreOffice创建或提供示例文件
        logger.info(f"尝试创建测试.doc文件: {doc_path}")
        
        # 检查是否有现成的.doc文件可以复制
        sample_doc_path = "/root/ai_report/sample_doc.doc"
        if os.path.exists(sample_doc_path):
            logger.info(f"发现示例.doc文件，正在复制: {sample_doc_path} -> {doc_path}")
            shutil.copyfile(sample_doc_path, doc_path)
            return True
        
        # 如果没有示例文件，检查是否安装了pydocx或其他库来创建.doc文件
        # 注意：Python本身没有很好的库来创建.doc文件，通常需要依赖外部工具
        logger.warning("无法创建.doc文件，需要手动提供测试文件")
        return False
        
    except Exception as e:
        logger.error(f"创建测试.doc文件失败: {e}", exc_info=True)
        return False

def test_doc_to_pdf_conversion(doc_path, pdf_path):
    """测试.doc文件到PDF的转换"""
    try:
        logger.info(f"测试.doc到PDF转换: {doc_path} -> {pdf_path}")
        
        # 使用WordProcessor转换.doc文件
        word_processor = WordProcessor()
        success = word_processor.convert_to_pdf(doc_path, pdf_path)
        
        if success and os.path.exists(pdf_path):
            logger.info("转换成功！")
            return True
        else:
            logger.error("转换失败！")
            return False
            
    except Exception as e:
        logger.error(f"转换过程出错: {e}", exc_info=True)
        return False

def test_pdf_processing(pdf_path, output_pdf_path):
    """测试PDF文件的批阅处理"""
    try:
        logger.info(f"测试PDF批阅处理: {pdf_path} -> {output_pdf_path}")
        
        # 使用PDFProcessor添加评语和分数
        pdf_processor = PDFProcessor()
        comments = "这是一个测试评语。" * 10  # 生成较长的评语以测试宽度控制
        score = 90
        
        pdf_processor.add_comments_and_score(pdf_path, comments, score, output_pdf_path)
        
        if os.path.exists(output_pdf_path):
            logger.info("PDF批阅处理成功！")
            return True
        else:
            logger.error("PDF批阅处理失败！")
            return False
            
    except Exception as e:
        logger.error(f"PDF批阅处理出错: {e}", exc_info=True)
        return False

def test_full_workflow(doc_path, converted_pdf_path, processed_pdf_path):
    """测试完整的.doc文件处理工作流"""
    logger.info("开始测试完整工作流...")
    
    # 测试1: 转换.doc到PDF
    if not test_doc_to_pdf_conversion(doc_path, converted_pdf_path):
        logger.error("完整工作流测试失败：转换阶段")
        return False
    
    # 测试2: 处理PDF文件
    if not test_pdf_processing(converted_pdf_path, processed_pdf_path):
        logger.error("完整工作流测试失败：批阅阶段")
        return False
    
    logger.info("完整工作流测试成功！")
    return True

def main():
    """主函数"""
    # 创建测试目录
    test_dir = os.path.join(os.getcwd(), "test_doc_processing")
    os.makedirs(test_dir, exist_ok=True)
    
    # 测试文件路径
    doc_path = os.path.join(test_dir, "test_report.doc")
    converted_pdf_path = os.path.join(test_dir, "test_report_converted.pdf")
    processed_pdf_path = os.path.join(test_dir, "test_report_processed.pdf")
    
    try:
        # 创建测试.doc文件
        if not create_test_doc_file(doc_path):
            logger.error("请手动提供一个.doc测试文件")
            return 1
        
        # 测试完整工作流
        if test_full_workflow(doc_path, converted_pdf_path, processed_pdf_path):
            logger.info("所有测试通过！")
            return 0
        else:
            logger.error("测试失败！")
            return 1
            
    except Exception as e:
        logger.error(f"测试过程中出现意外错误: {e}", exc_info=True)
        return 1
    finally:
        # 清理测试文件
        logger.info("清理测试文件...")
        # 我们可以选择保留测试结果以便查看
        # for file_path in [doc_path, converted_pdf_path, processed_pdf_path]:
        #     if os.path.exists(file_path):
        #         os.remove(file_path)
        # if os.path.exists(test_dir):
        #     os.rmdir(test_dir)

if __name__ == "__main__":
    sys.exit(main())