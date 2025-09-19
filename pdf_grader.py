import os
import json
import io
import sys
import decimal
from PyPDF2 import PdfReader, PdfWriter, PageObject
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
import comtypes.client
import pythoncom
from PIL import Image
from reportlab.lib.utils import ImageReader


def grade_student_reports(sub_dir=None):
    """
    处理学生报告，添加分数和评语

    参数:
    sub_dir -- 可选参数，指定要处理的子目录名称
    """
    # 注册黑体
    register_heiti_font()

    # 定义基础目录
    student_reports_base = "student_reports"
    output_base = "output"
    graded_reports_base = "graded_reports"

    # 根据参数确定要处理的目录
    if sub_dir:
        # 处理特定子目录
        target_dir = os.path.join(student_reports_base, sub_dir)
        if not os.path.exists(target_dir):
            print(f"错误：指定的子目录 '{sub_dir}' 不存在")
            return

        print(f"开始处理子目录: {sub_dir}")
        process_directory(target_dir, student_reports_base, output_base, graded_reports_base)
    else:
        # 处理所有子目录
        print("开始处理所有学生报告...")
        for root, dirs, files in os.walk(student_reports_base):
            # 跳过根目录本身
            if root == student_reports_base:
                for dir_name in dirs:
                    target_dir = os.path.join(root, dir_name)
                    print(f"\n处理子目录: {dir_name}")
                    process_directory(target_dir, student_reports_base, output_base, graded_reports_base)
        print("\n所有报告处理完成！")


def process_directory(target_dir, student_reports_base, output_base, graded_reports_base, specific_file=None):
    """
    处理指定目录中的文件
    
    参数:
    specific_file -- 如果指定，则只处理这个特定的文件
    """
    # 获取相对路径（保留原始子目录结构）
    rel_path = os.path.relpath(target_dir, student_reports_base)

    # 确定要处理的文件列表
    if specific_file:
        files_to_process = [specific_file] if os.path.exists(os.path.join(target_dir, specific_file)) else []
    else:
        files_to_process = os.listdir(target_dir)

    # 遍历要处理的文件
    for filename in files_to_process:
        file_path = os.path.join(target_dir, filename)

        if not os.path.isfile(file_path):
            continue

        file_ext = os.path.splitext(filename)[1].lower()

        # 只处理支持的格式
        if file_ext not in ['.pdf', '.docx', '.doc']:
            print(f"  跳过: 不支持的文件类型 {file_ext} ({filename})")
            continue

        # 构建JSON文件路径
        json_filename = os.path.splitext(filename)[0] + '.json'
        json_path = os.path.join(output_base, rel_path, json_filename)

        # 构建输出文件路径 - 统一输出为PDF格式
        output_dir = os.path.join(graded_reports_base, rel_path)
        output_filename = os.path.splitext(filename)[0] + '.pdf'
        output_path = os.path.join(output_dir, output_filename)

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        print(f"  处理文件: {filename}")

        # 检查JSON文件是否存在
        if not os.path.exists(json_path):
            print(f"    警告：未找到对应的JSON文件 {json_filename}",json_path)
            continue

        try:
            # 读取JSON数据
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            score = data.get('score', 'N/A')
            comments = data.get('comments', '')

            # 根据文件类型处理
            if file_ext == '.pdf':
                process_pdf(file_path, output_path, score, comments)
            elif file_ext in ['.docx', '.doc']:
                # 先将Word转换为PDF
                temp_pdf_path = os.path.join(output_dir, os.path.splitext(filename)[0] + '_temp.pdf')
                if convert_word_to_pdf(file_path, temp_pdf_path):
                    # 处理转换后的PDF
                    process_pdf(temp_pdf_path, output_path, score, comments)
                    # 删除临时文件
                    try:
                        os.remove(temp_pdf_path)
                    except:
                        pass
                else:
                    print(f"    Word转PDF失败: {filename}")
                    continue

            print(f"    完成: {output_filename}")

        except Exception as e:
            print(f"    处理出错: {str(e)}")
            import traceback
            traceback.print_exc()


def register_heiti_font():
    """注册黑体字体，优先使用黑体"""
    try:
        # 检查是否已注册
        if 'HeiTi' in pdfmetrics.getRegisteredFontNames():
            return True
            
        # 尝试多种常见黑体路径
        font_paths = [
            'C:/Windows/Fonts/simhei.ttf',  # Windows 黑体
            'C:/Windows/Fonts/msyh.ttf',  # Windows 微软雅黑
            'C:/Windows/Fonts/msyhbd.ttf',  # Windows 微软雅黑粗体
            'C:/Windows/Fonts/simfang.ttf',  # Windows 仿宋
            'C:/Windows/Fonts/simkai.ttf',  # Windows 楷体
            '/System/Library/Fonts/PingFang.ttc',  # macOS 苹方
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',  # Linux 文泉驿微米黑
            'simhei.ttf',  # 当前目录黑体
            'msyh.ttf'    # 当前目录微软雅黑
        ]

        # 尝试注册每种字体
        for path in font_paths:
            try:
                if os.path.exists(path):
                    try:
                        # 尝试注册为HeiTi
                        pdfmetrics.registerFont(TTFont('HeiTi', path))
                        print(f"成功注册中文字体: {path} 为 HeiTi")
                        return True
                    except Exception as e:
                        print(f"注册 {path} 为 HeiTi 失败: {str(e)}")
                        continue
            except Exception as e:
                print(f"检查字体路径 {path} 时出错: {str(e)}")
                continue

        print("错误：未能找到可用的中文字体文件")
        return False
    except Exception as e:
        print(f"字体注册过程中发生严重错误: {str(e)}")
        return False


def process_pdf(input_path, output_path, score, comments):
    """处理PDF文件，添加分数和评语"""
    try:
        # 读取原始PDF
        reader = PdfReader(input_path)
        writer = PdfWriter()

        # 检查对号图片是否存在
        checkmark_path = "check_right.png"
        if not os.path.exists(checkmark_path):
            print("    警告：未找到对号图片(check_right.png)，将不添加对号标记")
            checkmark = None
        else:
            try:
                # 打开并调整对号图片大小
                img = Image.open(checkmark_path)
                img_width, img_height = img.size
                # 调整图片大小为合适尺寸
                target_width = 2 * cm
                target_height = target_width * img_height / img_width
                checkmark = (checkmark_path, target_width, target_height)
            except Exception as e:
                print(f"    无法加载对号图片: {str(e)}")
                checkmark = None

        # 处理每一页
        for i, page in enumerate(reader.pages):
            processed_page = page

            # 添加对号图片到页面
            if checkmark:
                processed_page = add_checkmark_to_page(page, checkmark, i + 1, len(reader.pages))

            # 只在第一页添加分数
            if i == 0:
                score_page = create_pdf_score_page(score, processed_page)
                if score_page:
                    processed_page.merge_page(score_page)

            writer.add_page(processed_page)

        # 添加评论页面（如果存在评语）
        if comments.strip():
            comment_pages = create_pdf_comment_pages(comments, reader.pages[0] if reader.pages else None)
            for page in comment_pages:
                # 为评语页也添加对号
                if checkmark:
                    page = add_checkmark_to_page(page, checkmark, len(writer.pages) + 1,
                                                 len(writer.pages) + len(comment_pages))
                writer.add_page(page)

        # 保存结果
        with open(output_path, "wb") as f:
            writer.write(f)
    except Exception as e:
        print(f"    处理PDF时出错: {str(e)}")
        # 尝试使用备选方法处理PDF
        alternative_pdf_process(input_path, output_path, score, comments)


def add_checkmark_to_page(page, checkmark, page_num, total_pages):
    """在页面的居中位置添加占页面三分之一高度的对号图片"""
    try:
        # 如果是最后一页(评语页)，不添加对号图片
        if page_num == total_pages:
            return page

        checkmark_path, _, _ = checkmark  # 不再使用原尺寸

        # 获取页面尺寸
        try:
            page_width = float(page.mediabox[2])
            page_height = float(page.mediabox[3])
        except:
            page_width, page_height = letter
            page_width = float(page_width)
            page_height = float(page_height)

        # 创建一个新的PDF页用于放置对号图片
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(page_width, page_height))

        # 计算对号图片的大小 - 页面高度的三分之一
        target_height = page_height / 3
        # 保持图片原比例
        img = Image.open(checkmark_path)
        img_width, img_height = img.size
        aspect_ratio = img_width / img_height
        target_width = target_height * aspect_ratio

        # 计算居中位置
        x_position = (page_width - target_width) / 2
        y_position = (page_height - target_height) / 2

        # 绘制对号图片
        can.drawImage(checkmark_path, x_position, y_position, width=target_width, height=target_height, mask='auto')

        can.save()

        # 将对号图片页合并到原始页面
        packet.seek(0)
        checkmark_page = PdfReader(packet).pages[0]
        page.merge_page(checkmark_page)

        return page
    except Exception as e:
        print(f"    添加对号图片时出错: {str(e)}")
        return page

def alternative_pdf_process(input_path, output_path, score, comments):
    """备用的PDF处理方法，用于处理特殊PDF"""
    print("    尝试备用的PDF处理方法...")
    try:
        # 创建一个新的PDF作为封面
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)

        # 添加分数
        can.setFont("Helvetica-Bold", 28)
        can.setFillColorRGB(0.8, 0.1, 0.1)
        text = f"分数: {score}"
        text_width = can.stringWidth(text, "Helvetica-Bold", 28)
        page_width, page_height = letter
        x = page_width - text_width - 1.5 * cm
        y = page_height - 1.5 * cm

        # 添加背景框
        can.setFillColorRGB(1, 1, 0.9)
        can.rect(x - 0.3 * cm, y - 0.3 * cm,
                 text_width + 0.6 * cm, 1.2 * cm,
                 fill=1, stroke=0)

        # 添加边框
        can.setStrokeColorRGB(0.8, 0.1, 0.1)
        can.setLineWidth(1.5)
        can.rect(x - 0.3 * cm, y - 0.3 * cm,
                 text_width + 0.6 * cm, 1.2 * cm,
                 fill=0, stroke=1)

        # 绘制分数
        can.setFillColorRGB(0.8, 0.1, 0.1)
        can.drawString(x, y, text)
        can.save()

        # 将封面与原始PDF合并
        packet.seek(0)
        cover = PdfReader(packet).pages[0]

        reader = PdfReader(input_path)
        writer = PdfWriter()

        # 添加封面
        writer.add_page(cover)

        # 添加原始PDF的所有页面
        for i, page in enumerate(reader.pages):
            # 为原始PDF的每一页添加对号
            checkmark_path = "check_right.png"
            if os.path.exists(checkmark_path):
                try:
                    img = Image.open(checkmark_path)
                    img_width, img_height = img.size
                    target_width = 2 * cm
                    target_height = target_width * img_height / img_width
                    page = add_checkmark_to_page(page, (checkmark_path, target_width, target_height), i + 2,
                                                 len(reader.pages) + 2)
                except:
                    pass
            writer.add_page(page)

        # 添加评语
        if comments.strip():
            comment_pages = create_pdf_comment_pages(comments, None)
            for i, page in enumerate(comment_pages):
                # 为评语页添加对号
                checkmark_path = "check_right.png"
                if os.path.exists(checkmark_path):
                    try:
                        img = Image.open(checkmark_path)
                        img_width, img_height = img.size
                        target_width = 2 * cm
                        target_height = target_width * img_height / img_width
                        page_num = len(reader.pages) + 2 + i
                        total_pages = len(reader.pages) + 2 + len(comment_pages)
                        page = add_checkmark_to_page(page, (checkmark_path, target_width, target_height), page_num,
                                                     total_pages)
                    except:
                        pass
                writer.add_page(page)

        # 保存结果
        with open(output_path, "wb") as f:
            writer.write(f)

        print("    备用方法处理成功")
    except Exception as e:
        print(f"    备用方法处理失败: {str(e)}")
        raise


def create_pdf_score_page(score, orig_page):
    """创建PDF分数水印页"""
    try:
        # 获取原始页面尺寸并转换为浮点数
        try:
            page_width = float(orig_page.mediabox.width)
            page_height = float(orig_page.mediabox.height)
        except:
            # 默认使用letter尺寸，并转换为浮点数
            page_width, page_height = letter
            page_width = float(page_width)
            page_height = float(page_height)

        # 创建分数水印
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(page_width, page_height))

        # 设置分数文本样式
        can.setFont("Helvetica-Bold", 28)
        can.setFillColorRGB(0.8, 0.1, 0.1)  # 深红色

        # 右上角位置 (距离右边1.5厘米，上边1.5厘米)
        text = f"{score}"
        text_width = can.stringWidth(text, "Helvetica-Bold", 34)
        x = page_width - text_width - 1.5 * cm
        y = page_height - 1.5 * cm

        # # 添加背景框
        # can.setFillColorRGB(1, 1, 0.9)  # 浅黄色背景
        # can.rect(x - 0.3 * cm, y - 0.3 * cm,
        #          text_width + 0.6 * cm, 1.2 * cm,
        #          fill=1, stroke=0)
        #
        # # 添加边框
        # can.setStrokeColorRGB(0.8, 0.1, 0.1)
        # can.setLineWidth(1.5)
        # can.rect(x - 0.3 * cm, y - 0.3 * cm,
        #          text_width + 0.6 * cm, 1.2 * cm,
        #          fill=0, stroke=1)

        # 绘制分数
        can.setFillColorRGB(0.8, 0.1, 0.1)  # 恢复红色
        can.drawString(x, y, text)
        can.save()

        # 返回水印页面
        packet.seek(0)
        return PdfReader(packet).pages[0]
    except Exception as e:
        print(f"    创建分数页时出错: {str(e)}")
        return None


def create_pdf_comment_pages(comments, orig_page):
    """创建PDF评语页面，使用黑体"""
    try:
        # 获取原始页面尺寸并转换为浮点数
        if orig_page:
            try:
                page_width = float(orig_page.mediabox.width)
                page_height = float(orig_page.mediabox.height)
            except:
                page_width, page_height = letter
                page_width = float(page_width)
                page_height = float(page_height)
        else:
            page_width, page_height = letter
            page_width = float(page_width)
            page_height = float(page_height)

        # 创建评论PDF
        packet = io.BytesIO()
        doc = SimpleDocTemplate(packet, pagesize=(page_width, page_height))

        # 创建样式
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontName='HeiTi' if 'HeiTi' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Bold',
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=14,
            textColor=colors.red  # 设置字体颜色为红色
        )

        # 创建评语样式 - 使用黑体
        comment_style = ParagraphStyle(
            'CommentStyle',
            parent=styles['Normal'],
            fontName='HeiTi' if 'HeiTi' in pdfmetrics.getRegisteredFontNames() else 'Helvetica',
            fontSize=12,
            leading=16,
            spaceBefore=6,
            spaceAfter=6,
            alignment=TA_JUSTIFY
        )

        # 构建内容
        content = []

        # 添加标题 - 使用黑体
        content.append(Paragraph("教师评语", title_style))
        content.append(Spacer(1, 0.2 * cm))

        # 添加分隔线
        content.append(Paragraph("<hr/>", styles['Normal']))
        content.append(Spacer(1, 0.5 * cm))

        # 添加评语内容 - 使用黑体
        paragraphs = [p.strip() for p in comments.split('\n') if p.strip()]
        for para in paragraphs:
            content.append(Paragraph(para, comment_style))
            content.append(Spacer(1, 0.2 * cm))

        # 生成PDF
        doc.build(content)

        # 获取所有评论页面
        packet.seek(0)
        comment_pdf = PdfReader(packet)
        return comment_pdf.pages
    except Exception as e:
        print(f"    创建评语页时出错: {str(e)}")
        return []


def convert_word_to_pdf(word_path, pdf_path):
    """将Word文档转换为PDF格式"""
    try:
        pythoncom.CoInitialize()

        # 创建Word应用实例
        word = comtypes.client.CreateObject("Word.Application")
        word.Visible = False

        # 打开Word文件
        doc = word.Documents.Open(os.path.abspath(word_path))

        # 另存为PDF
        doc.SaveAs(os.path.abspath(pdf_path), FileFormat=17)  # 17 = wdFormatPDF

        # 关闭文档和Word应用
        doc.Close()
        word.Quit()

        return True
    except Exception as e:
        print(f"    Word转PDF失败: {str(e)}")
        return False
    finally:
        pythoncom.CoUninitialize()


# def generate_graded_pdf(input_pdf_path, output_pdf_path, score, comments):
#     """
#     生成评阅版PDF文件
#
#     参数:
#     input_pdf_path -- 原始PDF文件路径
#     output_pdf_path -- 输出PDF文件路径
#     score -- 分数
#     comments -- 评语内容
#     """
#     try:
#         # 确保输出目录存在
#         os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
#
#         # 直接处理单个PDF文件
#         process_pdf(input_pdf_path, output_pdf_path, score, comments)
#         print(f"成功生成评阅版PDF: {output_pdf_path}")
#         return True
#     except Exception as e:
#         print(f"生成评阅版PDF失败: {str(e)}")
#         return False

if __name__ == "__main__":
    # 确保输出目录存在
    os.makedirs("graded_reports", exist_ok=True)

    # 解析命令行参数
    import argparse

    parser = argparse.ArgumentParser(description='处理学生报告并添加评分')
    parser.add_argument('--sub-dir', type=str, help='指定要处理的子目录名称', default=None)
    args = parser.parse_args()

    sub_dir = "内蒙古民族大学-电子22级-c++程序设计-6班-实验五科学计算器的实现"
    # 调用主函数
    grade_student_reports(sub_dir)
    print("\n处理完成！")