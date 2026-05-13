"""FastAPI application for AI-powered resume analysis."""

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import settings
from pdf_parser import parse_resume
from ai_extractor import extract_info
from matcher import match_resume
from cache import get_cached_result, set_cached_result


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    yield


app = FastAPI(
    title="AI 简历分析系统",
    description="智能简历解析、关键信息提取与岗位匹配评分",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MatchRequest(BaseModel):
    job_description: str


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "resume-analyzer"}


@app.post("/api/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    """Upload and parse a PDF resume, extract key information."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 格式的简历文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传的文件为空")

    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制 ({settings.max_upload_size_mb}MB)",
        )

    # Parse PDF
    resume_text = parse_resume(content)
    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="无法从 PDF 中提取文本内容，请确认文件格式")

    # Check cache
    cached = await get_cached_result(resume_text)
    if cached:
        cached["cached"] = True
        return JSONResponse(content=cached)

    # Extract key info
    extracted = extract_info(resume_text)

    result = {
        "resume_id": uuid.uuid4().hex[:12],
        "parse_time_ms": 0,
        "raw_text_length": len(resume_text),
        "info": extracted,
        "cached": False,
    }

    # Cache result
    await set_cached_result(resume_text, result)

    return JSONResponse(content=result)


@app.post("/api/resume/match")
async def match_resume_to_job(
    file: UploadFile = File(...),
    job_description: str = Form(...),
):
    """Upload a resume and match it against a job description."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 格式的简历文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传的文件为空")

    start_time = time.time()

    resume_text = parse_resume(content)
    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="无法从 PDF 中提取文本内容")

    # Check cache
    cached = await get_cached_result(resume_text, job_description)
    if cached:
        cached["cached"] = True
        return JSONResponse(content=cached)

    # Extract info
    extracted = extract_info(resume_text)

    # Match
    match_result = match_resume(extracted, job_description)

    elapsed_ms = int((time.time() - start_time) * 1000)

    result = {
        "resume_id": uuid.uuid4().hex[:12],
        "parse_time_ms": elapsed_ms,
        "raw_text_length": len(resume_text),
        "info": extracted,
        "match": match_result,
        "cached": False,
    }

    await set_cached_result(resume_text, result, job_description)

    return JSONResponse(content=result)


@app.post("/api/resume/analyze")
async def full_analysis(
    file: UploadFile = File(...),
    job_description: str = Form(""),
):
    """Full analysis pipeline: parse + extract + match (optional)."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 格式的简历文件")

    content = await file.read()
    start_time = time.time()

    resume_text = parse_resume(content)
    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="无法从 PDF 中提取文本内容")

    # Check cache
    cached = await get_cached_result(resume_text, job_description or None)
    if cached:
        cached["cached"] = True
        return JSONResponse(content=cached)

    extracted = extract_info(resume_text)

    match_result = None
    if job_description.strip():
        match_result = match_resume(extracted, job_description.strip())

    elapsed_ms = int((time.time() - start_time) * 1000)

    result = {
        "resume_id": uuid.uuid4().hex[:12],
        "parse_time_ms": elapsed_ms,
        "raw_text_length": len(resume_text),
        "info": extracted,
        "match": match_result,
        "cached": False,
    }

    await set_cached_result(resume_text, result, job_description or None)

    return JSONResponse(content=result)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=settings.host, port=settings.port, reload=True)
