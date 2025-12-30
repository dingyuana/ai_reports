#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复效果的脚本
验证：
1. 对号大小和位置（每页中央，48号）
2. 批注内容是否有乱码
3. 分数是否在首页右上角
"""

import os
from document_processor import PDFProcessor, WordProcessor

def main():
    # 测试PDF文档
    pdf_file = "/root/ai_report/student_reports/内蒙古民族大学-电子-22级-5班-嵌入图形界面开发-实验四基于tcpip的网络聊天室系统的实现/2022级电子信息科学与技术1班-229051091009-张学峰-实验报告.pdf"
    pdf_output = "/root/ai_report/temp/test_pdf_fixed.pdf"
    
    # 测试Word文档
    word_file = "/root/ai_report/student_reports/内蒙古民族大学-电子-22级-5班-嵌入图形界面开发-实验四基于tcpip的网络聊天室系统的实现/2022级电子信息科学与技术1班-229051091004-张羽-实验报告.docx"
    word_output = "/root/ai_report/temp/test_word_fixed.docx"
    
    # 测试内容 - 中文批注
    score = 85
    comments_chinese = """1. 实验目的明确，能够准确理解实验要求。
2. 代码实现基本正确，但存在一些细节问题需要改进。
3. 实验报告格式规范，内容完整。
4. 实验结果分析较为深入，但可以进一步完善。
5. 整体表现良好，值得肯定。"""
    
    # 测试内容 - 英文批注，用于验证是否中文显示问题
    comments_english = """1. The experiment objective is clear, with accurate understanding of requirements.
2. Code implementation is generally correct, but there are some details that need improvement.
3. The experiment report format is standardized and content is complete.
4. The analysis of experimental results is relatively in-depth, but could be further improved.
5. Overall performance is good and worthy of recognition."""
    
    # 选择使用的批注语言（默认使用中文，如需测试英文，可切换）
    comments = comments_chinese  # 或 comments_english
    
    # 确保temp目录存在
    os.makedirs("/root/ai_report/temp", exist_ok=True)
    
    print("开始测试PDF修复效果...")
    try:
        # 测试PDFProcessor
        pdf_processor = PDFProcessor()
        
        # 测试添加分数和批注
        pdf_processor.add_comments_and_score(pdf_file, comments, score, pdf_output)
        print(f"PDF分数和批注添加成功: {pdf_output}")
        
        # 测试添加对号
        pdf_checkmark_output = "/root/ai_report/temp/test_pdf_checkmark.pdf"
        pdf_processor.add_checkmarks(pdf_output, pdf_checkmark_output)
        print(f"PDF对号添加成功: {pdf_checkmark_output}")
        
    except Exception as e:
        print(f"PDF测试失败: {e}")
    
    print("\n开始测试Word修复效果...")
    try:
        # 测试WordProcessor
        word_processor = WordProcessor()
        
        # 测试添加分数和批注
        word_processor.add_comments_and_score(word_file, comments, score, word_output)
        print(f"Word分数和批注添加成功: {word_output}")
        
        # 测试添加对号
        word_checkmark_output = "/root/ai_report/temp/test_word_checkmark.docx"
        word_processor.add_checkmarks(word_output, word_checkmark_output)
        print(f"Word对号添加成功: {word_checkmark_output}")
        
    except Exception as e:
        print(f"Word测试失败: {e}")
    
    print("\n测试完成！请检查输出文件:")
    print(f"PDF测试文件: {pdf_checkmark_output}")
    print(f"Word测试文件: {word_checkmark_output}")
    print("\n验证内容:")
    print("1. 对号是否在每页中央，字号是否为96号")
    print("2. 批注内容是否有乱码")
    print("3. 分数是否在首页右上角")
    print("4. 字号是否增大到20pt")
    print("5. 是否包含日期信息")

if __name__ == "__main__":
    main()
