import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib import colors

def register_chinese_fonts():
    """注册中文字体，返回是否成功"""
    try:
        # 检查是否已注册
        if 'HeiTi' in pdfmetrics.getRegisteredFontNames():
            return True

        # 尝试多种常见中文字体路径
        font_paths = [
            'C:/Windows/Fonts/simhei.ttf',  # Windows 黑体
            'C:/Windows/Fonts/msyh.ttf',   # Windows 微软雅黑
            'C:/Windows/Fonts/simfang.ttf', # Windows 仿宋
            'C:/Windows/Fonts/simkai.ttf',  # Windows 楷体
            '/System/Library/Fonts/PingFang.ttc',  # macOS 苹方
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',  # Linux 文泉驿微米黑
            'simhei.ttf',  # 当前目录黑体
            'msyh.ttf'     # 当前目录微软雅黑
        ]

        # 尝试注册每种字体
        for path in font_paths:
            try:
                if os.path.exists(path):
                    try:
                        # 尝试注册为HeiTi
                        pdfmetrics.registerFont(TTFont('HeiTi', path))
                        print(f"成功注册中文字体: {path} 为 HeiTi")
                        # 同时注册为其他常用名称
                        pdfmetrics.registerFont(TTFont('SimHei', path))
                        pdfmetrics.registerFont(TTFont('MicrosoftYaHei', path))
                        return True
                    except Exception as e:
                        print(f"注册 {path} 失败: {str(e)}")
                        continue
            except Exception as e:
                print(f"检查字体路径 {path} 时出错: {str(e)}")
                continue

        print("错误：未能找到可用的中文字体文件")
        return False
    except Exception as e:
        print(f"字体注册过程中发生严重错误: {str(e)}")
        return False

def create_chinese_pdf(output_path, title, content):
    """
    创建包含中文内容的PDF文件

    参数:
    output_path -- 输出PDF文件路径
    title -- 标题文本
    content -- 正文内容(可以包含多段，用换行符分隔)
    """
    try:
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 注册中文字体
        if not register_chinese_fonts():
            raise Exception("无法加载中文字体")

        # 创建样式
        styles = getSampleStyleSheet()

        # 标题样式 - 使用黑体
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontName='HeiTi',
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=14,
            textColor=colors.red
        )

        # 正文样式 - 使用黑体
        content_style = ParagraphStyle(
            'ContentStyle',
            parent=styles['Normal'],
            fontName='HeiTi',
            fontSize=12,
            leading=16,
            spaceBefore=6,
            spaceAfter=6,
            alignment=TA_JUSTIFY
        )

        # 构建PDF内容
        story = []

        # 添加标题
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 12))

        # 添加内容(按段落)
        paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
        for para in paragraphs:
            story.append(Paragraph(para, content_style))
            story.append(Spacer(1, 6))

        # 生成PDF
        doc = SimpleDocTemplate(output_path)
        doc.build(story)

        print(f"成功生成中文PDF: {output_path}")
        return True

    except Exception as e:
        print(f"生成中文PDF失败: {str(e)}")
        return False

if __name__ == "__main__":
    # 测试中文PDF生成
    test_output = "test_chinese.pdf"
    test_title = "中文测试文档"
    test_content = """这是第一段中文内容，用于测试PDF生成功能。
    
这是第二段中文内容，检查是否能够正确处理多段落文本。
    
最后一段，验证所有功能是否正常工作。"""

    create_chinese_pdf(test_output, test_title, test_content)
