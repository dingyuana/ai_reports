#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证PDF文件中的中文是否正确显示
"""

import pdfplumber

def verify_pdf_chinese(pdf_path):
    print(f"验证PDF文件: {pdf_path}")
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    print(f"第{page_num}页文本内容:")
                    print(text)
                    print("-" * 50)
                    
                    # 检查是否包含中文字符
                    has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
                    print(f"第{page_num}页是否包含中文字符: {'是' if has_chinese else '否'}")
    except Exception as e:
        print(f"验证失败: {e}")

if __name__ == "__main__":
    pdf_path = "/root/ai_report/temp/test_pdf_checkmark.pdf"
    verify_pdf_chinese(pdf_path)
