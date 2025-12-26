"""
实时监控路由
===========
提供实时监控数据和K线数据查询接口
"""
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Query

from ..core.config import settings
from ..core.database import SessionLocal
from ..core.timezone import now_beijing
from ..models.kline import PriceKline
from ..models.symbol import Symbol
from ..schemas.monitoring import KlineData, MonitorMetrics, SymbolMonitorData, SymbolMonitorListResponse
from ..services.config_service import config_service
from ..services.monitor_service import monitor_service
from ..services.binance_client import BinanceClient

router = APIRouter(prefix="/monitor", tags=["实时监控"])




@router.get("/data", response_model=SymbolMonitorListResponse)
async def get_monitor_data(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    symbol: Optional[str] = None,
    interval: str = Query("15m", description="K线周期"),
    kline_limit: int = Query(50, ge=10, le=200, description="K线数量")
):
    """
    获取币种实时监控数据
    
    返回每个币种的三大需求计算值和K线数据
    
    - **skip**: 跳过记录数
    - **limit**: 返回记录数限制
    - **symbol**: 按交易对筛选
    - **interval**: K线周期
    - **kline_limit**: 返回的K线数量
    """
    db = SessionLocal()
    try:
        # 获取启用的币种
        query = db.query(Symbol).filter(Symbol.is_active == True)
        if symbol:
            query = query.filter(Symbol.symbol == symbol)
        
        total = query.count()
        symbols = query.offset(skip).limit(limit).all()
        
        items = []
        for sym in symbols:
            try:
                data = await _get_symbol_monitor_data(db, sym.symbol, interval, kline_limit)
                items.append(data)
            except Exception as e:
                print(f"获取 {sym.symbol} 监控数据失败: {e}")
                continue
        
        return SymbolMonitorListResponse(total=total, items=items)
    finally:
        db.close()


@router.get("/data/{symbol}", response_model=SymbolMonitorData)
async def get_single_symbol_data(
    symbol: str,
    interval: str = Query("15m", description="K线周期"),
    kline_limit: int = Query(50, ge=10, le=200, description="K线数量")
):
    """
    获取单个币种的监控数据
    
    - **symbol**: 交易对名称
    - **interval**: K线周期
    - **kline_limit**: 返回的K线数量
    """
    db = SessionLocal()
    try:
        return await _get_symbol_monitor_data(db, symbol, interval, kline_limit)
    finally:
        db.close()


async def _get_open_price_match_result(
    db, symbol: str, interval: str, price_error: float, middle_kline_cnt: int, fake_count_n: int
) -> dict:
    """
    获取开盘价匹配结果（调用 monitor_service）
    
    Args:
        db: 数据库会话
        symbol: 交易对
        interval: K线周期
        price_error: 价格误差阈值
        middle_kline_cnt: D和E之间最少间隔K线数
        fake_count_n: 中间K线数量阈值
    
    Returns:
        包含匹配结果的字典
    """
    result = {
        "triggered": False,
        "match_info": None,
        "price_d": None,
        "price_d_time": None,
        "price_e": None,
        "price_e_time": None,
        "error_percent": None,
        "middle_count": None
    }
    
    try:
        now = now_beijing()
        one_month_ago = now - timedelta(days=settings.MAX_LOOKBACK_DAYS)
        
        bullish_klines = db.query(PriceKline).filter(
            PriceKline.symbol == symbol,
            PriceKline.interval == interval,
            PriceKline.close > PriceKline.open,
            PriceKline.open_time >= one_month_ago,
            PriceKline.close_time < now
        ).order_by(PriceKline.open_time.desc()).all()
        
        if len(bullish_klines) < 1:
            return result
        
        latest = bullish_klines[0]
        price_d = latest.open
        time_d = latest.open_time
        result["price_d"] = price_d
        result["price_d_time"] = time_d.strftime("%m-%d %H:%M")
        
        if len(bullish_klines) < 2:
            return result
        
        for i, historical in enumerate(bullish_klines[1:], 1):
            if i < middle_kline_cnt:
                continue
            
            price_e = historical.open
            time_e = historical.open_time
            error_percent = abs(price_d - price_e) / min(price_d, price_e) * 100
            
            if error_percent <= price_error:
                avg_price = (price_d + price_e) / 2
                
                middle_klines = db.query(PriceKline).filter(
                    PriceKline.symbol == symbol,
                    PriceKline.interval == interval,
                    PriceKline.close > PriceKline.open,
                    PriceKline.open_time > time_e,
                    PriceKline.open_time < time_d,
                    PriceKline.open < avg_price
                ).all()
                
                middle_count = len(middle_klines)
                
                if middle_count <= fake_count_n:
                    # 计算实际间隔K线数量
                    minutes_per_interval = BinanceClient.INTERVAL_TO_MINUTES.get(interval, 15)
                    diff_minutes = (time_d - time_e).total_seconds() / 60
                    interval_count = int(diff_minutes / minutes_per_interval)
                    
                    result["triggered"] = True
                    result["match_info"] = f"D: {price_d:.4f} | E: {price_e:.4f} | 误差: {error_percent:.2f}%"
                    result["price_e"] = price_e
                    result["price_e_time"] = time_e.strftime("%m-%d %H:%M")
                    result["middle_count"] = interval_count  # 返回实际间隔数量而不是假K线数量
                    result["error_percent"] = error_percent
                    return result
        
        return result
    except Exception as e:
        print(f"[API] 开盘价匹配检测异常 {symbol} {interval}: {e}")
        return result


async def _get_symbol_monitor_data(db, symbol: str, interval: str, kline_limit: int) -> SymbolMonitorData:
    """
    获取单个币种的完整监控数据（从数据库读取）
    
    Args:
        db: 数据库会话
        symbol: 交易对
        interval: K线周期
        kline_limit: K线数量
    
    Returns:
        币种监控数据
    """
    # 获取配置值
    volume_percent = config_service.get_config_float(db, "1_volume_percent", settings.DEFAULT_1_VOLUME_PERCENT)
    rise_threshold = config_service.get_config_float(db, "2_rise_percent", settings.DEFAULT_2_RISE_PERCENT)
    price_error = config_service.get_config_float(db, "3_price_error", settings.DEFAULT_3_PRICE_ERROR)
    middle_kline_cnt = int(config_service.get_config_float(db, "3_middle_kline_cnt", settings.DEFAULT_3_MIDDLE_KLINE_CNT))
    fake_count_n = int(config_service.get_config_float(db, "3_fake_kline_cnt", settings.DEFAULT_3_FAKE_KLINE_CNT))
    
    # 从数据库获取K线数据
    klines_db = db.query(PriceKline).filter(
        PriceKline.symbol == symbol,
        PriceKline.interval == interval
    ).order_by(PriceKline.open_time.desc()).limit(kline_limit).all()
    klines_db = list(reversed(klines_db))  # 按时间正序
    
    # 获取最新K线的收盘价作为当前价格
    current_price = klines_db[-1].close if klines_db else 0.0
    
    # 从数据库获取1分钟K线计算成交量
    now = now_beijing()
    klines_1m = db.query(PriceKline).filter(
        PriceKline.symbol == symbol,
        PriceKline.interval == "1m",
        PriceKline.open_time >= now - timedelta(minutes=480)
    ).order_by(PriceKline.open_time.desc()).all()
    
    # 计算15分钟成交量（最近15根1m K线）
    volume_15m = sum(k.volume for k in klines_1m[:15])
    # 计算8小时成交量（全部480根1m K线）
    volume_8h = sum(k.volume for k in klines_1m)
    volume_threshold = volume_8h * volume_percent / 100
    volume_triggered = volume_15m >= volume_threshold
    
    # 从数据库计算涨幅（最近15根已收盘的1m K线）
    klines_1m_sorted = sorted(klines_1m, key=lambda x: x.open_time)
    completed_klines = klines_1m_sorted[:-1] if len(klines_1m_sorted) > 1 else klines_1m_sorted
    recent_15 = completed_klines[-15:] if len(completed_klines) >= 15 else completed_klines
    
    rise_start_time = None
    rise_start_price = None
    rise_end_time = None
    rise_end_price = None
    
    if recent_15:
        first_open = recent_15[0].open
        last_close = recent_15[-1].close
        rise_percent = (last_close - first_open) / first_open * 100 if first_open > 0 else 0
        
        rise_start_time = recent_15[0].open_time.strftime("%m-%d %H:%M")
        rise_start_price = first_open
        rise_end_time = recent_15[-1].open_time.strftime("%m-%d %H:%M")
        rise_end_price = last_close
    else:
        rise_percent = 0.0
    rise_triggered = rise_percent >= rise_threshold
    
    # 检测开盘价匹配 - 使用 monitor_service 的方法
    open_price_result = await _get_open_price_match_result(
        db, symbol, interval, price_error, middle_kline_cnt, fake_count_n
    )
    
    # 转换K线数据格式
    kline_data = [
        KlineData(
            open_time=k.open_time.strftime("%Y-%m-%d %H:%M"),
            open=k.open,
            high=k.high,
            low=k.low,
            close=k.close,
            volume=k.volume,
            quote_volume=k.quote_volume,
            close_time=k.close_time.strftime("%Y-%m-%d %H:%M")
        )
        for k in klines_db
    ]
    
    return SymbolMonitorData(
        symbol=symbol,
        timestamp=now_beijing().strftime("%Y-%m-%d %H:%M:%S"),
        current_price=current_price,
        metrics=MonitorMetrics(
            volume_15m=volume_15m,
            volume_8h=volume_8h,
            volume_percent=volume_percent,
            volume_threshold=volume_threshold,
            volume_triggered=volume_triggered,
            rise_percent=rise_percent,
            rise_threshold=rise_threshold,
            rise_triggered=rise_triggered,
            rise_start_time=rise_start_time,
            rise_start_price=rise_start_price,
            rise_end_time=rise_end_time,
            rise_end_price=rise_end_price,
            price_error_config=price_error,
            fake_count_n_config=fake_count_n,
            open_price_triggered=open_price_result["triggered"],
            open_price_match_info=open_price_result["match_info"],
            open_price_d=open_price_result["price_d"],
            open_price_d_time=open_price_result["price_d_time"],
            open_price_e=open_price_result["price_e"],
            open_price_e_time=open_price_result["price_e_time"],
            open_price_error=open_price_result["error_percent"],
            open_price_middle_count=open_price_result["middle_count"]
        ),
        klines=kline_data
    )


@router.get("/klines/{symbol}")
async def get_klines(
    symbol: str,
    interval: str = Query("15m", description="K线周期: 15m, 30m, 1h, 4h, 1d, 3d"),
    limit: int = Query(100, ge=10, le=1000, description="K线数量")
):
    """
    获取K线数据（从数据库读取）
    
    - **symbol**: 交易对名称
    - **interval**: K线周期
    - **limit**: 返回的K线数量
    """
    db = SessionLocal()
    try:
        klines = db.query(PriceKline).filter(
            PriceKline.symbol == symbol,
            PriceKline.interval == interval
        ).order_by(PriceKline.open_time.desc()).limit(limit).all()
        klines = list(reversed(klines))  # 按时间正序
        
        return {
            "symbol": symbol,
            "interval": interval,
            "count": len(klines),
            "klines": [
                {
                    "open_time": k.open_time.strftime("%Y-%m-%d %H:%M"),
                    "open": k.open,
                    "high": k.high,
                    "low": k.low,
                    "close": k.close,
                    "volume": k.volume,
                    "quote_volume": k.quote_volume
                }
                for k in klines
            ]
        }
    finally:
        db.close()

