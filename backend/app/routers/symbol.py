"""
币种管理路由
===========
提供监控币种的管理接口，包括添加、删除、同步K线数据等
"""
import asyncio
import json
from typing import List, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..core.deps import get_db_session
from ..core.logger import logger
from ..models.symbol import Symbol
from ..models.kline import PriceKline
from ..schemas.symbol import SymbolCreate, SymbolResponse, SymbolListResponse
from ..services.binance_client import binance_client, SUPPORTED_INTERVALS

router = APIRouter(prefix="/symbols", tags=["币种管理"])


@router.get("", response_model=SymbolListResponse)
def get_symbols(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: bool = Query(None),
    symbol: str = Query(None),
    db: Session = Depends(get_db_session)
):
    """
    获取监控币种列表
    
    - **skip**: 跳过记录数
    - **limit**: 返回记录数限制
    - **is_active**: 按启用状态筛选
    - **symbol**: 按交易对模糊筛选
    """
    query = db.query(Symbol)
    
    if is_active is not None:
        query = query.filter(Symbol.is_active == is_active)
    
    if symbol:
        query = query.filter(Symbol.symbol.contains(symbol.upper()))
    
    total = query.count()
    items = query.order_by(Symbol.symbol).offset(skip).limit(limit).all()
    
    return SymbolListResponse(total=total, items=items)


@router.post("", response_model=SymbolResponse)
async def create_symbol(symbol_data: SymbolCreate, db: Session = Depends(get_db_session)):
    """
    添加监控币种
    
    仅创建记录，数据同步通过同步接口触发
    """
    symbol_name = symbol_data.symbol.upper()
    existing = db.query(Symbol).filter(Symbol.symbol == symbol_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="币种已存在")
    
    symbol = Symbol(symbol=symbol_name)
    db.add(symbol)
    db.commit()
    db.refresh(symbol)
    
    return symbol


# ========== 静态路由必须在动态路由之前 ==========

@router.get("/init-progress")
def get_init_progress(db: Session = Depends(get_db_session)):
    """
    获取交易对初始化进度
    
    返回已初始化和未初始化的交易对数量
    """
    from ..jobs.monitoring_jobs import INITIAL_SYNC_BATCH_SIZE
    
    total = db.query(Symbol).filter(Symbol.is_active == True).count()
    synced = db.query(Symbol).filter(
        Symbol.is_active == True,
        Symbol.initial_synced == True
    ).count()
    unsynced = total - synced
    
    # 估算剩余时间（每分钟初始化 INITIAL_SYNC_BATCH_SIZE 个）
    estimated_minutes = (unsynced + INITIAL_SYNC_BATCH_SIZE - 1) // INITIAL_SYNC_BATCH_SIZE if unsynced > 0 else 0
    
    return {
        "total": total,
        "synced": synced,
        "unsynced": unsynced,
        "progress_percent": round(synced / total * 100, 1) if total > 0 else 100,
        "batch_size": INITIAL_SYNC_BATCH_SIZE,
        "estimated_minutes": estimated_minutes
    }


@router.get("/available")
async def get_available_symbols(db: Session = Depends(get_db_session)):
    """
    获取所有可添加的Binance合约交易对
    
    排除已添加的交易对
    """
    try:
        # 获取Binance所有合约交易对
        all_symbols = await binance_client.get_all_futures_symbols()
        
        # 获取已添加的交易对
        existing = db.query(Symbol.symbol).all()
        existing_set = {s.symbol for s in existing}
        
        # 过滤出未添加的
        available = [s for s in all_symbols if s not in existing_set]
        
        return {
            "total_binance": len(all_symbols),
            "existing": len(existing_set),
            "available": len(available),
            "symbols": available
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取交易对列表失败: {str(e)}")


@router.get("/bulk-add")
async def bulk_add_all_symbols(
    db: Session = Depends(get_db_session)
):
    """
    一键添加所有Binance合约交易对（SSE进度推送）
    
    仅添加交易对到数据库，不同步历史数据
    K线数据将由定时任务自动同步
    """
    async def generate_progress() -> AsyncGenerator[str, None]:
        try:
            # 1. 获取所有可用交易对
            yield f"data: {json.dumps({'phase': 'fetch', 'message': '正在获取Binance交易对列表...'})}\n\n"
            
            all_symbols = await binance_client.get_all_futures_symbols()
            
            # 获取已存在的交易对
            existing = db.query(Symbol.symbol).all()
            existing_set = {s.symbol for s in existing}
            
            # 过滤出需要添加的
            to_add = [s for s in all_symbols if s not in existing_set]
            
            yield f"data: {json.dumps({'phase': 'info', 'total': len(to_add), 'existing': len(existing_set), 'message': f'共 {len(to_add)} 个新交易对需要添加'})}\n\n"
            
            if not to_add:
                yield f"data: {json.dumps({'phase': 'complete', 'progress': 100, 'message': '所有交易对已存在，无需添加', 'added': 0})}\n\n"
                return
            
            # 2. 逐个添加交易对到数据库
            added_count = 0
            failed_symbols = []
            
            for idx, symbol_name in enumerate(to_add):
                try:
                    progress = int((idx / len(to_add)) * 100)
                    
                    # 添加交易对到数据库
                    existing_symbol = db.query(Symbol).filter(Symbol.symbol == symbol_name).first()
                    if not existing_symbol:
                        new_symbol = Symbol(symbol=symbol_name, is_active=True)
                        db.add(new_symbol)
                        db.commit()
                        added_count += 1
                    
                    yield f"data: {json.dumps({'phase': 'adding', 'progress': progress, 'current': idx + 1, 'total': len(to_add), 'symbol': symbol_name, 'status': 'done'})}\n\n"
                    
                except Exception as e:
                    logger.error(f"[BulkAdd] {symbol_name} 添加失败: {e}")
                    failed_symbols.append(symbol_name)
                    yield f"data: {json.dumps({'phase': 'adding', 'progress': progress, 'current': idx + 1, 'total': len(to_add), 'symbol': symbol_name, 'status': 'error', 'error': str(e)})}\n\n"
            
            # 3. 完成
            yield f"data: {json.dumps({'phase': 'complete', 'progress': 100, 'message': f'添加完成: 新增 {added_count} 个交易对，K线数据将由定时任务自动同步', 'added': added_count, 'failed': len(failed_symbols)})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'phase': 'error', 'message': f'批量添加失败: {str(e)}'})}\n\n"
    
    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ========== 动态路由 ==========

@router.get("/{symbol_name}/sync")
async def sync_symbol_data(symbol_name: str, db: Session = Depends(get_db_session)):
    """
    同步币种的所有周期K线数据（最近90天）
    
    通过SSE推送同步进度
    """
    symbol_upper = symbol_name.upper()
    symbol = db.query(Symbol).filter(Symbol.symbol == symbol_upper).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="币种不存在")
    
    async def generate_progress() -> AsyncGenerator[str, None]:
        total_intervals = len(SUPPORTED_INTERVALS)
        
        for idx, interval in enumerate(SUPPORTED_INTERVALS):
            progress = int((idx / total_intervals) * 100)
            yield f"data: {json.dumps({'progress': progress, 'interval': interval, 'status': 'syncing'})}\n\n"
            
            try:
                count = await binance_client.sync_klines(
                    symbol_upper, 
                    interval=interval, 
                    initial_days=90, 
                    force=True
                )
                yield f"data: {json.dumps({'progress': progress, 'interval': interval, 'status': 'done', 'count': count})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'progress': progress, 'interval': interval, 'status': 'error', 'error': str(e)})}\n\n"
            
            await asyncio.sleep(0.1)
        
        yield f"data: {json.dumps({'progress': 100, 'status': 'complete'})}\n\n"
    
    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.put("/{symbol_name}/toggle")
def toggle_symbol(symbol_name: str, db: Session = Depends(get_db_session)):
    """
    切换币种监控状态
    
    启用/停用监控
    """
    symbol = db.query(Symbol).filter(Symbol.symbol == symbol_name.upper()).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="币种不存在")
    
    symbol.is_active = not symbol.is_active
    db.commit()
    db.refresh(symbol)
    return {"symbol": symbol.symbol, "is_active": symbol.is_active}


@router.put("/batch/activate")
def batch_activate_symbols(
    symbols: List[str],
    is_active: bool = Query(True),
    db: Session = Depends(get_db_session)
):
    """
    批量启用/停用币种
    
    - **symbols**: 交易对列表
    - **is_active**: 目标状态
    """
    count = 0
    for symbol_name in symbols:
        symbol = db.query(Symbol).filter(Symbol.symbol == symbol_name.upper()).first()
        if symbol:
            symbol.is_active = is_active
            count += 1
    
    db.commit()
    return {"message": f"已更新 {count} 个币种"}


@router.delete("/batch")
def batch_delete_symbols(symbols: List[str], db: Session = Depends(get_db_session)):
    """
    批量删除监控币种及其K线数据
    
    - **symbols**: 要删除的交易对列表
    """
    if not symbols:
        raise HTTPException(status_code=400, detail="请提供要删除的币种列表")

    normalized = [symbol.upper() for symbol in symbols]

    deleted_klines = (
        db.query(PriceKline)
        .filter(PriceKline.symbol.in_(normalized))
        .delete(synchronize_session=False)
    )

    deleted_symbols = (
        db.query(Symbol)
        .filter(Symbol.symbol.in_(normalized))
        .delete(synchronize_session=False)
    )

    if deleted_symbols == 0:
        raise HTTPException(status_code=404, detail="未找到任何匹配的币种")

    db.commit()
    return {
        "message": f"已删除 {deleted_symbols} 个币种并清理 {deleted_klines} 条K线数据",
        "deleted": deleted_symbols,
        "deleted_klines": deleted_klines,
    }


@router.delete("/{symbol_name}")
def delete_symbol(symbol_name: str, db: Session = Depends(get_db_session)):
    """
    删除监控币种及其K线数据
    
    - **symbol_name**: 交易对名称
    """
    symbol_upper = symbol_name.upper()
    symbol = db.query(Symbol).filter(Symbol.symbol == symbol_upper).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="币种不存在")
    
    # 删除该币种的所有周期K线数据
    deleted_klines = db.query(PriceKline).filter(PriceKline.symbol == symbol_upper).delete()
    
    db.delete(symbol)
    db.commit()
    return {"message": f"删除成功，已清理 {deleted_klines} 条K线数据"}

