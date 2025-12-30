#!/usr/bin/env python3
"""
测试Word到PDF的转换功能
"""

import os
import logging
from document_processor import WordProcessor

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_word_to_pdf_conversion():
    """测试Word到PDF的转换"""
    
    # 测试文档路径
    word_path = 'student_reports/test_report.docx'
    pdf_path = 'student_reports/test_report_converted.pdf'
    
    # 检查测试文档是否存在
    if not os.path.exists(word_path):
        logger.error(f"测试文档不存在: {word_path}")
        return False
    
    try:
        # 创建WordProcessor实例
        word_processor = WordProcessor()
        
        logger.info(f"开始将 {word_path} 转换为 PDF")
        
        # 执行转换
        success = word_processor.convert_to_pdf(word_path, pdf_path)
        
        if success:
            logger.info(f"转换成功! 输出文件: {pdf_path}")
            
            # 检查转换后的PDF文件是否存在
            if os.path.exists(pdf_path):
                logger.info(f"转换后的PDF文件已存在，大小为: {os.path.getsize(pdf_path)} 字节")
                return True
            else:
                logger.error(f"转换成功但未找到输出文件: {pdf_path}")
                return False
        else:
            logger.error(f"转换失败: {word_path}")
            return False
            
    except Exception as e:
        logger.error(f"转换过程中出错: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    test_word_to_pdf_conversion()
