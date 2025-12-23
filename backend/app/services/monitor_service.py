"""
监控服务
=======
实现三大需求的核心监控逻辑

功能：
- 需求一：成交量监控 - 15分钟成交量与8小时成交量对比
- 需求二：涨幅监控 - 15分钟累计涨幅检测
- 需求三：开盘价匹配 - 历史开盘价匹配检测
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.database import SessionLocal
from ..core.logger import logger
from ..core.stats import monitor_stats_collector, MonitorResult
from ..models.kline import PriceKline
from ..models.config import SymbolConfig
from .binance_client import binance_client
from .alert_service import alert_service
from .config_service import config_service


class MonitorService:
    """监控服务 - 实现三大需求的核心逻辑"""
    
    def __init__(self):
        self.binance = binance_client
        self.alert = alert_service
    
    
    def _get_symbol_config(self, db: Session, symbol: str, interval: str) -> SymbolConfig | None:
        """
        获取币种+间隔的个性化配置
        
        Args:
            db: 数据库会话
            symbol: 交易对
            interval: K线间隔
        
        Returns:
            币种配置对象，如果不存在则返回None
        """
        return db.query(SymbolConfig).filter(
            SymbolConfig.symbol == symbol,
            SymbolConfig.interval == interval
        ).first()
    
    def _get_symbol_price_error(self, db: Session, symbol: str, interval: str, global_price_error: float) -> float:
        """
        获取币种的价格误差阈值
        优先使用币种+间隔的个性化配置，如果没有则使用全局配置
        
        Args:
            db: 数据库会话
            symbol: 交易对
            interval: K线间隔
            global_price_error: 全局误差阈值
        
        Returns:
            该币种+间隔应使用的误差阈值
        """
        config = self._get_symbol_config(db, symbol, interval)
        
        if config and config.price_error is not None:
            return config.price_error
        
        return global_price_error
    
    def _get_symbol_middle_kline_cnt(self, db: Session, symbol: str, interval: str, global_middle_kline_cnt: int) -> int:
        """
        获取币种的中间K线数阈值
        优先使用币种+间隔的个性化配置，如果没有则使用全局配置
        
        Args:
            db: 数据库会话
            symbol: 交易对
            interval: K线间隔
            global_middle_kline_cnt: 全局中间K线数阈值
        
        Returns:
            该币种+间隔应使用的中间K线数阈值
        """
        config = self._get_symbol_config(db, symbol, interval)
        
        if config and config.middle_kline_cnt is not None:
            return config.middle_kline_cnt
        
        return global_middle_kline_cnt
    
    def _get_symbol_fake_kline_cnt(self, db: Session, symbol: str, interval: str, global_fake_kline_cnt: int) -> int:
        """
        获取币种的假K线数阈值
        优先使用币种+间隔的个性化配置，如果没有则使用全局配置
        
        Args:
            db: 数据库会话
            symbol: 交易对
            interval: K线间隔
            global_fake_kline_cnt: 全局假K线数阈值
        
        Returns:
            该币种+间隔应使用的假K线数阈值
        """
        config = self._get_symbol_config(db, symbol, interval)
        
        if config and config.fake_kline_cnt is not None:
            return config.fake_kline_cnt
        
        return global_fake_kline_cnt
    
    async def check_volume(self, symbol: str) -> bool:
        """
        需求一：成交量监控
        
        计算15分钟成交量A与8小时成交量B，判断A >= B * percent / 100
        """
        try:
            db = SessionLocal()
            try:
                percent = config_service.get_config_float(db, "1_volume_percent", settings.DEFAULT_1_VOLUME_PERCENT)
            finally:
                db.close()
            
            volume_15m = await self.binance.get_recent_volume(symbol, 15)
            volume_8h = await self.binance.get_recent_volume(symbol, 480)
            threshold = volume_8h * percent / 100
            
            if volume_15m >= threshold:
                volume_ratio = (volume_15m / volume_8h * 100) if volume_8h > 0 else 0
                data = {
                    "volume_15m": volume_15m,
                    "volume_8h": volume_8h,
                    "volume_ratio": volume_ratio,
                    "volume_threshold": percent
                }
                await self.alert.reminder(symbol, 1, data)
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"[Monitor] 成交量监控异常 {symbol}: {e}")
            return False
    
    async def check_rise(self, symbol: str) -> bool:
        """
        需求二：涨幅监控
        
        计算15分钟累计涨幅C，判断C >= threshold
        """
        try:
            db = SessionLocal()
            try:
                threshold = config_service.get_config_float(db, "2_rise_percent", settings.DEFAULT_2_RISE_PERCENT)
            finally:
                db.close()
            
            # 获取15分钟涨幅和价格信息
            price_info = await self.binance.get_price_change_with_prices(symbol, 15)
            price_change = price_info["change_percent"]
            
            if price_change >= threshold:
                data = {
                    "rise_percent": price_change,
                    "rise_threshold": threshold,
                    "rise_start_price": price_info["start_price"],
                    "rise_end_price": price_info["end_price"]
                }
                await self.alert.reminder(symbol, 2, data)
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"[Monitor] 涨幅监控异常 {symbol}: {e}")
            return False
    
    async def check_open_price_match(self, symbol: str, timeframe: str) -> bool:
        """
        需求三：开盘价匹配
        
        匹配历史开盘价，误差≤阈值且中间满足条件
        """
        try:
            db = SessionLocal()
            try:
                # 获取全局配置
                global_price_error = config_service.get_config_float(db, "3_price_error", settings.DEFAULT_3_PRICE_ERROR)
                global_middle_kline_cnt = int(config_service.get_config_float(db, "3_middle_kline_cnt", settings.DEFAULT_3_MIDDLE_KLINE_CNT))
                global_fake_kline_cnt = int(config_service.get_config_float(db, "3_fake_kline_cnt", settings.DEFAULT_3_FAKE_KLINE_CNT))
                
                # 获取币种+间隔的个性化配置（优先级高于全局配置）
                price_error = self._get_symbol_price_error(db, symbol, timeframe, global_price_error)
                middle_kline_cnt = self._get_symbol_middle_kline_cnt(db, symbol, timeframe, global_middle_kline_cnt)
                fake_count_n = self._get_symbol_fake_kline_cnt(db, symbol, timeframe, global_fake_kline_cnt)
                
                now = datetime.utcnow()
                one_month_ago = now - timedelta(days=settings.MAX_LOOKBACK_DAYS)
                
                bullish_klines = db.query(PriceKline).filter(
                    PriceKline.symbol == symbol,
                    PriceKline.interval == timeframe,
                    PriceKline.close > PriceKline.open,
                    PriceKline.open_time >= one_month_ago,
                    PriceKline.close_time < now
                ).order_by(PriceKline.open_time.desc()).all()
                
                if len(bullish_klines) < 2:
                    return False
                
                latest = bullish_klines[0]
                price_d = latest.open
                time_d = latest.open_time
                
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
                            PriceKline.interval == timeframe,
                            PriceKline.close > PriceKline.open,
                            PriceKline.open_time > time_e,
                            PriceKline.open_time < time_d,
                            PriceKline.open < avg_price
                        ).all()
                        
                        middle_count = len(middle_klines)
                        
                        if middle_count <= fake_count_n:
                            dedup_key = f"{timeframe}_{time_d.strftime('%Y%m%d%H%M')}_{time_e.strftime('%Y%m%d%H%M')}"
                            
                            # 计算实际间隔K线数量
                            from .binance_client import BinanceClient
                            minutes_per_interval = BinanceClient.INTERVAL_TO_MINUTES.get(timeframe, 15)
                            diff_minutes = (time_d - time_e).total_seconds() / 60
                            interval_count = int(diff_minutes / minutes_per_interval)
                            
                            data = {
                                "timeframe": timeframe,
                                "price_d": price_d,
                                "price_e": price_e,
                                "time_d": time_d.strftime('%Y-%m-%d %H:%M'),
                                "time_e": time_e.strftime('%Y-%m-%d %H:%M'),
                                "price_error": error_percent,
                                "price_error_threshold": price_error,
                                "middle_count": interval_count,  # 使用实际间隔数量
                                "middle_count_threshold": fake_count_n
                            }
                            result = await self.alert.reminder(symbol, 3, data, dedup_key=dedup_key)
                            return result is not None
                
                return False
                
            finally:
                db.close()
                
        except Exception as e:
            logger.debug(f"[Monitor] 开盘价匹配异常 {symbol} {timeframe}: {e}")
            return False
    
    async def run_all_checks(self, symbol: str) -> dict:
        """
        运行所有监控检查
        
        Args:
            symbol: 交易对
        
        Returns:
            检查结果字典
        """
        results = {
            "symbol": symbol,
            "volume_alert": False,
            "rise_alert": False,
            "open_price_alerts": {},
            "error": ""
        }
        
        try:
            # 需求一：成交量监控
            results["volume_alert"] = await self.check_volume(symbol)
            
            # 需求二：涨幅监控
            results["rise_alert"] = await self.check_rise(symbol)
            
            # 需求三：开盘价匹配（各周期）
            timeframes = ['15m', '30m', '1h', '4h', '1d', '3d']
            for tf in timeframes:
                results["open_price_alerts"][tf] = await self.check_open_price_match(symbol, tf)
        except Exception as e:
            results["error"] = str(e)
            logger.debug(f"[Monitor] {symbol} 监控异常: {e}")
        
        # 记录到统计收集器
        monitor_result = MonitorResult(
            symbol=symbol,
            volume_alert=results["volume_alert"],
            rise_alert=results["rise_alert"],
            open_price_alerts=results["open_price_alerts"],
            error=results["error"]
        )
        monitor_stats_collector.add_result(monitor_result)
        
        return results


# 全局实例
monitor_service = MonitorService()

