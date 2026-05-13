"""Resume scoring and job matching module."""

import json
import re
from typing import Optional

from openai import OpenAI

from config import settings


def extract_keywords(job_description: str) -> list[str]:
    """Extract keywords from job description using simple NLP heuristics."""
    # Remove common stop words and split
    stop_words = {
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
        "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
        "没有", "看", "好", "自己", "这", "the", "a", "an", "is", "are",
        "was", "were", "be", "been", "being", "have", "has", "had",
        "do", "does", "did", "will", "would", "could", "should",
        "may", "might", "can", "shall", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "or", "and", "not",
        "this", "that", "it", "as", "we", "our", "you", "your",
    }

    # Extract meaningful tokens (Chinese + English words)
    tokens = re.findall(r"[一-鿿]{2,}|[a-zA-Z]{2,}", job_description.lower())
    meaningful = [t for t in tokens if t.lower() not in stop_words]

    # Count frequency and return top keywords
    freq: dict[str, int] = {}
    for t in meaningful:
        freq[t] = freq.get(t, 0) + 1

    sorted_keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [k for k, _ in sorted_keywords[:20]]


def calculate_similarity(text: str, keywords: list[str]) -> float:
    """Calculate keyword match ratio between resume text and job keywords."""
    if not keywords:
        return 0.0
    text_lower = text.lower()
    matches = sum(1 for kw in keywords if kw.lower() in text_lower)
    return matches / len(keywords)


def match_with_rules(resume_info: dict, job_description: str) -> dict:
    """Rule-based matching between resume and job description."""
    keywords = extract_keywords(job_description)

    # Build combined text from all resume fields
    combined_parts = []
    for field in ["name", "phone", "email", "address", "job_intent", "education",
                   "expected_salary", "work_years"]:
        if resume_info.get(field):
            combined_parts.append(str(resume_info[field]))

    projects_text = ""
    for p in resume_info.get("projects", []):
        projects_text += f"{p.get('name', '')} {p.get('description', '')} "
    combined_parts.append(projects_text)

    combined_text = " ".join(combined_parts)

    skill_match_rate = calculate_similarity(combined_text, keywords)

    # Experience relevance: check work_years field against job description
    experience_score = 0.5
    work_years = resume_info.get("work_years", "")
    if work_years:
        # Try to extract numeric years
        years_num = re.search(r"(\d+)", str(work_years))
        if years_num:
            yrs = int(years_num.group(1))
            if yrs >= 5:
                experience_score = 1.0
            elif yrs >= 3:
                experience_score = 0.8
            elif yrs >= 1:
                experience_score = 0.6
            else:
                experience_score = 0.4

    # Education bonus
    education_bonus = 0.0
    education = resume_info.get("education", "")
    if education:
        if re.search(r"(本科|学士|bachelor)", str(education), re.IGNORECASE):
            education_bonus = 0.1
        elif re.search(r"(硕士|研究生|master|MS|MA)", str(education), re.IGNORECASE):
            education_bonus = 0.15
        elif re.search(r"(博士|doctor|PhD)", str(education), re.IGNORECASE):
            education_bonus = 0.2

    overall_score = min(1.0, skill_match_rate * 0.6 + experience_score * 0.3 + education_bonus)

    return {
        "overall_score": round(overall_score, 4),
        "skill_match_rate": round(skill_match_rate, 4),
        "experience_score": round(experience_score, 4),
        "education_bonus": round(education_bonus, 4),
        "matched_keywords": [
            kw for kw in keywords if kw.lower() in combined_text.lower()
        ],
        "job_keywords": keywords,
    }


MATCH_PROMPT = """你是一个专业的招聘匹配度评估助手。请根据以下简历信息和岗位需求，对候选人进行匹配度评分。

岗位需求：
{job_description}

候选人简历信息（JSON 格式）：
{resume_info}

请从以下维度评分（0.0 到 1.0）：
1. skill_match_rate: 技能匹配率（候选人技能与岗位要求的匹配程度）
2. experience_score: 工作经验相关性（工作年限和项目经验与岗位的匹配程度）
3. education_score: 学历匹配度
4. overall_score: 综合评分（加权计算）
5. analysis: 简短的匹配分析（100字以内）
6. matched_skills: 匹配上的技能列表
7. missing_skills: 候选人缺少的关键技能

请只返回 JSON，不要包含其他文字。"""


def match_with_ai(resume_info: dict, job_description: str) -> dict:
    """Use AI to calculate precise match score."""
    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": "你是一个专业的招聘评估助手，只返回 JSON 格式数据。"},
            {"role": "user", "content": MATCH_PROMPT.format(
                job_description=job_description[:4000],
                resume_info=json.dumps(resume_info, ensure_ascii=False, indent=2),
            )},
        ],
        temperature=0.1,
        max_tokens=1500,
    )

    content = response.choices[0].message.content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content[:-3]
    return json.loads(content)


def match_resume(resume_info: dict, job_description: str) -> dict:
    """Compute match score, preferring AI with rule-based fallback."""
    if settings.openai_api_key:
        try:
            return match_with_ai(resume_info, job_description)
        except Exception:
            pass
    return match_with_rules(resume_info, job_description)
