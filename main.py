import logging
from config import API_CONFIG, REPORTS_DIR, OUTPUT_DIR, LOG_CONFIG
from grading_system import GradingSystem
from api_server import app as api_app

# 配置日志
logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(__name__)

# 导出FastAPI应用，用于uvicorn启动
report = api_app


def main():
    try:
        # 创建系统实例
        system = GradingSystem(REPORTS_DIR, OUTPUT_DIR, API_CONFIG)

        # 设置批阅标准
        criteria = """
        1. 实验目的明确性 (20分): 学生是否清晰阐述了实验目的?
        2. 实验方法合理性 (20分): 实验步骤是否完整且合理?
        3. 实验数据准确性 (20分): 数据记录是否准确，图表是否清晰?
        4. 数据分析深度 (20分): 是否对实验结果进行了深入分析?
        5. 结论合理性 (20分): 结论是否与实验结果一致，是否有适当的讨论?
        """
        system.set_grading_criteria(criteria)

        # 处理所有报告
        summary_path = system.process_all_reports()

        if summary_path:
            print(f"所有报告处理完成，评分汇总表保存在: {summary_path}")
        else:
            print("未处理任何报告")

    except Exception as e:
        logger.critical(f"系统运行失败: {e}", exc_info=True)
        print(f"系统运行失败: {e}")


if __name__ == "__main__":
    main()    