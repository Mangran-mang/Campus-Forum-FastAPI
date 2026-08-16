import json
import logging

from langchain.chat_models import init_chat_model

from config.config import Config

# 独立的审核模型实例：与闲聊版"小柯"完全隔离
# temperature=0 保证审核判定严谨
# qwen3.6-flash 是推理模型，思考会消耗大量 token，max_tokens 需给足（500 会被思考耗尽导致输出截断）
review_model = init_chat_model(
    model="qwen3.5-flash",
    model_provider="openai",
    api_key=Config.API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    temperature=0,
    max_tokens=2048,
)

REVIEW_PROMPT = """你是校园论坛的内容审核员，负责审核帖子是否违规。

违规类型包括：政治敏感、色情低俗、暴力恐怖、广告营销、辱骂攻击、诈骗信息、其他违规。

请严格根据以下帖子内容判断是否违规，只输出 JSON（不要任何其他文字、不要 markdown 代码块）：

{"violated": true/false, "type": "违规类型，未违规则为空字符串", "reason": "简短的中文理由，未违规则说明为何安全"}

帖子标题：__TITLE__
帖子内容：__CONTENT__"""


def build_review_prompt(title: str, content: str) -> str:
    """组装审核 prompt，只包含贴主发布的内容，不包含任何评论"""
    # 用 replace 替换占位符，避免与 JSON 示例中的花括号冲突
    return (
        REVIEW_PROMPT
        .replace("__TITLE__", title or "")
        .replace("__CONTENT__", content or "")
    )


def parse_review_result(raw_text: str) -> dict:
    """
    解析 AI 返回的审核结果
    兼容纯 JSON 和 markdown 代码块包裹两种格式
    解析失败返回默认"未违规"，保证 AI 异常时不影响帖子存活
    """
    text = raw_text.strip()
    # 去掉可能的 ```json ... ``` 包裹
    if text.startswith("```"):
        text = text.strip("`")
        # 去掉可能的 json 前缀
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        result = json.loads(text)
        return {
            "violated": bool(result.get("violated", False)),
            "type": result.get("type", ""),
            "reason": result.get("reason", ""),
        }
    except json.JSONDecodeError:
        logging.exception(f"AI 审核结果解析失败，原文：{raw_text}")
        # 解析失败视为未违规，避免误删
        return {"violated": False, "type": "", "reason": "AI 审核结果解析失败，已按安全处理"}


def review_post_content(title: str, content: str) -> dict:
    """
    审核帖子内容，返回 {"violated": bool, "type": str, "reason": str}
    同步调用：qwen3.6-flash 通常 2-5 秒返回
    调用失败时抛出异常，由调用方决定降级策略
    """
    prompt = build_review_prompt(title, content)
    response = review_model.invoke(prompt)
    return parse_review_result(response.content if hasattr(response, "content") else str(response))
# hasattr：判断参数1有没有参数2这个属性，类似于三元表达式（A if 条件 else B）
