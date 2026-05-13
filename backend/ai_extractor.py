"""AI-powered key information extraction from resume text."""

import json
import re

from openai import OpenAI

from config import settings


EXTRACTION_PROMPT = """你是一个专业的简历信息提取助手。请从以下简历文本中提取关键信息，以 JSON 格式返回。

需提取的字段：
- name: 姓名
- phone: 电话号码
- email: 电子邮箱
- address: 地址
- job_intent: 求职意向（⭐加分项）
- expected_salary: 期望薪资（⭐加分项）
- work_years: 工作年限（⭐加分项）
- education: 学历背景（⭐加分项）
- projects: 项目经历列表，每个项目包含 name 和 description（⭐加分项）

规则：
1. 如果某个字段在简历中未找到，请填写 null
2. phone 只保留数字和连字符
3. email 确保格式正确
4. projects 为数组格式

请只返回 JSON，不要包含其他文字。

简历文本：
{resume_text}"""


def extract_with_ai(resume_text: str) -> dict:
    """Use AI model to extract structured information from resume."""
    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": "你是一个专业的简历解析助手，只返回 JSON 格式的数据。"},
            {"role": "user", "content": EXTRACTION_PROMPT.format(resume_text=resume_text[:6000])},
        ],
        temperature=0.1,
        max_tokens=2000,
    )

    content = response.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content[:-3]
    return json.loads(content)


def extract_with_rules(resume_text: str) -> dict:
    """Rule-based fallback extraction when AI is unavailable."""
    result = {
        "name": None,
        "phone": None,
        "email": None,
        "address": None,
        "job_intent": None,
        "expected_salary": None,
        "work_years": None,
        "education": None,
        "projects": [],
    }

    # Email
    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", resume_text)
    if email_match:
        result["email"] = email_match.group()

    # Phone (Chinese mobile: 1xx-xxxx-xxxx)
    phone_match = re.search(r"1[3-9]\d[-]?\d{4}[-]?\d{4}", resume_text)
    if phone_match:
        result["phone"] = phone_match.group()

    # Name: assume first line or line after "姓名"
    name_match = re.search(r"姓\s*名[：:]\s*([^\n]{2,6})", resume_text)
    if name_match:
        result["name"] = name_match.group(1).strip()
    else:
        lines = [l for l in resume_text.splitlines() if l.strip()]
        if lines:
            first = lines[0].strip()
            if 2 <= len(first) <= 6 and not re.search(r"[a-zA-Z@\d]", first):
                result["name"] = first

    # Job intent
    intent_match = re.search(r"(?:求职意向|应聘岗位|期望职位)[：:]\s*([^\n]+)", resume_text)
    if intent_match:
        result["job_intent"] = intent_match.group(1).strip()

    # Expected salary
    salary_match = re.search(r"(?:期望薪资|期望薪水|薪资要求)[：:]\s*([^\n]+)", resume_text)
    if salary_match:
        result["expected_salary"] = salary_match.group(1).strip()

    # Work years
    years_match = re.search(r"(?:工作年限|工作经验)[：:]\s*([^\n]+)", resume_text)
    if years_match:
        result["work_years"] = years_match.group(1).strip()

    # Education
    edu_match = re.search(r"(?:学历|教育背景|毕业院校)[：:]\s*([^\n]+)", resume_text)
    if edu_match:
        result["education"] = edu_match.group(1).strip()

    # Address
    addr_match = re.search(r"(?:地址|居住地|现居)[：:]\s*([^\n]+)", resume_text)
    if addr_match:
        result["address"] = addr_match.group(1).strip()

    # Projects
    project_blocks = re.findall(
        r"(?:项目名称|项目)[：:]\s*([^\n]+)\s*\n(?:项目描述|描述)[：:]\s*([^\n]+)",
        resume_text,
    )
    for name, desc in project_blocks:
        result["projects"].append({"name": name.strip(), "description": desc.strip()})

    return result


def extract_info(resume_text: str) -> dict:
    """Extract key information, preferring AI with rule-based fallback."""
    if settings.openai_api_key:
        try:
            return extract_with_ai(resume_text)
        except Exception:
            pass
    return extract_with_rules(resume_text)
