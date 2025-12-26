"""
提醒记录路由
===========
提供提醒记录的 CRUD 接口和仪表盘统计数据
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.deps import get_db_session
from ..models.alert import Alert
from ..models.symbol import Symbol
from ..schemas.alert import AlertResponse, AlertListResponse, DashboardStats

router = APIRouter(prefix="/alerts", tags=["提醒记录"])


@router.get("", response_model=AlertListResponse)
def get_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    alert_type: Optional[int] = Query(None, ge=1, le=3),
    symbol: Optional[str] = None,
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    db: Session = Depends(get_db_session)
):
    """
    获取提醒列表
    
    - **skip**: 跳过记录数
    - **limit**: 返回记录数限制
    - **alert_type**: 按类型筛选（1:成交量, 2:涨幅, 3:开盘价匹配）
    - **symbol**: 按交易对筛选
    - **start_time**: 开始时间
    - **end_time**: 结束时间
    """
    query = db.query(Alert)
    
    if alert_type:
        query = query.filter(Alert.alert_type == alert_type)
    if symbol:
        query = query.filter(Alert.symbol == symbol)
    if start_time:
        query = query.filter(Alert.created_at >= start_time)
    if end_time:
        query = query.filter(Alert.created_at <= end_time)
    
    total = query.count()
    items = query.order_by(Alert.created_at.desc()).offset(skip).limit(limit).all()
    
    return AlertListResponse(total=total, items=items)


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(db: Session = Depends(get_db_session)):
    """
    获取仪表盘统计数据
    
    包含：今日提醒统计、按类型分类、活跃币种、最近提醒等
    """
    from ..core.scheduler import scheduler_running
    
    # 使用北京时间计算今日开始时间
    today_start = now_beijing().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 今日提醒总数
    total_alerts_today = db.query(Alert).filter(Alert.created_at >= today_start).count()
    
    # 按类型统计
    type_counts = db.query(Alert.alert_type, func.count(Alert.id)).filter(
        Alert.created_at >= today_start
    ).group_by(Alert.alert_type).all()
    
    type_count_dict = {t: c for t, c in type_counts}
    
    # 活跃币种数量
    active_symbols_query = db.query(Symbol).filter(Symbol.is_active == True)
    active_symbols_count = active_symbols_query.count()
    active_symbols = [s.symbol for s in active_symbols_query.all()]
    
    # 最近30条提醒
    recent_alerts = db.query(Alert).order_by(Alert.created_at.desc()).limit(30).all()
    
    return DashboardStats(
        total_alerts_today=total_alerts_today,
        alert_type_1_count=type_count_dict.get(1, 0),
        alert_type_2_count=type_count_dict.get(2, 0),
        alert_type_3_count=type_count_dict.get(3, 0),
        active_symbols_count=active_symbols_count,
        active_symbols=active_symbols,
        is_running=scheduler_running,
        recent_alerts=recent_alerts
    )


@router.delete("/{alert_id}")
def delete_alert(alert_id: int, db: Session = Depends(get_db_session)):
    """
    删除单条提醒记录
    
    - **alert_id**: 提醒记录ID
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="提醒记录不存在")
    
    db.delete(alert)
    db.commit()
    return {"message": "删除成功"}


@router.delete("")
def delete_all_alerts(
    alert_type: Optional[int] = Query(None, ge=1, le=3),
    db: Session = Depends(get_db_session)
):
    """
    批量删除提醒记录
    
    - **alert_type**: 按类型筛选删除（可选）
    """
    query = db.query(Alert)
    if alert_type:
        query = query.filter(Alert.alert_type == alert_type)
    
    count = query.delete()
    db.commit()
    return {"message": f"已删除 {count} 条记录"}

