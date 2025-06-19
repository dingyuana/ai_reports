import os
import io
from typing import List, Dict, Any
from abc import ABC, abstractmethod
import logging
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import Color
from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import pdfplumber
import win32com.client

logger = logging.getLogger(__name__)


class DocumentProcessor(ABC):
    """文档处理抽象基类"""

    @abstractmethod
    def extract_text(self, file_path: str) -> str:
        """从文档中提取文本"""
        pass

    @abstractmethod
    def add_comments_and_score(self, file_path: str, comments: str, score: int, output_path: str) -> None:
        """在文档上添加评语和分数"""
        pass

    @abstractmethod
    def add_checkmarks(self, file_path: str, output_path: str) -> None:
        """在每页添加对号标注"""
        pass


class PDFProcessor(DocumentProcessor):
    """PDF文档处理实现"""

    def extract_text(self, file_path: str) -> str:
        """从PDF中提取文本"""
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text

    def add_comments_and_score(self, file_path: str, comments: str, score: int, output_path: str) -> None:
        """在PDF上添加评语和分数"""
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        can.setFont("Helvetica", 10)
        can.setFillColor(Color(0, 0, 0, alpha=0.7))

        x, y = 30, 30
        can.drawString(x, y, f"分数: {score}分")
        can.drawString(x, y - 20, "评语:")

        lines = comments.split('\n')
        for i, line in enumerate(lines):
            can.drawString(x, y - 40 - i * 15, line)

        can.save()

        packet.seek(0)
        new_pdf = PdfReader(packet)

        input_pdf = PdfReader(file_path)
        output_pdf = PdfWriter()

        first_page = input_pdf.pages[0]
        first_page.merge_page(new_pdf.pages[0])
        output_pdf.add_page(first_page)

        for page in input_pdf.pages[1:]:
            output_pdf.add_page(page)

        with open(output_path, "wb") as out_f:
            output_pdf.write(out_f)

    def add_checkmarks(self, file_path: str, output_path: str) -> None:
        """在PDF每页添加对号标注"""
        input_pdf = PdfReader(file_path)
        output_pdf = PdfWriter()

        for page_num in range(len(input_pdf.pages)):
            page = input_pdf.pages[page_num]

            # 创建对号标记
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=letter)
            can.setFont("Helvetica", 12)
            can.setFillColor(Color(0, 1, 0, alpha=0.7))  # 绿色对号

            # 在每页右下角添加对号
            x, y = 550, 30
            can.drawString(x, y, "✓")

            can.save()
            packet.seek(0)
            checkmark_pdf = PdfReader(packet)

            # 合并对号到当前页
            page.merge_page(checkmark_pdf.pages[0])
            output_pdf.add_page(page)

        with open(output_path, "wb") as out_f:
            output_pdf.write(out_f)


class WordProcessor(DocumentProcessor):
    """Word文档处理实现"""

    def extract_text(self, file_path: str) -> str:
        """从Word文档中提取文本"""
        if file_path.endswith('.docx'):
            doc = Document(file_path)
            return '\n'.join([para.text for para in doc.paragraphs])
        else:  # .doc
            word = win32com.client.Dispatch("Word.Application")
            doc = word.Documents.Open(file_path)
            text = doc.Content.Text
            doc.Close()
            word.Quit()
            return text

    def add_comments_and_score(self, file_path: str, comments: str, score: int, output_path: str) -> None:
        """在Word文档上添加评语和分数"""
        doc = Document(file_path)

        doc.add_page_break()

        p = doc.add_paragraph()
        p.add_run(f"分数: {score}分").bold = True
        p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

        doc.add_paragraph("评语:")
        doc.add_paragraph(comments)

        doc.save(output_path)

    def add_checkmarks(self, file_path: str, output_path: str) -> None:
        """在Word文档每页添加对号标注"""
        # 注意：Word文档添加对号标注的实现比PDF复杂，因为Word的分页在处理时不如PDF直观
        # 这里简化处理，仅在文档末尾添加对号汇总
        doc = Document(file_path)

        doc.add_page_break()
        p = doc.add_paragraph()
        p.add_run("✓ 本报告已完成批阅").bold = True

        doc.save(output_path)    