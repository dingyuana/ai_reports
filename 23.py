import os
import json
import io
import sys
import decimal
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib import colors
import comtypes.client
import pythoncom
import math
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


def process_directory(target_dir, student_reports_base, output_base, graded_reports_base):
    """处理指定目录中的所有文件"""
    # 获取相对路径（保留原始子目录结构）
    rel_path = os.path.relpath(target_dir, student_reports_base)

    # 遍历目录中的文件
    for filename in os.listdir(target_dir):
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
        output_filename = os.path.splitext(filename)[0] + '_graded.pdf'
        output_path = os.path.join(output_dir, output_filename)

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        print(f"  处理文件: {filename}")

        # 检查JSON文件是否存在
        if not os.path.exists(json_path):
            print(f"    警告：未找到对应的JSON文件 {json_filename}")
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
        # 尝试多种常见黑体路径
        font_paths = [
            'C:/Windows/Fonts/simhei.ttf',  # Windows 黑体
            'C:/Windows/Fonts/msyh.ttf',  # Windows 微软雅黑
            'C:/Windows/Fonts/msyhbd.ttf',  # Windows 微软雅黑粗体
            '/System/Library/Fonts/PingFang.ttc',  # macOS 苹方
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',  # Linux 文泉驿微米黑
            'simhei.ttf'  # 当前目录黑体
        ]

        font_registered = False

        for path in font_paths:
            try:
                if os.path.exists(path):
                    # 尝试注册黑体
                    try:
                        pdfmetrics.registerFont(TTFont('HeiTi', path))
                        print(f"成功加载黑体: {path}")
                        font_registered = True
                        break
                    except:
                        # 有些字体文件包含多种字体，尝试特定名称
                        if 'simhei' in path.lower():
                            try:
                                pdfmetrics.registerFont(TTFont('HeiTi', path))
                                print(f"成功加载黑体: {path}")
                                font_registered = True
                                break
                            except:
                                continue
                        elif 'msyh' in path.lower():
                            try:
                                pdfmetrics.registerFont(TTFont('HeiTi', path))
                                print(f"成功加载微软雅黑: {path}")
                                font_registered = True
                                break
                            except:
                                continue
            except Exception as e:
                print(f"尝试路径 {path} 时出错: {str(e)}")
                continue

        if not font_registered:
            print("警告：未找到可用的黑体文件，将使用默认字体")
    except Exception as e:
        print(f"字体加载过程中发生错误: {str(e)}")


def process_pdf(input_path, output_path, score, comments):
    """处理PDF文件，添加分数和评语"""
    try:
        # 首先检查文件是否存在
        if not os.path.exists(input_path):
            print(f"    错误：文件 {input_path} 不存在")
            raise FileNotFoundError(f"文件 {input_path} 不存在")

        # 检查文件大小是否为0
        if os.path.getsize(input_path) == 0:
            print(f"    错误：文件 {input_path} 是空文件")
            raise ValueError("空PDF文件")

        # 读取原始PDF
        try:
            # 尝试使用更安全的PDF读取方式
            with open(input_path, 'rb') as f:
                reader = PdfReader(f)
                
                # 验证PDF结构
                if not hasattr(reader, 'pages') or len(reader.pages) == 0:
                    print(f"    警告：PDF文件 {input_path} 没有有效页面")
                    raise ValueError("PDF文件没有有效页面")
                    
                # 尝试访问第一页以验证PDF完整性
                _ = reader.pages[0].mediabox
                
        except Exception as pdf_error:
            print(f"    读取PDF文件 {input_path} 时出错: {str(pdf_error)}")
            print("    尝试使用备选方法处理...")
            # 直接使用备选方法处理PDF
            alternative_pdf_process(input_path, output_path, score, comments)
            return

        writer = PdfWriter()

        # 添加分数到第一页
        try:
            first_page = reader.pages[0]

            # 添加对号图片水印
            try:
                checkmark_page = create_image_watermark(first_page)
                if checkmark_page:
                    first_page.merge_page(checkmark_page)
            except Exception as watermark_error:
                print(f"    添加水印时出错: {str(watermark_error)}")
                # 继续处理，不添加水印

            # 添加分数
            try:
                score_page = create_pdf_score_page(score, first_page)
                if score_page:
                    first_page.merge_page(score_page)
            except Exception as score_error:
                print(f"    添加分数时出错: {str(score_error)}")
                # 继续处理，不添加分数

            writer.add_page(first_page)
        except Exception as first_page_error:
            print(f"    处理第一页时出错: {str(first_page_error)}")
            # 如果处理第一页失败，尝试使用备选方法
            alternative_pdf_process(input_path, output_path, score, comments)
            return

        # 添加剩余页面
        try:
            for i in range(1, len(reader.pages)):
                try:
                    page = reader.pages[i]

                    # 添加对号图片水印
                    try:
                        checkmark_page = create_image_watermark(page)
                        if checkmark_page:
                            page.merge_page(checkmark_page)
                    except Exception as watermark_error:
                        print(f"    添加水印到第{i+1}页时出错: {str(watermark_error)}")
                        # 继续处理，不添加水印

                    writer.add_page(page)
                except Exception as page_error:
                    print(f"    处理第{i+1}页时出错: {str(page_error)}")
                    # 跳过这一页，继续处理其他页面
                    continue
        except Exception as pages_error:
            print(f"    处理剩余页面时出错: {str(pages_error)}")
            # 继续处理，尝试添加评语页面

        # 添加评论页面（如果存在评语）
        if comments.strip():
            try:
                comment_pages = create_pdf_comment_pages(comments, reader.pages[0] if reader.pages else None)
                for page in comment_pages:
                    # 添加对号图片水印
                    try:
                        checkmark_page = create_image_watermark(page)
                        if checkmark_page:
                            page.merge_page(checkmark_page)
                    except Exception as watermark_error:
                        print(f"    添加水印到评语页时出错: {str(watermark_error)}")
                        # 继续处理，不添加水印

                    writer.add_page(page)
            except Exception as comments_error:
                print(f"    添加评语页时出错: {str(comments_error)}")
                # 继续处理，不添加评语页面

        # 保存结果
        try:
            with open(output_path, "wb") as f:
                writer.write(f)
            print(f"    成功保存处理后的PDF到 {output_path}")
        except Exception as save_error:
            print(f"    保存PDF时出错: {str(save_error)}")
            # 尝试使用备选方法处理PDF
            alternative_pdf_process(input_path, output_path, score, comments)
    except Exception as e:
        print(f"    处理PDF时出错: {str(e)}")
        # 尝试使用备选方法处理PDF
        alternative_pdf_process(input_path, output_path, score, comments)


def create_image_watermark(orig_page):
    """创建图片水印页（每个页面添加一个大对号图片）"""
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

        # 创建水印
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(page_width, page_height))

        # 检查图片是否存在
        image_path = "check_right.png"
        if not os.path.exists(image_path):
            print(f"    警告：对号图片 {image_path} 不存在")
            return None

        # 读取图片
        img = ImageReader(image_path)
        img_width, img_height = img.getSize()

        # 计算图片大小 - 占据页面的1/3
        target_width = min(page_width, page_height) * 0.33
        target_height = target_width * (img_height / img_width)

        # 计算图片位置 - 页面中心
        x = (page_width - target_width) / 2
        y = (page_height - target_height) / 2

        # 设置透明度 (0.1 = 10% 透明度)
        can.setFillAlpha(0.9)
        can.setStrokeAlpha(0.9)

        # 绘制图片
        can.drawImage(img, x, y, width=target_width, height=target_height, mask='auto')

        # 保存
        can.save()

        # 返回水印页面
        packet.seek(0)
        return PdfReader(packet).pages[0]
    except Exception as e:
        print(f"    创建图片水印时出错: {str(e)}")
        return None


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
        text_width = float(can.stringWidth(text, "Helvetica-Bold", 28))
        page_width, page_height = letter
        page_width = float(page_width)
        page_height = float(page_height)
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

        # 添加对号图片水印
        try:
            image_path = "check_right.png"
            if os.path.exists(image_path):
                img = ImageReader(image_path)
                img_width, img_height = img.getSize()
                target_width = min(page_width, page_height) * 0.33
                target_height = target_width * (img_height / img_width)
                x_img = (page_width - target_width) / 2
                y_img = (page_height - target_height) / 2
                can.setFillAlpha(0.8)
                can.setStrokeAlpha(0.8)
                can.drawImage(img, x_img, y_img, width=target_width, height=target_height, mask='auto')
        except Exception as img_error:
            print(f"    添加对号图片水印时出错: {str(img_error)}")
            # 继续处理，不添加水印

        can.save()

        # 将封面与原始PDF合并
        packet.seek(0)
        cover = PdfReader(packet).pages[0]

        writer = PdfWriter()

        # 添加封面
        writer.add_page(cover)

        # 尝试添加原始PDF的所有页面
        try:
            reader = PdfReader(input_path)
            
            # 添加原始PDF的所有页面
            for i, page in enumerate(reader.pages):
                try:
                    # 添加对号图片水印
                    try:
                        watermark = create_image_watermark(page)
                        if watermark:
                            page.merge_page(watermark)
                    except Exception as watermark_error:
                        print(f"    备用方法：添加水印到第{i+1}页时出错: {str(watermark_error)}")
                        # 继续处理，不添加水印
                    
                    writer.add_page(page)
                except Exception as page_error:
                    print(f"    备用方法：处理第{i+1}页时出错: {str(page_error)}")
                    # 跳过这一页，继续处理其他页面
                    continue
        except Exception as pdf_error:
            print(f"    备用方法：读取原始PDF时出错: {str(pdf_error)}")
            # 继续处理，只保留封面和评语页面

        # 添加评语
        if comments.strip():
            try:
                comment_pages = create_pdf_comment_pages(comments, None)
                for i, page in enumerate(comment_pages):
                    try:
                        # 添加对号图片水印
                        try:
                            watermark = create_image_watermark(page)
                            if watermark:
                                page.merge_page(watermark)
                        except Exception as watermark_error:
                            print(f"    备用方法：添加水印到评语页{i+1}时出错: {str(watermark_error)}")
                            # 继续处理，不添加水印
                        
                        writer.add_page(page)
                    except Exception as page_error:
                        print(f"    备用方法：处理评语页{i+1}时出错: {str(page_error)}")
                        # 跳过这一页，继续处理其他页面
                        continue
            except Exception as comments_error:
                print(f"    备用方法：创建评语页时出错: {str(comments_error)}")
                # 继续处理，不添加评语页面

        # 保存结果
        try:
            with open(output_path, "wb") as f:
                writer.write(f)
            print("    备用方法处理成功")
        except Exception as save_error:
            print(f"    备用方法：保存PDF时出错: {str(save_error)}")
            
            # 最后的尝试：创建一个只包含封面的PDF
            try:
                print("    尝试创建只包含封面的PDF...")
                simple_writer = PdfWriter()
                simple_writer.add_page(cover)
                
                with open(output_path, "wb") as f:
                    simple_writer.write(f)
                print("    成功创建只包含封面的PDF")
            except Exception as final_error:
                print(f"    创建只包含封面的PDF也失败了: {str(final_error)}")
                raise
    except Exception as e:
        print(f"    备用方法处理失败: {str(e)}")
        # 创建一个错误报告文件
        try:
            error_output_path = output_path.replace(".pdf", "_error.txt")
            with open(error_output_path, "w", encoding="utf-8") as f:
                f.write(f"处理PDF文件时出错: {str(e)}\n")
                f.write(f"原始文件: {input_path}\n")
                f.write(f"分数: {score}\n")
                f.write(f"评语: {comments}\n")
            print(f"    已创建错误报告文件: {error_output_path}")
        except:
            print("    创建错误报告文件也失败了")


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
        can.setFont("Helvetica-Bold", 36)
        can.setFillColorRGB(0.8, 0.1, 0.1)  # 深红色

        # 右上角位置 (距离右边1.5厘米，上边1.5厘米)
        text = f"分数: {score}"
        text_width = can.stringWidth(text, "Helvetica-Bold", 28)
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
            alignment=TA_JUSTIFY,
            textColor=colors.red  # 确保评语内容为黑色
        )

        # 构建内容
        content = []

        # 添加标题 - 使用黑体（红色）
        content.append(Paragraph("教师评语", title_style))
        content.append(Spacer(1, 0.2 * cm))

        # 添加分隔线（红色）
        hr_style = ParagraphStyle(
            'HrStyle',
            parent=styles['Normal'],
            textColor=colors.red
        )
        content.append(Paragraph("<hr/>", hr_style))
        content.append(Spacer(1, 0.5 * cm))

        # 添加评语内容 - 使用黑体（黑色）
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


if __name__ == "__main__":
    # 确保输出目录存在
    os.makedirs("graded_reports", exist_ok=True)

    # 解析命令行参数
    import argparse

    parser = argparse.ArgumentParser(description='处理学生报告并添加评分')
    parser.add_argument('--sub-dir', type=str, help='指定要处理的子目录名称', default=None)
    args = parser.parse_args()

    # 调用主函数
    grade_student_reports(args.sub_dir)
    print("\n处理完成！")