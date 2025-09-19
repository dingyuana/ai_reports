import os
import json
from pdf_grader import process_pdf, convert_word_to_pdf
from pdf_chinese_helper import register_chinese_fonts

def grade_single_student(student_file_path, output_path=None, score=None, comments=None):
    """
    处理单个学生的报告，添加分数和评语

    参数:
    student_file_path -- 学生报告文件路径
    output_path -- 输出文件路径，如果为None则自动生成
    score -- 分数，如果为None则尝试从JSON文件读取
    comments -- 评语，如果为None则尝试从JSON文件读取

    返回:
    输出文件路径，处理失败则返回None
    """
    try:
        # 注册中文字体
        register_chinese_fonts()

        # 获取文件信息
        file_dir = os.path.dirname(student_file_path)
        filename = os.path.basename(student_file_path)
        file_ext = os.path.splitext(filename)[1].lower()
        file_name_without_ext = os.path.splitext(filename)[0]

        # 只处理支持的格式
        if file_ext not in ['.pdf', '.docx', '.doc']:
            print(f"不支持的文件类型 {file_ext} ({filename})")
            return None

        # 如果未提供输出路径，则自动生成
        if output_path is None:
            output_dir = os.path.join("graded_reports", os.path.basename(file_dir))
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, file_name_without_ext + '.pdf')

        # 如果未提供分数和评语，尝试从JSON文件读取
        if score is None or comments is None:
            json_filename = file_name_without_ext + '.json'
            json_path = os.path.join("output", os.path.basename(file_dir), json_filename)

            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    score = data.get('score', 'N/A') if score is None else score
                    comments = data.get('comments', '') if comments is None else comments
                except Exception as e:
                    print(f"读取JSON文件失败: {str(e)}")
                    if score is None:
                        score = 'N/A'
                    if comments is None:
                        comments = ''
            else:
                print(f"未找到对应的JSON文件: {json_path}")
                if score is None:
                    score = 'N/A'
                if comments is None:
                    comments = ''

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 根据文件类型处理
        if file_ext == '.pdf':
            process_pdf(student_file_path, output_path, score, comments)
            print(f"PDF处理完成: {output_path}")
            return output_path
        elif file_ext in ['.docx', '.doc']:
            # 先将Word转换为PDF
            temp_pdf_path = os.path.join(os.path.dirname(output_path), file_name_without_ext + '_temp.pdf')
            if convert_word_to_pdf(student_file_path, temp_pdf_path):
                # 处理转换后的PDF
                process_pdf(temp_pdf_path, output_path, score, comments)
                # 删除临时文件
                try:
                    os.remove(temp_pdf_path)
                except:
                    pass
                print(f"Word文档处理完成: {output_path}")
                return output_path
            else:
                print(f"Word转PDF失败: {filename}")
                return None

        return None
    except Exception as e:
        print(f"处理学生报告时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # 测试单个学生报告处理
    import sys
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        score = sys.argv[2] if len(sys.argv) > 2 else None
        comments = sys.argv[3] if len(sys.argv) > 3 else None
        grade_single_student(file_path, score=score, comments=comments)
    else:
        print("用法: python grade_single_student.py <文件路径> [分数] [评语]")
