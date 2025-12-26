"""
监控服务
=======
实现三大需求的核心监控逻辑

功能：
- 需求一：成交量监控 - 15分钟成交量与8小时成交量对比
- 需求二：涨幅监控 - 15分钟累计涨幅检测
- 需求三：开盘价匹配 - 历史开盘价匹配检测

性能优化：
- 批量获取全局配置，减少数据库查询
- 并行执行独立的监控检查
- 复用K线数据，避免重复查询
- 单次数据库连接复用
"""
import asyncio
from datetime import timedelta
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.database import SessionLocal
from ..core.logger import logger
from ..core.stats import monitor_stats_collector, MonitorResult
from ..core.timezone import now_beijing
from ..models.kline import PriceKline
from ..models.config import SymbolConfig
from .binance_client import binance_client, BinanceClient
from .alert_service import alert_service
from .config_service import config_service


class MonitorService:
    """监控服务 - 实现三大需求的核心逻辑"""
    
    # 缓存全局配置，避免每个交易对都查询
    _global_config_cache: Dict[str, Any] = {}
    _config_cache_time: Optional[Any] = None
    _config_cache_ttl: int = 60  # 配置缓存60秒
    
    def __init__(self):
        self.binance = binance_client
        self.alert = alert_service
    
    async def _get_1m_klines_cached(self, symbol: str, limit: int = 481) -> List[dict]:
        """
        获取1分钟K线数据（用于成交量和涨幅计算）
        
        Args:
            symbol: 交易对
            limit: 获取数量（默认481条，覆盖8小时+1条）
        
        Returns:
            K线数据列表
        """
        return await self.binance.get_klines(symbol, "1m", limit=limit)
    
    def _get_global_configs(self, db: Session) -> Dict[str, Any]:
        """
        批量获取全局配置（带缓存）
        
        Returns:
            全局配置字典
        """
        now = now_beijing()
        
        # 检查缓存是否有效
        if (self._config_cache_time and 
            (now - self._config_cache_time).total_seconds() < self._config_cache_ttl):
            return self._global_config_cache
        
        # 批量获取所有需要的配置
        self._global_config_cache = {
            "volume_percent": config_service.get_config_float(db, "1_volume_percent", settings.DEFAULT_1_VOLUME_PERCENT),
            "rise_percent": config_service.get_config_float(db, "2_rise_percent", settings.DEFAULT_2_RISE_PERCENT),
            "price_error": config_service.get_config_float(db, "3_price_error", settings.DEFAULT_3_PRICE_ERROR),
            "middle_kline_cnt": int(config_service.get_config_float(db, "3_middle_kline_cnt", settings.DEFAULT_3_MIDDLE_KLINE_CNT)),
            "fake_kline_cnt": int(config_service.get_config_float(db, "3_fake_kline_cnt", settings.DEFAULT_3_FAKE_KLINE_CNT)),
        }
        self._config_cache_time = now
        
        return self._global_config_cache
    
    def _get_symbol_configs_batch(self, db: Session, symbol: str, intervals: List[str]) -> Dict[str, SymbolConfig]:
        """
        批量获取币种的个性化配置
        
        Args:
            db: 数据库会话
            symbol: 交易对
            intervals: K线间隔列表
        
        Returns:
            {interval: SymbolConfig} 映射
        """
        configs = db.query(SymbolConfig).filter(
            SymbolConfig.symbol == symbol,
            SymbolConfig.interval.in_(intervals)
        ).all()
        
        return {c.interval: c for c in configs}
    
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
    
    async def check_volume_with_klines(self, symbol: str, klines_1m: List[dict], percent: float) -> bool:
        """
        需求一：成交量监控（使用预加载的K线数据）
        
        计算15分钟成交量A与8小时成交量B，判断A >= B * percent / 100
        
        Args:
            symbol: 交易对
            klines_1m: 预加载的1分钟K线数据
            percent: 成交量阈值百分比
        """
        try:
            if len(klines_1m) <= 1:
                return False
            
            # 跳过最后一条（未收盘），计算已收盘K线的成交量
            closed_klines = klines_1m[:-1] if len(klines_1m) > 1 else []
            
            # 计算15分钟成交量（取最近15条）
            volume_15m = sum(k["volume"] for k in closed_klines[-15:]) if len(closed_klines) >= 15 else 0
            # 计算8小时成交量（取最近480条）
            volume_8h = sum(k["volume"] for k in closed_klines[-480:]) if len(closed_klines) >= 1 else 0
            
            threshold = volume_8h * percent / 100
            
            if volume_15m >= threshold:
                volume_ratio = (volume_15m / volume_8h * 100) if volume_8h > 0 else 0
                data = {
                    "volume_15m": volume_15m,
                    "volume_8h": volume_8h,
                    "volume_ratio": volume_ratio,
                    "volume_threshold": percent
                }
                result = await self.alert.reminder(symbol, 1, data)
                return result is not None
            
            return False
            
        except Exception as e:
            logger.debug(f"[Monitor] 成交量监控异常 {symbol}: {e}")
            return False
    
    async def check_volume(self, symbol: str) -> bool:
        """
        需求一：成交量监控（兼容旧接口）
        
        计算15分钟成交量A与8小时成交量B，判断A >= B * percent / 100
        """
        try:
            db = SessionLocal()
            try:
                percent = config_service.get_config_float(db, "1_volume_percent", settings.DEFAULT_1_VOLUME_PERCENT)
            finally:
                db.close()
            
            klines_1m = await self._get_1m_klines_cached(symbol, 481)
            return await self.check_volume_with_klines(symbol, klines_1m, percent)
            
        except Exception as e:
            logger.debug(f"[Monitor] 成交量监控异常 {symbol}: {e}")
            return False
    
    async def check_rise_with_klines(self, symbol: str, klines_1m: List[dict], threshold: float) -> bool:
        """
        需求二：涨幅监控（使用预加载的K线数据）
        
        计算15分钟累计涨幅C，判断C >= threshold
        
        Args:
            symbol: 交易对
            klines_1m: 预加载的1分钟K线数据
            threshold: 涨幅阈值
        """
        try:
            if len(klines_1m) <= 2:
                return False
            
            # 跳过最后一条（未收盘），取最近15条已收盘K线
            closed_klines = klines_1m[:-1] if len(klines_1m) > 1 else []
            if len(closed_klines) < 15:
                return False
            
            recent_15 = closed_klines[-15:]
            first_open = recent_15[0]["open"]
            last_close = recent_15[-1]["close"]
            
            if first_open == 0:
                return False
            
            price_change = ((last_close - first_open) / first_open) * 100
            
            if price_change >= threshold:
                data = {
                    "rise_percent": price_change,
                    "rise_threshold": threshold,
                    "rise_start_price": first_open,
                    "rise_end_price": last_close
                }
                result = await self.alert.reminder(symbol, 2, data)
                return result is not None
            
            return False
            
        except Exception as e:
            logger.debug(f"[Monitor] 涨幅监控异常 {symbol}: {e}")
            return False
    
    async def check_rise(self, symbol: str) -> bool:
        """
        需求二：涨幅监控（兼容旧接口）
        
        计算15分钟累计涨幅C，判断C >= threshold
        """
        try:
            db = SessionLocal()
            try:
                threshold = config_service.get_config_float(db, "2_rise_percent", settings.DEFAULT_2_RISE_PERCENT)
            finally:
                db.close()
            
            klines_1m = await self._get_1m_klines_cached(symbol, 16)
            return await self.check_rise_with_klines(symbol, klines_1m, threshold)
            
        except Exception as e:
            logger.debug(f"[Monitor] 涨幅监控异常 {symbol}: {e}")
            return False
    
    async def check_open_price_match_with_db(self, symbol: str, timeframe: str, db: Session, global_configs: Dict[str, Any]) -> bool:
        """
        需求三：开盘价匹配（使用共享数据库连接）
        
        匹配历史开盘价，误差≤阈值且中间满足条件
        
        Args:
            symbol: 交易对
            timeframe: K线周期
            db: 共享的数据库会话
            global_configs: 全局配置字典
        """
        try:
            global_price_error = global_configs["price_error"]
            global_middle_kline_cnt = global_configs["middle_kline_cnt"]
            global_fake_kline_cnt = global_configs["fake_kline_cnt"]
            
            # 获取币种+间隔的个性化配置（优先级高于全局配置）
            price_error = self._get_symbol_price_error(db, symbol, timeframe, global_price_error)
            middle_kline_cnt = self._get_symbol_middle_kline_cnt(db, symbol, timeframe, global_middle_kline_cnt)
            fake_count_n = self._get_symbol_fake_kline_cnt(db, symbol, timeframe, global_fake_kline_cnt)
            
            now = now_beijing()
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
                            "middle_count": interval_count,
                            "middle_count_threshold": fake_count_n
                        }
                        result = await self.alert.reminder(symbol, 3, data, dedup_key=dedup_key)
                        return result is not None
            
            return False
                
        except Exception as e:
            logger.debug(f"[Monitor] 开盘价匹配异常 {symbol} {timeframe}: {e}")
            return False
    
    async def check_open_price_match(self, symbol: str, timeframe: str) -> bool:
        """
        需求三：开盘价匹配（兼容旧接口）
        
        匹配历史开盘价，误差≤阈值且中间满足条件
        """
        try:
            db = SessionLocal()
            try:
                global_configs = self._get_global_configs(db)
                return await self.check_open_price_match_with_db(symbol, timeframe, db, global_configs)
            finally:
                db.close()
                
        except Exception as e:
            logger.debug(f"[Monitor] 开盘价匹配异常 {symbol} {timeframe}: {e}")
            return False
    
    async def run_all_checks(self, symbol: str) -> dict:
        """
        运行所有监控检查（优化版：并行执行 + 数据复用）
        
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
            # 1. 预加载共享数据（一次性获取）
            db = SessionLocal()
            try:
                global_configs = self._get_global_configs(db)
                
                # 2. 获取1分钟K线数据（成交量和涨幅共用）
                klines_1m = await self._get_1m_klines_cached(symbol, 481)
                
                # 3. 并行执行所有监控检查
                timeframes = ['15m', '30m', '1h', '4h', '1d', '3d']
                
                # 创建所有任务
                tasks = [
                    # 需求一：成交量监控
                    self.check_volume_with_klines(symbol, klines_1m, global_configs["volume_percent"]),
                    # 需求二：涨幅监控
                    self.check_rise_with_klines(symbol, klines_1m, global_configs["rise_percent"]),
                ]
                
                # 需求三：开盘价匹配（各周期）- 使用共享db连接
                for tf in timeframes:
                    tasks.append(self.check_open_price_match_with_db(symbol, tf, db, global_configs))
                
                # 并行执行所有任务
                all_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 解析结果
                results["volume_alert"] = all_results[0] if not isinstance(all_results[0], Exception) else False
                results["rise_alert"] = all_results[1] if not isinstance(all_results[1], Exception) else False
                
                for i, tf in enumerate(timeframes):
                    result = all_results[2 + i]
                    results["open_price_alerts"][tf] = result if not isinstance(result, Exception) else False
                    
            finally:
                db.close()
                
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

