"""
参数配置路由
===========
提供全局配置和币种个性化配置的管理接口
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.deps import get_db_session
from ..models.config import Config, SymbolConfig
from ..models.symbol import Symbol
from ..schemas.config import (
    ConfigUpdate, ConfigResponse, ConfigBatchUpdate,
    SymbolConfigCreate, SymbolConfigUpdate, SymbolConfigResponse, SymbolConfigListResponse
)
from ..services.config_service import config_service

router = APIRouter(prefix="/config", tags=["参数配置"])


# ========== 全局配置接口 ==========

@router.get("", response_model=List[ConfigResponse])
def get_configs(db: Session = Depends(get_db_session)):
    """
    获取所有全局配置
    
    如果没有配置会自动初始化默认值
    """
    return config_service.get_all_configs(db)


@router.post("/batch", response_model=List[ConfigResponse])
def batch_update_configs(batch: ConfigBatchUpdate, db: Session = Depends(get_db_session)):
    """
    批量更新全局配置
    
    不存在的配置会自动创建
    """
    results = []
    for config_data in batch.configs:
        config = db.query(Config).filter(Config.key == config_data.key).first()
        
        if not config:
            config = Config(key=config_data.key, value=config_data.value)
            db.add(config)
        else:
            config.value = config_data.value
        
        db.commit()
        db.refresh(config)
        results.append(config)
    
    return results


# ========== 币种个性化配置接口（静态路由必须在动态路由之前） ==========

@router.get("/symbol-configs", response_model=SymbolConfigListResponse)
def get_symbol_configs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    symbol: str = Query(None),
    interval: str = Query(None),
    db: Session = Depends(get_db_session)
):
    """
    获取币种个性化配置列表
    
    - **skip**: 跳过记录数
    - **limit**: 返回记录数限制
    - **symbol**: 按交易对模糊筛选
    - **interval**: 按K线间隔筛选
    """
    query = db.query(SymbolConfig)
    
    if symbol:
        query = query.filter(SymbolConfig.symbol.contains(symbol.upper()))
    if interval:
        query = query.filter(SymbolConfig.interval == interval.lower())
    
    total = query.count()
    items = query.order_by(SymbolConfig.symbol, SymbolConfig.interval).offset(skip).limit(limit).all()
    
    return SymbolConfigListResponse(total=total, items=items)


@router.post("/symbol-configs", response_model=SymbolConfigResponse)
def create_symbol_config(config_data: SymbolConfigCreate, db: Session = Depends(get_db_session)):
    """
    创建币种个性化配置
    
    币种必须存在于监控列表中，同一币种+间隔只能有一条配置
    """
    symbol_upper = config_data.symbol.upper()
    interval_lower = config_data.interval.lower()
    
    # 检查币种是否存在于监控列表
    symbol = db.query(Symbol).filter(Symbol.symbol == symbol_upper).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="币种不存在于监控列表中")
    
    # 检查是否已存在配置（同一币种+间隔）
    existing = db.query(SymbolConfig).filter(
        SymbolConfig.symbol == symbol_upper,
        SymbolConfig.interval == interval_lower
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该币种+间隔已存在个性化配置")
    
    config = SymbolConfig(
        symbol=symbol_upper,
        interval=interval_lower,
        price_error=config_data.price_error,
        middle_kline_cnt=config_data.middle_kline_cnt,
        fake_kline_cnt=config_data.fake_kline_cnt
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    
    return config


@router.get("/symbol-configs/{symbol_name}/{interval}", response_model=SymbolConfigResponse)
def get_symbol_config(symbol_name: str, interval: str, db: Session = Depends(get_db_session)):
    """
    获取单个币种+间隔的个性化配置
    
    - **symbol_name**: 交易对名称
    - **interval**: K线间隔
    """
    symbol_upper = symbol_name.upper()
    interval_lower = interval.lower()
    config = db.query(SymbolConfig).filter(
        SymbolConfig.symbol == symbol_upper,
        SymbolConfig.interval == interval_lower
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="该币种+间隔没有个性化配置")
    
    return config


@router.put("/symbol-configs/{symbol_name}/{interval}", response_model=SymbolConfigResponse)
def update_symbol_config(
    symbol_name: str,
    interval: str,
    config_update: SymbolConfigUpdate,
    db: Session = Depends(get_db_session)
):
    """
    更新币种个性化配置
    
    如果配置不存在会自动创建
    """
    symbol_upper = symbol_name.upper()
    interval_lower = interval.lower()
    config = db.query(SymbolConfig).filter(
        SymbolConfig.symbol == symbol_upper,
        SymbolConfig.interval == interval_lower
    ).first()
    
    if not config:
        # 如果不存在，检查币种是否在监控列表中
        symbol = db.query(Symbol).filter(Symbol.symbol == symbol_upper).first()
        if not symbol:
            raise HTTPException(status_code=404, detail="币种不存在于监控列表中")
        
        # 创建新配置
        config = SymbolConfig(
            symbol=symbol_upper,
            interval=interval_lower,
            price_error=config_update.price_error,
            middle_kline_cnt=config_update.middle_kline_cnt,
            fake_kline_cnt=config_update.fake_kline_cnt
        )
        db.add(config)
    else:
        # 更新现有配置
        if config_update.price_error is not None:
            config.price_error = config_update.price_error
        if config_update.middle_kline_cnt is not None:
            config.middle_kline_cnt = config_update.middle_kline_cnt
        if config_update.fake_kline_cnt is not None:
            config.fake_kline_cnt = config_update.fake_kline_cnt
    
    db.commit()
    db.refresh(config)
    
    return config


@router.delete("/symbol-configs/{symbol_name}/{interval}")
def delete_symbol_config(symbol_name: str, interval: str, db: Session = Depends(get_db_session)):
    """
    删除币种个性化配置
    
    删除后将使用全局配置
    """
    symbol_upper = symbol_name.upper()
    interval_lower = interval.lower()
    config = db.query(SymbolConfig).filter(
        SymbolConfig.symbol == symbol_upper,
        SymbolConfig.interval == interval_lower
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="该币种+间隔没有个性化配置")
    
    db.delete(config)
    db.commit()
    
    return {"message": "个性化配置已删除，将使用全局配置"}


# ========== 全局配置动态路由（放在最后） ==========

@router.get("/{key}", response_model=ConfigResponse)
def get_config_by_key(key: str, db: Session = Depends(get_db_session)):
    """
    获取单个全局配置
    
    - **key**: 配置键名
    """
    config = db.query(Config).filter(Config.key == key).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return config


@router.put("/{key}", response_model=ConfigResponse)
def update_config(key: str, config_update: ConfigUpdate, db: Session = Depends(get_db_session)):
    """
    更新单个全局配置
    
    不存在会自动创建
    """
    config = db.query(Config).filter(Config.key == key).first()
    
    if not config:
        # 如果不存在则创建
        config = Config(key=key, value=config_update.value)
        db.add(config)
    else:
        config.value = config_update.value
    
    db.commit()
    db.refresh(config)
    return config


@router.delete("/{key}")
def delete_config(key: str, db: Session = Depends(get_db_session)):
    """
    删除单个全局配置
    
    - **key**: 配置键名
    """
    config = db.query(Config).filter(Config.key == key).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    db.delete(config)
    db.commit()
    return {"message": "删除成功"}

