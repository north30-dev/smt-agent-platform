"""LLM 结构化输出 JSON Schema 定义。

供各 Agent 在调用 llm_client.chat() 时传入 json_schema 参数，
强制模型输出符合指定结构的 JSON。
"""


# 设备运维：故障诊断
DIAGNOSE_SCHEMA = {
    "name": "diagnose_result",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "root_causes": {
                "type": "array",
                "description": "根因假设列表，按可能性排序",
                "items": {"type": "string"},
            },
            "repair_suggestions": {
                "type": "array",
                "description": "维修建议列表",
                "items": {"type": "string"},
            },
        },
        "required": ["root_causes", "repair_suggestions"],
        "additionalProperties": False,
    },
}


# 质量分析：根因分析
ROOT_CAUSE_SCHEMA = {
    "name": "root_cause_result",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "root_causes": {
                "type": "array",
                "description": "根因假设列表，按人/机/料/法/环分类",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "五要素分类：人/机/料/法/环",
                        },
                        "cause": {
                            "type": "string",
                            "description": "根因描述",
                        },
                    },
                    "required": ["category", "cause"],
                    "additionalProperties": False,
                },
            },
            "corrective_actions": {
                "type": "array",
                "description": "纠正措施列表",
                "items": {"type": "string"},
            },
        },
        "required": ["root_causes", "corrective_actions"],
        "additionalProperties": False,
    },
}


# 调度智能体：急单响应
URGENT_SCHEMA = {
    "name": "urgent_result",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "changeover_suggestion": {
                "type": "string",
                "description": "换线建议",
            },
            "overtime_suggestion": {
                "type": "string",
                "description": "加班建议",
            },
        },
        "required": ["changeover_suggestion", "overtime_suggestion"],
        "additionalProperties": False,
    },
}


# 执行协同：异常分析
EXCEPTION_ANALYSIS_SCHEMA = {
    "name": "exception_analysis_result",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "root_causes": {
                "type": "array",
                "description": "根因假设列表，按人/机/料/法/环分类",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "五要素分类：人/机/料/法/环",
                        },
                        "cause": {
                            "type": "string",
                            "description": "根因描述",
                        },
                    },
                    "required": ["category", "cause"],
                    "additionalProperties": False,
                },
            },
            "corrective_actions": {
                "type": "array",
                "description": "纠正措施列表",
                "items": {"type": "string"},
            },
            "priority": {
                "type": "string",
                "description": "指令优先级",
                "enum": ["LOW", "MEDIUM", "CRITICAL"],
            },
            "auto_executable": {
                "type": "boolean",
                "description": "是否可自动执行",
            },
        },
        "required": ["root_causes", "corrective_actions", "priority", "auto_executable"],
        "additionalProperties": False,
    },
}
