"""
币安API客户端
=============
封装币安合约API调用与数据转换

功能：
- 获取所有USDT永续合约交易对
- 同步K线数据到数据库
- 获取K线数据（从数据库读取）
- 获取成交量和价格变化数据
- 清理过期K线数据
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from binance.client import Client
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.database import SessionLocal
from ..core.logger import logger
from ..core.stats import sync_stats_collector, SyncResult
from ..models.kline import PriceKline


# 支持的K线周期列表
SUPPORTED_INTERVALS = ["1m", "15m", "30m", "1h", "4h", "1d", "3d"]


class BinanceClient:
    """币安合约API客户端"""
    
    # 同步节流间隔（秒）- 同一(symbol, interval)组合在此时间内只同步一次
    SYNC_THROTTLE_SECONDS = 30
    
    # 增量同步时获取的最大K线数量（1-5条）
    INCREMENTAL_SYNC_LIMIT = 5
    
    # 数据库存储限制天数（按周期区分）
    DATA_RETENTION_DAYS = 90
    
    # 各周期数据保留天数配置
    INTERVAL_RETENTION_DAYS = {
        "1m": 1,      # 1分钟K线保留1天
        "15m": 30,    # 15分钟K线保留30天
        "30m": 30,    # 30分钟K线保留30天
        "1h": 30,     # 1小时K线保留30天
        "4h": 90,     # 4小时K线保留90天
        "1d": 90,     # 日K线保留90天
        "3d": 90,     # 3日K线保留90天
    }
    
    # API速率限制配置
    API_RATE_LIMIT_DELAY = 0.1  # 每次API请求间隔（秒）
    API_MAX_RETRIES = 5  # 最大重试次数
    API_RETRY_BASE_DELAY = 0.5  # 重试基础延迟（秒）
    
    # 时间周期到分钟数的映射
    INTERVAL_TO_MINUTES = {
        "1m": 1,
        "3m": 3,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "2h": 120,
        "4h": 240,
        "6h": 360,
        "8h": 480,
        "12h": 720,
        "1d": 1440,
        "3d": 4320,
        "1w": 10080,
        "1M": 43200,
    }
    
    # interval到Binance API常量的映射
    INTERVAL_TO_BINANCE = {
        "1m": Client.KLINE_INTERVAL_1MINUTE,
        "15m": Client.KLINE_INTERVAL_15MINUTE,
        "30m": Client.KLINE_INTERVAL_30MINUTE,
        "1h": Client.KLINE_INTERVAL_1HOUR,
        "4h": Client.KLINE_INTERVAL_4HOUR,
        "1d": Client.KLINE_INTERVAL_1DAY,
        "3d": Client.KLINE_INTERVAL_3DAY,
    }
    
    # 各周期初始同步的最大天数限制
    INTERVAL_MAX_INITIAL_DAYS = {
        "1m": 1,
        "15m": 7,  
        "30m": 15,  
        "1h": 30,    
        "4h": 60,  
        "1d": 90,  
        "3d": 90, 
    }
    
    def __init__(self):
        self._client = None
        # (symbol, interval) -> last sync time
        self._last_sync_time: dict[tuple[str, str], datetime] = {}
        # 固定分钟窗口速率限制（每分钟0秒重置，1分钟内最多1200次请求）
        self._request_count: int = 0  # 当前分钟的请求计数
        self._current_minute: int = -1  # 当前分钟标记（用于检测分钟切换）
        # 速率限制锁（仅用于速率检查，不锁定整个API调用）
        self._rate_limit_lock: asyncio.Lock = asyncio.Lock()
    
    @property
    def client(self) -> Client:
        """延迟初始化 Binance Client"""
        if self._client is None:
            self._client = Client(
                api_key=settings.BINANCE_API_KEY or "",
                api_secret=settings.BINANCE_API_SECRET or "",
                requests_params={'timeout': 30}
            )
        return self._client
    
    def _get_db(self) -> Session:
        """获取数据库会话"""
        return SessionLocal()
    
    def _parse_kline(self, k: list) -> dict:
        """
        解析K线原始数据
        
        Args:
            k: K线原始数据列表
        
        Returns:
            解析后的K线数据字典
        """
        return {
            "open_time": datetime.utcfromtimestamp(k[0] / 1000),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
            "close_time": datetime.utcfromtimestamp(k[6] / 1000),
            "quote_volume": float(k[7]),
            "trades": int(k[8]),
            "taker_buy_volume": float(k[9]),
            "taker_buy_quote_volume": float(k[10]),
        }
    
    # ========== API方法 ==========
    
    async def _check_rate_limit(self):
        """
        检查并执行速率限制（固定分钟窗口算法）
        币安API限制：1分钟内最多1200次请求
        每分钟0秒重置计数器
        """
        async with self._rate_limit_lock:
            now = datetime.now()
            current_minute = now.minute + now.hour * 60  # 使用小时+分钟作为分钟标记
            
            # 检测分钟切换，重置计数器
            if current_minute != self._current_minute:
                self._current_minute = current_minute
                self._request_count = 0
            
            # 如果达到限制，等待到下一分钟
            if self._request_count >= 1150:  # 留50个缓冲
                # 计算距离下一分钟0秒的等待时间
                seconds_to_wait = 60 - now.second + 0.1
                logger.warning(f"API速率限制：等待{seconds_to_wait:.1f}秒到下一分钟")
                await asyncio.sleep(seconds_to_wait)
                # 重置计数器
                now = datetime.now()
                self._current_minute = now.minute + now.hour * 60
                self._request_count = 0
            
            # 增加请求计数
            self._request_count += 1
    
    async def _rate_limited_api_call(self, api_func, **kwargs):
        """
        带速率限制和重试机制的API调用
        优化：移除全局锁，允许真正的并发API调用
        
        Args:
            api_func: API函数
            **kwargs: API参数
        
        Returns:
            API调用结果
        """
        last_exception = None
        for attempt in range(self.API_MAX_RETRIES):
            try:
                # 速率限制检查（仅锁定检查部分，不锁定API调用）
                await self._check_rate_limit()
                
                # 最小延迟（优化为0.01秒）
                await asyncio.sleep(self.API_RATE_LIMIT_DELAY)
                
                # 并发执行API调用
                result = await asyncio.to_thread(api_func, **kwargs)
                return result
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()
                
                # 检查是否是速率限制或网络错误
                is_retryable = any(x in error_str for x in [
                    'rate limit', 'too many request', '429', '-1015', 
                    'ip banned', 'request limit', 'exceed',
                    'timeout', 'timed out', 'connection error', 'connection refused',
                    'network is unreachable', 'remote disconnected'
                ])
                
                if is_retryable:
                    # 指数退避重试
                    delay = self.API_RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(f"API调用异常(速率限制/网络错误)，{delay:.1f}秒后重试 (尝试 {attempt + 1}/{self.API_MAX_RETRIES}): {e}")
                    await asyncio.sleep(delay)
                else:
                    # 非速率限制错误，直接抛出
                    raise e
        
        # 所有重试都失败
        raise Exception(f"API调用失败，已重试{self.API_MAX_RETRIES}次: {last_exception}")

    async def get_all_futures_symbols(self) -> List[str]:
        """
        获取所有Binance USDT合约交易对
        
        Returns:
            交易对列表 (如 ['BTCUSDT', 'ETHUSDT', ...])
        """
        try:
            exchange_info = await self._rate_limited_api_call(
                self.client.futures_exchange_info
            )
            
            symbols = []
            for s in exchange_info.get('symbols', []):
                # 只获取USDT永续合约，状态为TRADING的交易对
                if (s.get('quoteAsset') == 'USDT' and 
                    s.get('contractType') == 'PERPETUAL' and
                    s.get('status') == 'TRADING'):
                    symbols.append(s['symbol'])
            
            return sorted(symbols)
        except Exception as e:
            logger.error(f"[Binance] 获取合约交易对列表失败: {e}")
            raise e

    # ========== K线数据同步 ==========
    
    async def sync_klines(
        self,
        symbol: str,
        interval: str = "15m",
        initial_days: int = 3,
        force: bool = False
    ) -> int:
        """
        同步指定周期的K线数据到数据库
        
        Args:
            symbol: 交易对
            interval: K线周期
            initial_days: 无数据时同步的历史天数（默认3天）
            force: 强制同步，忽略节流
        
        Returns:
            新增的K线数量
        """
        if interval not in self.INTERVAL_TO_BINANCE:
            logger.warning(f"[Binance] {symbol} {interval} 不支持的周期")
            return 0
        
        # 节流检查 - 基于(symbol, interval)组合
        cache_key = (symbol, interval)
        now = datetime.utcnow()
        if not force and cache_key in self._last_sync_time:
            elapsed = (now - self._last_sync_time[cache_key]).total_seconds()
            if elapsed < self.SYNC_THROTTLE_SECONDS:
                logger.debug(f"[Binance] {symbol} {interval} 节流跳过 (距上次{elapsed:.1f}秒)")
                return 0
        
        self._last_sync_time[cache_key] = now
        
        interval_minutes = self.INTERVAL_TO_MINUTES.get(interval, 1)
        binance_interval = self.INTERVAL_TO_BINANCE[interval]
        
        db = self._get_db()
        try:
            # 获取数据库中该周期的最新K线时间
            latest_kline = db.query(PriceKline).filter(
                and_(PriceKline.symbol == symbol, PriceKline.interval == interval)
            ).order_by(desc(PriceKline.open_time)).first()
            
            # 用于增量同步的起始时间戳
            start_ts = None
            
            if latest_kline:
                # 增量同步：从数据库最新时间开始获取
                start_time = latest_kline.open_time + timedelta(minutes=interval_minutes)
                periods_needed = int((now - start_time).total_seconds() / 60 / interval_minutes)
                logger.debug(f"[Binance] {symbol} {interval} 增量同步: 最新={latest_kline.open_time}, 需要{periods_needed}条")
                
                if periods_needed <= 0:
                    # 获取最新2条K线（包含当前正在形成的）
                    limit = 2
                    logger.debug(f"[Binance] {symbol} {interval} 更新当前K线: 获取最新{limit}条")
                elif periods_needed > self.INCREMENTAL_SYNC_LIMIT:
                    # 缺失较多，使用startTime从数据库最新时间开始获取
                    start_ts = int(start_time.replace(tzinfo=timezone.utc).timestamp() * 1000)
                    limit = min(periods_needed + 1, 1500)  
                    logger.debug(f"[Binance] {symbol} {interval} 大量补齐: 从{start_time}开始获取{limit}条")
                else:
                    limit = periods_needed + 2 
            else:
                # 初始同步：获取历史数据，使用该周期的最大天数限制
                max_days = self.INTERVAL_MAX_INITIAL_DAYS.get(interval, initial_days)
                actual_days = min(initial_days, max_days)
                limit = int(actual_days * 24 * 60 / interval_minutes)
                # logger.info(f"[Binance] {symbol} {interval} 初始同步: 获取{actual_days}天约{limit}条")
            
            # 从API获取数据
            all_klines = []
            remaining = limit
            end_ts = None
            
            while remaining > 0:
                batch_limit = min(remaining, 1500)
                params = {
                    "symbol": symbol,
                    "interval": binance_interval,
                    "limit": batch_limit
                }
                # 增量同步时使用startTime从数据库最新时间开始
                if start_ts and not end_ts:
                    params["startTime"] = start_ts
                if end_ts:
                    params["endTime"] = end_ts
                
                logger.debug(f"[Binance] {symbol} {interval} API请求: limit={batch_limit}, startTime={start_ts}, endTime={end_ts}")
                
                # 使用带速率限制和重试的API调用
                klines_raw = await self._rate_limited_api_call(
                    self.client.futures_klines, **params
                )
                
                logger.debug(f"[Binance] {symbol} {interval} API返回: {len(klines_raw) if klines_raw else 0}条")
                
                if not klines_raw:
                    logger.warning(f"[Binance] {symbol} {interval} API返回空数据!")
                    break
                
                for k in klines_raw:
                    parsed = self._parse_kline(k)
                    # 包含所有K线（包括未收盘的），以便实时更新数据
                    all_klines.append(parsed)
                
                remaining -= len(klines_raw)
                if klines_raw and remaining > 0:
                    end_ts = klines_raw[0][0] - 1
                else:
                    break
            
            logger.debug(f"[Binance] {symbol} {interval} 待写入: {len(all_klines)}条")
            
            # 批量插入或更新数据库（优化性能）
            inserted_count = 0
            updated_count = 0
            
            if not all_klines:
                return 0
            
            # 批量查询已存在的K线
            open_times = [k["open_time"] for k in all_klines]
            existing_klines = db.query(PriceKline).filter(
                and_(
                    PriceKline.symbol == symbol,
                    PriceKline.interval == interval,
                    PriceKline.open_time.in_(open_times)
                )
            ).all()
            
            # 创建已存在K线的映射
            existing_map = {k.open_time: k for k in existing_klines}
            
            # 分离新增和更新的数据
            to_insert = []
            to_update = []
            
            for kline_data in all_klines:
                open_time = kline_data["open_time"]
                if open_time not in existing_map:
                    # 新增
                    to_insert.append({
                        "symbol": symbol,
                        "interval": interval,
                        **kline_data
                    })
                    inserted_count += 1
                else:
                    # 更新
                    existing = existing_map[open_time]
                    to_update.append({
                        "id": existing.id,
                        "open": kline_data["open"],
                        "high": kline_data["high"],
                        "low": kline_data["low"],
                        "close": kline_data["close"],
                        "volume": kline_data["volume"],
                        "quote_volume": kline_data["quote_volume"],
                        "trades": kline_data["trades"],
                        "taker_buy_volume": kline_data["taker_buy_volume"],
                        "taker_buy_quote_volume": kline_data["taker_buy_quote_volume"]
                    })
                    updated_count += 1
            
            # 批量插入
            if to_insert:
                db.bulk_insert_mappings(PriceKline, to_insert)
            
            # 批量更新
            if to_update:
                db.bulk_update_mappings(PriceKline, to_update)
            
            db.commit()
            
            # 记录同步结果到统计收集器
            result = SyncResult(
                symbol=symbol,
                interval=interval,
                success=True,
                inserted=inserted_count,
                updated=updated_count
            )
            sync_stats_collector.add_result(result)
            
            # 详细日志降级为DEBUG
            logger.debug(f"[Binance] {symbol} {interval} 写入完成: 新增{inserted_count}条, 更新{updated_count}条")
            
            return inserted_count + updated_count
        except Exception as e:
            db.rollback()
            
            # 记录失败结果到统计收集器
            result = SyncResult(
                symbol=symbol,
                interval=interval,
                success=False,
                error=str(e)
            )
            sync_stats_collector.add_result(result)
            
            # 错误日志仅记录简要信息
            logger.debug(f"[Binance] {symbol} {interval} 同步异常: {e}")
            raise e
        finally:
            db.close()
    
    # ========== K线数据获取 ==========
    
    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500,
        use_db: bool = True
    ) -> List[dict]:
        """
        获取K线数据（从数据库读取）
        
        Args:
            symbol: 交易对
            interval: K线周期
            limit: 获取数量
            use_db: 是否从数据库读取
        
        Returns:
            K线数据列表
        """
        if use_db and interval in self.INTERVAL_TO_BINANCE:
            try:
                return await self._get_klines_from_db(symbol, interval, limit)
            except Exception as e:
                logger.error(f"从数据库获取K线失败: {e}", exc_info=True)
                return []
        
        return []
    
    async def _get_klines_from_db(self, symbol: str, interval: str, limit: int) -> List[dict]:
        """
        从数据库直接获取对应周期的K线数据
        
        Args:
            symbol: 交易对
            interval: K线周期
            limit: 获取数量
        
        Returns:
            K线数据列表
        """
        db = self._get_db()
        try:
            klines = db.query(PriceKline).filter(
                and_(PriceKline.symbol == symbol, PriceKline.interval == interval)
            ).order_by(desc(PriceKline.open_time)).limit(limit).all()
            
            return [{
                "open_time": k.open_time,
                "open": k.open,
                "high": k.high,
                "low": k.low,
                "close": k.close,
                "volume": k.volume,
                "close_time": k.close_time,
                "quote_volume": k.quote_volume,
                "trades": k.trades,
                "taker_buy_volume": k.taker_buy_volume,
                "taker_buy_quote_volume": k.taker_buy_quote_volume,
            } for k in reversed(klines)]
        finally:
            db.close()
    
    # ========== 便捷方法 ==========
    
    async def get_recent_volume(self, symbol: str, minutes: int) -> float:
        """
        获取最近N分钟的成交量（只统计已收盘的K线）
        
        Args:
            symbol: 交易对
            minutes: 分钟数
        
        Returns:
            成交量
        """
        # 获取 minutes + 1 条数据，包含当前未收盘的K线
        klines = await self.get_klines(symbol, "1m", limit=minutes + 1)
        # 跳过最后一条（最新的、未收盘的K线），只计算已收盘的K线
        if len(klines) <= 1:
            return 0.0
        # 取前 minutes 条已收盘的K线数据（跳过最后一条）
        closed_klines = klines[:minutes]
        return sum(k["volume"] for k in closed_klines)
    
    async def get_price_change(self, symbol: str, minutes: int) -> float:
        """
        获取最近N分钟的价格变化百分比（只统计已收盘的K线）
        
        Args:
            symbol: 交易对
            minutes: 分钟数
        
        Returns:
            价格变化百分比
        """
        result = await self.get_price_change_with_prices(symbol, minutes)
        return result["change_percent"]
    
    async def get_price_change_with_prices(self, symbol: str, minutes: int) -> dict:
        """
        获取最近N分钟的价格变化信息（包含起始和结束价格）
        
        Args:
            symbol: 交易对
            minutes: 分钟数
        
        Returns:
            包含 change_percent, start_price, end_price 的字典
        """
        klines = await self.get_klines(symbol, "1m", limit=minutes + 1)
        if len(klines) <= 2:
            return {"change_percent": 0.0, "start_price": 0.0, "end_price": 0.0}

        closed_klines = klines[:minutes]
        first_open = closed_klines[0]["open"]
        last_close = closed_klines[-1]["close"]
        
        if first_open == 0:
            return {"change_percent": 0.0, "start_price": first_open, "end_price": last_close}
        
        change_percent = ((last_close - first_open) / first_open) * 100
        return {
            "change_percent": change_percent,
            "start_price": first_open,
            "end_price": last_close
        }
    
    
    async def cleanup_old_klines(self, days_to_keep: int = None) -> dict:
        """
        清理过期的K线数据（按周期区分保留天数）
        
        保留策略：
        - 1m: 1天
        - 15m, 30m, 1h: 30天
        - 4h, 1d, 3d: 90天
        
        Args:
            days_to_keep: 统一保留天数（如果指定，则忽略按周期配置）
        
        Returns:
            各周期删除的记录数字典
        """
        db = self._get_db()
        deleted_counts = {}
        total_deleted = 0
        
        try:
            if days_to_keep is not None:
                # 使用统一的保留天数
                cutoff_time = datetime.utcnow() - timedelta(days=days_to_keep)
                deleted = db.query(PriceKline).filter(PriceKline.open_time < cutoff_time).delete()
                total_deleted = deleted
                deleted_counts["all"] = deleted
            else:
                # 按周期分别清理
                for interval, retention_days in self.INTERVAL_RETENTION_DAYS.items():
                    cutoff_time = datetime.utcnow() - timedelta(days=retention_days)
                    deleted = db.query(PriceKline).filter(
                        and_(
                            PriceKline.interval == interval,
                            PriceKline.open_time < cutoff_time
                        )
                    ).delete()
                    if deleted > 0:
                        deleted_counts[interval] = deleted
                        total_deleted += deleted
            
            db.commit()
            deleted_counts["total"] = total_deleted
            return deleted_counts
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()


# 全局实例
binance_client = BinanceClient()

