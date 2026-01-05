from typing import Optional, Dict, Any
from database import get_db_cursor

class ConfigManager:
    def __init__(self):
        self.default_criteria = """
请依据以下评分标准对学生提交的大学实训报告进行客观、公正的批阅打分。

评分标准
总分100分，实际得分范围要在指定分数之间。评分需兼顾标准要求与分数正态分布特性，避免集中出现逢五、逢十的整数分数。

1. 内容完整性（34分）
- 核心要素齐全（21分）：报告需完整包含实验目的、实验原理、实验步骤、实验结果、实验分析与总结等必要核心部分。
- 过程描述清晰（13分）：实验过程文字描述逻辑连贯、条理清晰，能准确反映实验操作的先后顺序和关键细节。

2. 格式规范性（23分）
- 文档格式规范（23分）：报告标题、目录、正文段落、字体字号、行间距、页码等格式需完全符合实训报告统一要求。

3. 内容相关性（26分）
- 主题贴合紧密（14分）：报告正文内容与本次实训实验主题高度相关，无偏离主题的无关内容。
- 结果目的相符（12分）：实验结果能对实验目的进行有效回应，实验结论与实验目的保持一致。
- 不考虑截图，流程图及各种图表的要求

4. 原创性（17分）
- 内容原创无抄袭（11分）：报告的实验分析、总结与反思等核心内容为学生原创，无直接抄袭教材、网络或他人报告的情况。
- 引用成果标注规范（6分）：引用他人理论、数据、观点等成果时，需准确标明出处，引用格式规范。

批阅要求
1. 逐维度对照细则评分，各维度得分汇总为总分，总分需在指定分数范围内。
2. 保证分数正态分布，避免大量报告集中在某一分数段，尽量避免给出逢五、逢十的整数分数。
3. 撰写总评语，不列出具体扣分分数，字数控制在200字左右，明确指出报告的优点与不足，评语具有指导性。
"""

    def get_user_config(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户配置"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, user_id, criteria, min_score, max_score, created_at, updated_at
                    FROM user_configs
                    WHERE user_id = %s
                    """,
                    (user_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    return {
                        'id': result[0],
                        'user_id': result[1],
                        'criteria': result[2],
                        'min_score': result[3],
                        'max_score': result[4],
                        'created_at': result[5],
                        'updated_at': result[6]
                    }
                return None
        except Exception as e:
            print(f"获取用户配置失败: {e}")
            return None

    def get_or_create_user_config(self, user_id: int) -> Dict[str, Any]:
        """获取或创建用户配置"""
        config = self.get_user_config(user_id)
        
        if config:
            return config
        
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO user_configs (user_id, criteria, min_score, max_score)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, user_id, criteria, min_score, max_score, created_at, updated_at
                    """,
                    (user_id, self.default_criteria, 60, 95)
                )
                result = cursor.fetchone()
                
                return {
                    'id': result[0],
                    'user_id': result[1],
                    'criteria': result[2],
                    'min_score': result[3],
                    'max_score': result[4],
                    'created_at': result[5],
                    'updated_at': result[6]
                }
        except Exception as e:
            print(f"创建用户配置失败: {e}")
            return {
                'user_id': user_id,
                'criteria': self.default_criteria,
                'min_score': 60,
                'max_score': 95
            }

    def update_user_config(
        self,
        user_id: int,
        criteria: Optional[str] = None,
        min_score: Optional[int] = None,
        max_score: Optional[int] = None
    ) -> bool:
        """更新用户配置"""
        try:
            with get_db_cursor() as cursor:
                # 首先检查用户配置是否存在
                cursor.execute(
                    "SELECT id FROM user_configs WHERE user_id = %s",
                    (user_id,)
                )
                exists = cursor.fetchone()
                
                if not exists:
                    # 如果不存在，创建新配置
                    cursor.execute(
                        """
                        INSERT INTO user_configs (user_id, criteria, min_score, max_score)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            user_id,
                            criteria if criteria is not None else self.default_criteria,
                            min_score if min_score is not None else 60,
                            max_score if max_score is not None else 95
                        )
                    )
                    return True
                
                # 如果存在，更新配置
                update_fields = []
                params = []
                
                if criteria is not None:
                    update_fields.append("criteria = %s")
                    params.append(criteria)
                
                if min_score is not None:
                    update_fields.append("min_score = %s")
                    params.append(min_score)
                
                if max_score is not None:
                    update_fields.append("max_score = %s")
                    params.append(max_score)
                
                if not update_fields:
                    return False
                
                params.append(user_id)
                
                query = f"""
                    UPDATE user_configs
                    SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """
                
                cursor.execute(query, params)
                return cursor.rowcount > 0
        except Exception as e:
            print(f"更新用户配置失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_criteria_with_score_range(self, user_id: int) -> str:
        """获取包含分数范围的提示词"""
        config = self.get_or_create_user_config(user_id)
        
        criteria = config['criteria']
        min_score = config['min_score']
        max_score = config['max_score']
        
        criteria_with_range = criteria.replace(
            "实际得分范围要在指定分数之间",
            f"实际得分范围要在{min_score}分到{max_score}分之间"
        )
        
        criteria_with_range = criteria_with_range.replace(
            "总分需在指定分数范围内",
            f"总分需在{min_score}分到{max_score}分范围内"
        )
        
        return criteria_with_range

config_manager = ConfigManager()
