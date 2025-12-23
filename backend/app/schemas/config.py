"""
配置相关 Pydantic 模式
=====================
包含全局配置和币种个性化配置的数据验证模型
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


# ========== 全局配置相关 ==========

class ConfigBase(BaseModel):
    """配置基础模式"""
    key: str = Field(..., pattern=r'^[a-z0-9_]+$', description="配置键名，只能包含小写字母、数字和下划线")
    value: str = Field(..., min_length=1, description="配置值")
    
    @field_validator('value')
    @classmethod
    def validate_value(cls, v: str, info) -> str:
        """验证配置值的合法性"""
        key = info.data.get('key', '')
        
        # 百分比类型的配置
        if key.endswith('_percent') or key.endswith('_error'):
            try:
                val = float(v)
                if not 0 <= val <= 100:
                    raise ValueError('百分比必须在0-100之间')
            except ValueError as e:
                if '百分比' in str(e):
                    raise
                raise ValueError(f'百分比配置值必须是数字: {v}')
        
        # 计数类型的配置
        elif key.endswith('_cnt') or key.endswith('_count'):
            try:
                val = int(v)
                if val < 0:
                    raise ValueError('计数值必须大于等于0')
            except ValueError as e:
                if '计数' in str(e):
                    raise
                raise ValueError(f'计数配置值必须是整数: {v}')
        
        return v


class ConfigUpdate(BaseModel):
    """配置更新模式"""
    value: str = Field(..., min_length=1, description="新参数值")


class ConfigResponse(ConfigBase):
    """配置响应模式"""
    id: int  # 记录ID
    
    class Config:
        from_attributes = True


class ConfigBatchUpdate(BaseModel):
    """批量更新配置模式"""
    configs: List[ConfigBase]  # 配置列表


# ========== 币种个性化配置相关 ==========

class SymbolConfigBase(BaseModel):
    """币种配置基础模式"""
    symbol: str = Field(..., pattern=r'^[A-Z0-9]+$', min_length=3, max_length=20, description="交易对，如BTCUSDT")
    interval: str = Field(..., pattern=r'^(1m|3m|5m|15m|30m|1h|2h|4h|6h|8h|12h|1d|3d|1w|1M)$', description="K线间隔")
    price_error: Optional[float] = Field(None, ge=0, le=100, description="开盘价误差阈值（%），null表示使用全局配置")
    middle_kline_cnt: Optional[int] = Field(None, ge=0, le=1000, description="D和E之间最少间隔K线数，null表示使用全局配置")
    fake_kline_cnt: Optional[int] = Field(None, ge=0, le=100, description="中间最多N个假K线，null表示使用全局配置")


class SymbolConfigCreate(SymbolConfigBase):
    """币种配置创建模式"""
    pass


class SymbolConfigUpdate(BaseModel):
    """币种配置更新模式"""
    price_error: Optional[float] = Field(None, ge=0, le=100, description="开盘价误差阈值（%）")
    middle_kline_cnt: Optional[int] = Field(None, ge=0, le=1000, description="D和E之间最少间隔K线数")
    fake_kline_cnt: Optional[int] = Field(None, ge=0, le=100, description="中间最多N个假K线")


class SymbolConfigResponse(SymbolConfigBase):
    """币种配置响应模式"""
    id: int  # 记录ID
    created_at: datetime  # 创建时间
    updated_at: datetime  # 更新时间
    
    class Config:
        from_attributes = True


class SymbolConfigListResponse(BaseModel):
    """币种配置列表响应模式"""
    total: int  # 总数
    items: List[SymbolConfigResponse]  # 配置列表

