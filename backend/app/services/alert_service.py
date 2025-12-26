"""
提醒服务
=======
提供提醒相关的业务逻辑：去重检查、数据库入库、微信消息推送
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import httpx

from ..core.config import settings
from ..core.database import SessionLocal
from ..models.alert import Alert, AlertDedup


class AlertService:
    """提醒通知服务"""
    
    def __init__(self):
        self.webhook_url = settings.WECHAT_WEBHOOK_URL
        self.timeout = 10.0
    
    def _check_dedup_type3(self, db, symbol: str, dedup_key: str) -> bool:
        """检查需求三的去重：同一匹配对(D,E)只提醒一次"""
        from .config_service import config_service
        
        dedup_enabled = config_service.get_config_value(
            db, "3_dedup_enabled", str(settings.DEFAULT_3_DEDUP_ENABLED).lower()
        )
        
        if dedup_enabled.lower() != "true":
            return False
        
        dedup = db.query(AlertDedup).filter(
            AlertDedup.symbol == symbol,
            AlertDedup.alert_type == 3,
            AlertDedup.dedup_key == dedup_key
        ).first()
        
        if dedup:
            return True
        
        return False
    
    def _check_dedup_time_based(self, db, symbol: str, alert_type: int) -> bool:
        """
        检查基于时间的去重（用于需求一和需求二）
        在配置的间隔时间内不重复提醒
        
        Args:
            db: 数据库会话
            symbol: 交易对
            alert_type: 提醒类型 (1=成交量, 2=涨幅)
        
        Returns:
            True表示应跳过（在间隔内已有提醒），False表示可以发送
        """
        from .config_service import config_service
        
        # 获取对应类型的提醒间隔配置（分钟）
        if alert_type == 1:
            interval_minutes = int(config_service.get_config_float(
                db, "1_reminder_interval", settings.DEFAULT_1_REMINDER_INTERVAL
            ))
        elif alert_type == 2:
            interval_minutes = int(config_service.get_config_float(
                db, "2_reminder_interval", settings.DEFAULT_2_REMINDER_INTERVAL
            ))
        else:
            return False
        
        # 如果间隔为0，不进行去重
        if interval_minutes <= 0:
            return False
        
        # 查找该币种该类型的最后一条去重记录
        dedup = db.query(AlertDedup).filter(
            AlertDedup.symbol == symbol,
            AlertDedup.alert_type == alert_type
        ).order_by(AlertDedup.last_alert_time.desc()).first()
        
        if dedup:
            # 检查是否在间隔时间内
            time_threshold = datetime.utcnow() - timedelta(minutes=interval_minutes)
            if dedup.last_alert_time >= time_threshold:
                return True  # 在间隔内，应跳过
        
        return False
    
    def _update_dedup_record(self, db, symbol: str, alert_type: int, dedup_key: str = None):
        """
        更新或创建去重记录
        - 需求一和二：更新最后提醒时间（用于时间间隔去重）
        - 需求三：创建唯一匹配对记录
        """
        if alert_type == 3 and dedup_key:
            # 需求三：同一匹配对只提醒一次
            dedup = AlertDedup(
                symbol=symbol,
                alert_type=3,
                dedup_key=dedup_key,
                last_alert_time=datetime.utcnow()
            )
            db.add(dedup)
            db.commit()
        elif alert_type in (1, 2):
            # 需求一和二：更新或创建时间记录
            dedup = db.query(AlertDedup).filter(
                AlertDedup.symbol == symbol,
                AlertDedup.alert_type == alert_type
            ).first()
            
            if dedup:
                dedup.last_alert_time = datetime.utcnow()
            else:
                dedup = AlertDedup(
                    symbol=symbol,
                    alert_type=alert_type,
                    dedup_key=f"type{alert_type}_interval",
                    last_alert_time=datetime.utcnow()
                )
                db.add(dedup)
            db.commit()
    
    async def send_wechat_message(self, content: str) -> bool:
        """发送微信群机器人消息"""
        if not self.webhook_url:
            # print(f"[Reminder] 未配置微信Webhook URL，消息内容: {content}")
            return False
        
        payload = {"msgtype": "text", "text": {"content": content}}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.webhook_url, json=payload)
                result = response.json()
                if result.get("errcode") == 0:
                    print(f"[Reminder] 消息发送成功: {content[:50]}...")
                    return True
                else:
                    print(f"[Reminder] 消息发送失败: {result}")
                    return False
        except Exception as e:
            print(f"[Reminder] 发送消息异常: {e}")
            return False
    
    async def save_alert(self, symbol: str, alert_type: int, data: Dict[str, Any]) -> Alert:
        """保存提醒记录到数据库"""
        db = SessionLocal()
        try:
            alert = Alert(
                symbol=symbol,
                alert_type=alert_type,
                data=data,
                created_at=datetime.utcnow()
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)
            return alert
        finally:
            db.close()
    
    def _format_wechat_message(self, symbol: str, alert_type: int, data: Dict[str, Any]) -> str:
        """格式化微信消息"""
        type_names = {1: "成交量异常", 2: "涨幅异常", 3: "开盘价匹配"}
        type_name = type_names.get(alert_type, "未知类型")
        
        if alert_type == 1:
            detail = (
                f"15分钟成交量: {data['volume_15m']:,.2f}\n"
                f"8小时成交量: {data['volume_8h']:,.2f}\n"
                f"占比: {data['volume_ratio']:.1f}%"
            )
        elif alert_type == 2:
            detail = (
                f"涨幅: {data['rise_percent']:.2f}%\n"
                f"阈值: {data['rise_threshold']:.2f}%"
            )
        else:
            detail = (
                f"周期: {data['timeframe']}\n"
                f"最新开盘价: {data['price_d']:.4f} ({data['time_d']})\n"
                f"匹配开盘价: {data['price_e']:.4f} ({data['time_e']})\n"
                f"误差: {data['price_error']:.2f}%"
            )
        
        return f"""🔔 K线监控提醒

【类型】{type_name}
【币种】{symbol}
【时间】{now_beijing().strftime('%Y-%m-%d %H:%M:%S')}
【详情】{detail}"""
    
    async def reminder(
        self,
        symbol: str,
        alert_type: int,
        data: Dict[str, Any],
        send_wechat: bool = True,
        dedup_key: str = None
    ) -> Optional[Alert]:
        """完整的提醒流程：去重检查 + 保存记录 + 发送微信通知"""
        # 需求一和二：时间间隔去重检查
        if alert_type in (1, 2):
            db = SessionLocal()
            try:
                if self._check_dedup_time_based(db, symbol, alert_type):
                    return None
            finally:
                db.close()
        
        # 需求三去重检查
        if alert_type == 3 and dedup_key:
            db = SessionLocal()
            try:
                if self._check_dedup_type3(db, symbol, dedup_key):
                    return None
            finally:
                db.close()
        
        alert = await self.save_alert(symbol, alert_type, data)
        
        db = SessionLocal()
        try:
            self._update_dedup_record(db, symbol, alert_type, dedup_key)
        finally:
            db.close()
        
        if send_wechat:
            wechat_content = self._format_wechat_message(symbol, alert_type, data)
            await self.send_wechat_message(wechat_content)
        
        return alert


alert_service = AlertService()
