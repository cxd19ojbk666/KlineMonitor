"""
日志查看路由
===========
提供日志文件读取API
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/logs", tags=["日志"])

LOG_DIR = Path("logs")


class LogFile(BaseModel):
    """日志文件信息"""
    name: str
    type: str  # 'app' or 'error'
    date: str
    size: int
    modified: str


class LogContent(BaseModel):
    """日志内容"""
    file_name: str
    total_lines: int
    lines: List[str]
    has_more: bool


@router.get("/files", response_model=List[LogFile])
def list_log_files():
    """
    获取所有日志文件列表
    """
    if not LOG_DIR.exists():
        return []
    
    files = []
    # 返回分级日志文件
    log_files = [
        ("app.log", "app"),
        ("info.log", "info"),
        ("warning.log", "warning"),
        ("error.log", "error"),
    ]
    for log_name, log_type in log_files:
        file_path = LOG_DIR / log_name
        if file_path.exists():
            stat = file_path.stat()
            files.append(LogFile(
                name=log_name,
                type=log_type,
                date="",
                size=stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            ))
    
    return files


@router.get("/content/{file_name}", response_model=LogContent)
def get_log_content(
    file_name: str,
    tail: int = Query(default=500, ge=1, le=5000, description="返回最后N行"),
    search: Optional[str] = Query(default=None, description="搜索关键词")
):
    """
    获取日志文件内容
    
    Args:
        file_name: 日志文件名
        tail: 返回最后N行，默认500行
        search: 可选的搜索关键词
    """
    file_path = LOG_DIR / file_name
    
    # 安全检查：防止路径遍历
    if ".." in file_name or "/" in file_name or "\\" in file_name:
        raise HTTPException(status_code=400, detail="非法文件名")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="日志文件不存在")
    
    if not file_path.suffix == ".log":
        raise HTTPException(status_code=400, detail="非日志文件")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        
        total_lines = len(all_lines)
        
        # 如果有搜索关键词，先过滤
        if search:
            all_lines = [line for line in all_lines if search.lower() in line.lower()]
        
        # 取最后N行
        if len(all_lines) > tail:
            lines = all_lines[-tail:]
            has_more = True
        else:
            lines = all_lines
            has_more = False
        
        # 去除行尾换行符
        lines = [line.rstrip("\n\r") for line in lines]
        
        return LogContent(
            file_name=file_name,
            total_lines=total_lines,
            lines=lines,
            has_more=has_more
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取日志失败: {str(e)}")


@router.get("/today")
def get_today_logs(
    log_type: str = Query(default="app", regex="^(app|info|warning|error)$"),
    tail: int = Query(default=200, ge=1, le=5000),
    search: Optional[str] = Query(default=None)
):
    """
    获取日志
    
    Args:
        log_type: 日志类型 (app/info/warning/error)
        tail: 返回最后N行
        search: 搜索关键词
    """
    file_name = f"{log_type}.log"
    
    return get_log_content(file_name, tail, search)
