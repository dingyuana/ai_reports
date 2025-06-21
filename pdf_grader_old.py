import os
import json
import importlib.util
from io import BytesIO
import shutil
import sys
import datetime
import tempfile
import atexit

def create_temp_directory(base_dir):
    """
    创建临时目录并确保在程序退出时清理

    Args:
        base_dir (str): 基础目录路径

    Returns:
        str: 临时目录的路径
    """
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    temp_dir = os.path.join(base_dir, f"temp_{timestamp}")
    os.makedirs(temp_dir, exist_ok=True)

    def cleanup_temp_dir():
        """清理临时目录及其所有内容"""
        if not os.path.exists(temp_dir):
            return

        print(f"开始清理临时目录: {temp_dir}")
        try:
            # 遍历临时目录
            for root, dirs, files in os.walk(temp_dir, topdown=False):
                # 首先删除文件
                for name in files:
                    try:
                        file_path = os.path.join(root, name)
                        os.remove(file_path)
                    except Exception as e:
                        print(f"删除临时文件失败 {file_path}: {str(e)}")

                # 然后删除目录
                for name in dirs:
                    try:
                        dir_path = os.path.join(root, name)
                        os.rmdir(dir_path)
                    except Exception as e:
                        print(f"删除临时目录失败 {dir_path}: {str(e)}")

            # 最后删除临时目录本身
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"已清理临时目录: {temp_dir}")
        except Exception as e:
            print(f"清理临时目录时出错: {str(e)}")
            print("某些临时文件可能未被完全清理")

    # 注册清理函数
    atexit.register(cleanup_temp_dir)
    return temp_dir

# 检查必要的库是否已安装
def check_dependencies():
    missing_libs = []
    required_libs = ["PyPDF2", "reportlab"]

    # 检查是否有Word文档需要处理
    has_word_docs = False
    for root, _, files in os.walk("student_reports"):
        if any(f.lower().endswith(('.doc', '.docx')) for f in files):
            has_word_docs = True
            break

    # 如果有Word文档，添加必要的库
    if has_word_docs:
        required_libs.extend(["docx2pdf", "python-docx"])
    
    for lib in required_libs:
        if importlib.util.find_spec(lib) is None:
            missing_libs.append(lib)
    
    if missing_libs:
        print(f"错误: 缺少必要的库: {', '.join(missing_libs)}")
        print("\n请使用以下命令安装这些库:")
        
        # 特殊处理docx2pdf的安装说明
        if "docx2pdf" in missing_libs:
            print("对于Windows系统:")
            print("1. 首先安装Microsoft Office或LibreOffice")
            print("2. 然后运行: pip install docx2pdf python-docx")
            print("\n对于Linux/Mac系统:")
            print("1. 首先安装LibreOffice")
            print("2. 然后运行: pip install docx2pdf python-docx")
        else:
            print(f"pip install {' '.join(missing_libs)}")

        return False
    return True

# 只有在所有依赖都已安装的情况下才导入
if check_dependencies():
    from PyPDF2 import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.colors import red
    from reportlab.lib.units import inch

    # 如果安装了docx2pdf，则导入
    try:
        from docx2pdf import convert
        DOCX2PDF_AVAILABLE = True
    except ImportError:
        DOCX2PDF_AVAILABLE = False
else:
    # 定义空的占位符类，以避免导入错误
    class PdfReader: pass
    class PdfWriter: pass
    DOCX2PDF_AVAILABLE = False

def process_pdf_file(pdf_path, temp_dir, grade_data):
    """
    处理单个PDF文件，添加分数水印和评语页

    Args:
        pdf_path (str): PDF文件路径
        temp_dir (str): 临时目录路径
        grade_data (dict): 评分数据

    Returns:
        tuple: (PdfWriter对象, 错误信息)
    """
    try:
        # 提取评分信息
        score = grade_data.get("score", 0)
        comments = grade_data.get("comments", "无评语")
        is_qualified = grade_data.get("is_qualified", False)
        reasons = grade_data.get("reasons", [])

        # 生成基本文件名（不包含扩展名）
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]

        # 创建分数水印
        score_watermark_path = os.path.join(temp_dir, f"{base_name}_score_watermark.pdf")
        c = canvas.Canvas(score_watermark_path, pagesize=letter)
        c.setFont("Helvetica-Bold", 24)
        c.setFillColor(red)
        c.drawString(7 * inch, 10 * inch, f"分数: {score}")
        c.save()
        print(f"生成分数水印: {score_watermark_path}")

        # 生成评语页
        comments_page_path = os.path.join(temp_dir, f"{base_name}_comments.pdf")
        c = canvas.Canvas(comments_page_path, pagesize=letter)

        # 添加评语标题
        c.setFont("Helvetica-Bold", 16)
        c.drawString(1 * inch, 10 * inch, "评语:")

        # 添加评语内容
        c.setFont("Helvetica", 12)
        y_position = 9.5 * inch

        # 处理长评语，按行分割
        comment_lines = []
        current_line = ""
        for word in comments.split():
            if len(current_line + " " + word) < 80:  # 每行大约80个字符
                current_line += " " + word if current_line else word
            else:
                comment_lines.append(current_line)
                current_line = word
        if current_line:
            comment_lines.append(current_line)

        # 写入评语
        for line in comment_lines:
            c.drawString(1 * inch, y_position, line)
            y_position -= 0.25 * inch

        # 如果有不合格原因，添加到评语页
        if not is_qualified and reasons:
            y_position -= 0.5 * inch
            c.setFont("Helvetica-Bold", 14)
            c.drawString(1 * inch, y_position, "不合格原因:")
            c.setFont("Helvetica", 12)
            y_position -= 0.25 * inch

            for reason in reasons:
                c.drawString(1 * inch, y_position, f"• {reason}")
                y_position -= 0.25 * inch

        c.save()

        # 读取原始PDF
        original_pdf = PdfReader(pdf_path)
        output_pdf = PdfWriter()

        # 处理第一页，添加分数水印
        score_watermark_pdf = PdfReader(score_watermark_path)
        first_page = original_pdf.pages[0]
        first_page.merge_page(score_watermark_pdf.pages[0])
        output_pdf.add_page(first_page)
        print(f"已添加带水印的首页")

        # 添加剩余的页面
        for i in range(1, len(original_pdf.pages)):
            output_pdf.add_page(original_pdf.pages[i])
        print(f"已添加剩余 {len(original_pdf.pages)-1} 页")

        # 添加评语页
        comments_pdf = PdfReader(comments_page_path)
        output_pdf.add_page(comments_pdf.pages[0])
        print(f"已添加评语页")

        return output_pdf, None

    except Exception as e:
        error_msg = f"处理PDF文件时出错: {str(e)}"
        print(error_msg)
        return None, error_msg

def convert_word_to_pdf(word_path, output_dir=None):
    """
    将Word文档转换为PDF

    Args:
        word_path (str): Word文档路径
        output_dir (str, optional): 输出目录，默认与Word文档相同目录

    Returns:
        str: 转换后的PDF文件路径，如果转换失败则返回None
    """
    if not DOCX2PDF_AVAILABLE:
        print(f"错误: 无法转换Word文档，缺少docx2pdf库")
        print("请安装必要的库:")
        print("1. 确保已安装Microsoft Office或LibreOffice")
        print("2. 运行: pip install docx2pdf python-docx")
        return None

    try:
        # 检查输入文件是否存在
        if not os.path.exists(word_path):
            print(f"错误: Word文档不存在: {word_path}")
            return None

        # 确定输出路径
        if output_dir is None:
            output_dir = os.path.dirname(word_path)

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        base_name = os.path.splitext(os.path.basename(word_path))[0]
        pdf_path = os.path.join(output_dir, f"{base_name}.pdf")

        # 如果输出文件已存在，先删除以避免冲突
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
                print(f"已删除已存在的PDF文件: {pdf_path}")
            except Exception as e:
                print(f"警告: 无法删除已存在的PDF文件: {str(e)}")

        # 转换Word文档为PDF
        print(f"正在将Word文档转换为PDF: {word_path}")
        try:
            convert(word_path, pdf_path)
        except Exception as e:
            print(f"转换过程中出错: {str(e)}")
            print("可能的原因:")
            print("1. Microsoft Office或LibreOffice未正确安装或配置")
            print("2. Word文档可能已损坏或格式不兼容")
            print("3. Word文档可能被其他程序占用")
            return None

        # 检查转换是否成功
        if os.path.exists(pdf_path):
            print(f"转换成功: {pdf_path}")
            return pdf_path
        else:
            print(f"转换失败: 未生成PDF文件")
            return None
    except Exception as e:
        print(f"转换Word文档时出错: {str(e)}")
        print("请确保:")
        print("1. Microsoft Office或LibreOffice已正确安装")
        print("2. Word文档未被其他程序占用")
        print("3. 您有足够的权限访问该文件")
        return None

def generate_graded_reports(source_dir, target_dir, overwrite=True):
    """
    从student_reports指定的子目录下读取每个原始报告，
    与student_reports相同子目录下对应同文件名.json，
    在原始报告首页右上角加上分数，最后面加上评语，
    合并为一个pdf文件后，保存到graded_reports目录下的相同子目录下，
    文件名同原始文件名。支持PDF和Word文档格式。

    Args:
        source_dir (str): 源目录，通常是student_reports下的子目录
        target_dir (str): 目标目录，通常是graded_reports下的子目录
        overwrite (bool): 是否覆盖已存在的文件

    Returns:
        dict: 处理结果统计
    """
    start_time = datetime.datetime.now()
    print(f"开始处理目录: {source_dir}")
    print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    # 检查依赖
    if not check_dependencies():
        return {
            "total": 0,
            "success": 0,
            "failed": 0,
            "processed_files": [],
            "error": "缺少必要的库，请安装PyPDF2和reportlab",
            "start_time": start_time.isoformat(),
            "end_time": datetime.datetime.now().isoformat()
        }
        
    # 确保目标目录存在
    os.makedirs(target_dir, exist_ok=True)
    
    # 创建临时目录
    temp_dir = create_temp_directory(target_dir)
    print(f"创建临时目录: {temp_dir}")

    # 统计信息
    stats = {
        "total": 0,
        "success": 0,
        "failed": 0,
        "processed_files": [],
        "skipped_files": [],
        "start_time": start_time.isoformat(),
        "temp_dir": temp_dir
    }

    # 遍历源目录中的所有文件
    for filename in os.listdir(source_dir):
        # 只处理PDF和Word文件
        if not (filename.lower().endswith('.pdf') or filename.lower().endswith('.doc') or filename.lower().endswith('.docx')):
            continue

        stats["total"] += 1
        file_path = os.path.join(source_dir, filename)
        base_name = os.path.splitext(filename)[0]
        json_path = os.path.join(source_dir, f"{base_name}.json")
        target_file = os.path.join(target_dir, f"{base_name}.pdf")
        
        # 检查目标文件是否已存在
        if os.path.exists(target_file) and not overwrite:
            print(f"跳过已存在的文件: {target_file}")
            stats["skipped_files"].append({
                "file": filename,
                "reason": "文件已存在且未设置覆盖选项"
            })
            continue
            
        # 检查评分JSON文件是否存在
        if not os.path.exists(json_path):
            error_msg = f"评分JSON文件不存在: {json_path}"
            print(error_msg)
            stats["failed"] += 1
            stats["processed_files"].append({
                "file": filename,
                "status": "failed",
                "error": error_msg,
                "time": datetime.datetime.now().isoformat()
            })
            continue
            
        # 读取评分数据
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                grade_data = json.load(f)
        except Exception as e:
            error_msg = f"读取评分JSON文件时出错: {str(e)}"
            print(error_msg)
            stats["failed"] += 1
            stats["processed_files"].append({
                "file": filename,
                "status": "failed",
                "error": error_msg,
                "time": datetime.datetime.now().isoformat()
            })
            continue
            
        # 处理文件
        pdf_path = file_path
        
        # 如果是Word文档，先转换为PDF
        if filename.lower().endswith(('.doc', '.docx')):
            print(f"处理Word文档: {file_path}")
            pdf_path = convert_word_to_pdf(file_path, temp_dir)
            if pdf_path is None:
                error_msg = f"无法将Word文档转换为PDF: {file_path}"
                print(error_msg)
                stats["failed"] += 1
                stats["processed_files"].append({
                    "file": filename,
                    "status": "failed",
                    "error": error_msg,
                    "time": datetime.datetime.now().isoformat()
                })
                continue
        else:
            print(f"处理PDF文件: {file_path}")
            
        # 处理PDF文件，添加分数水印和评语页
        try:
            output_pdf, error = process_pdf_file(pdf_path, temp_dir, grade_data)
            if error or not output_pdf:
                stats["failed"] += 1
                stats["processed_files"].append({
                    "file": filename,
                    "status": "failed",
                    "error": error or "处理PDF文件失败",
                    "time": datetime.datetime.now().isoformat()
                })
                continue
                
            # 保存到目标目录
            output_path = os.path.join(target_dir, f"{base_name}.pdf")  # 确保输出文件是PDF格式
            try:
                with open(output_path, 'wb') as output_file:
                    output_pdf.write(output_file)
                
                # 验证输出文件是否成功创建
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    stats["success"] += 1
                    stats["processed_files"].append({
                        "file": filename,
                        "output": output_path,
                        "status": "success",
                        "score": grade_data.get("score", 0),
                        "is_qualified": grade_data.get("is_qualified", False),
                        "time": datetime.datetime.now().isoformat()
                    })
                    print(f"成功处理: {filename}, 分数: {grade_data.get('score', 0)}, 合格: {grade_data.get('is_qualified', False)}")
                    print(f"已保存到: {output_path}")
                else:
                    raise Exception("输出文件创建失败或为空")
            except Exception as e:
                error_msg = f"保存输出文件时出错: {str(e)}"
                print(error_msg)
                stats["failed"] += 1
                stats["processed_files"].append({
                    "file": filename,
                    "status": "failed",
                    "error": error_msg,
                    "time": datetime.datetime.now().isoformat()
                })
                
        except Exception as e:
            error_msg = f"处理文件时出错: {str(e)}"
            print(error_msg)
            stats["failed"] += 1
            stats["processed_files"].append({
                "file": filename,
                "status": "failed",
                "error": error_msg,
                "time": datetime.datetime.now().isoformat()
            })
    
    # 记录结束时间
    end_time = datetime.datetime.now()
    stats["end_time"] = end_time.isoformat()
    duration = end_time - start_time
    print(f"\n处理完成")
    print(f"总文件数: {stats['total']}")
    print(f"成功处理: {stats['success']}")
    print(f"处理失败: {stats['failed']}")
    print(f"处理时间: {duration}")
    
    return stats

def main():
    """
    主函数，处理指定目录下的报告文件
    """
    # 指定要处理的目录
    source_subdir = "内蒙古民族大学-电子-22级-6班-嵌入图形界面开发-嵌入式图形界面开发实验一"
    
    # 构建完整的源目录和目标目录路径
    source_dir = os.path.join("student_reports", source_subdir)
    target_dir = os.path.join("graded_reports", source_subdir)
    
    # 检查源目录是否存在
    if not os.path.exists(source_dir):
        print(f"错误: 源目录不存在: {source_dir}")
        print("请确保目录结构正确，并且目录名称拼写正确")
        return
    
    print("=== 开始处理报告文件 ===")
    print(f"源目录: {source_dir}")
    print(f"目标目录: {target_dir}")
    
    # 处理报告文件
    try:
        stats = generate_graded_reports(source_dir, target_dir)
        
        # 打印处理结果
        print("\n=== 处理完成 ===")
        print(f"总文件数: {stats['total']}")
        print(f"成功处理: {stats['success']}")
        print(f"处理失败: {stats['failed']}")
        
        if stats.get("error"):
            print(f"\n错误: {stats['error']}")
            
        if stats["processed_files"]:
            print("\n处理的文件:")
            for file_info in stats["processed_files"]:
                status = "成功" if file_info["status"] == "success" else "失败"
                print(f"- {file_info['file']}: {status}")
                if file_info.get("error"):
                    print(f"  错误: {file_info['error']}")
                    
        if stats.get("skipped_files"):
            print("\n跳过的文件:")
            for file_info in stats["skipped_files"]:
                print(f"- {file_info['file']}: {file_info['reason']}")
                
    except Exception as e:
        print(f"\n处理过程中出现错误: {str(e)}")
        print("请检查:")
        print("1. 文件权限是否正确")
        print("2. 磁盘空间是否充足")
        print("3. 所有必要的库是否正确安装")

if __name__ == "__main__":
    main()