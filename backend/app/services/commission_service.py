import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import Commission, Trade, CommissionStatus

logger = logging.getLogger(__name__)

class CommissionCalculator:
    """Service for calculating trading commissions"""
    
    def __init__(self):
        self.base_commission_rate = settings.COMMISSION_RATE  # 0.1% per trade
        self.profit_commission_rate = settings.PROFIT_COMMISSION_RATE  # 10% of profit
        self.min_commission = 0.10  # Minimum commission in USD
    
    def calculate_commission(self, trade: dict) -> dict:
        """Calculate commission for completed trade"""
        try:
            trade_volume = float(trade.get('volume', 0))
            profit_loss = float(trade.get('profit_loss', 0))
            
            # Volume-based commission (0.1% of trade volume)
            volume_commission = max(
                trade_volume * self.base_commission_rate,
                self.min_commission
            )
            
            # Profit commission (10% of profitable trades only)
            profit_commission = 0
            if profit_loss > 0:
                profit_commission = profit_loss * self.profit_commission_rate
            
            total_commission = volume_commission + profit_commission
            
            commission = {
                'trade_id': trade.get('id'),
                'volume_commission': round(volume_commission, 2),
                'profit_commission': round(profit_commission, 2),
                'total': round(total_commission, 2),
                'breakdown': {
                    'base_rate': self.base_commission_rate,
                    'profit_rate': self.profit_commission_rate,
                    'trade_volume': trade_volume,
                    'profit_loss': profit_loss,
                    'min_commission': self.min_commission
                }
            }
            
            logger.info(f"Commission calculated for trade {trade.get('id')}: ${commission['total']}")
            return commission
            
        except Exception as e:
            logger.error(f"Error calculating commission: {e}")
            raise
    
    def calculate_monthly_commission(self, trades: List[dict]) -> dict:
        """Calculate commission summary for a month"""
        try:
            total_volume = 0
            total_profit = 0
            total_commission = 0
            trade_count = 0
            profitable_trades = 0
            
            for trade in trades:
                trade_count += 1
                trade_volume = float(trade.get('volume', 0))
                profit_loss = float(trade.get('profit_loss', 0))
                
                total_volume += trade_volume
                
                if profit_loss > 0:
                    total_profit += profit_loss
                    profitable_trades += 1
            
            # Calculate commissions
            volume_commission = max(total_volume * self.base_commission_rate, self.min_commission * trade_count)
            profit_commission = total_profit * self.profit_commission_rate
            total_commission = volume_commission + profit_commission
            
            summary = {
                'period': {
                    'total_trades': trade_count,
                    'profitable_trades': profitable_trades,
                    'win_rate': (profitable_trades / trade_count * 100) if trade_count > 0 else 0
                },
                'volume': {
                    'total_volume': round(total_volume, 2),
                    'commission': round(volume_commission, 2)
                },
                'profit': {
                    'total_profit': round(total_profit, 2),
                    'commission': round(profit_commission, 2)
                },
                'total_commission': round(total_commission, 2),
                'breakdown': {
                    'volume_percentage': (volume_commission / total_commission * 100) if total_commission > 0 else 0,
                    'profit_percentage': (profit_commission / total_commission * 100) if total_commission > 0 else 0
                }
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error calculating monthly commission: {e}")
            raise
    
    def estimate_commission_for_strategy(self, strategy_config: dict) -> dict:
        """Estimate potential commission for a trading strategy"""
        try:
            # Extract strategy parameters
            max_risk = strategy_config.get('risk_management', {}).get('max_risk_per_trade', 2.0)
            expected_trades = strategy_config.get('expected_performance', {}).get('monthly_trades', 20)
            win_rate = strategy_config.get('expected_performance', {}).get('win_rate', 60) / 100
            profit_factor = strategy_config.get('expected_performance', {}).get('profit_factor', 1.5)
            
            # Estimate average trade size (based on risk)
            account_size = 10000  # Assuming $10k account
            avg_risk_amount = account_size * (max_risk / 100)
            
            # Estimate average profit/loss
            avg_win = avg_risk_amount * profit_factor
            avg_loss = avg_risk_amount
            avg_profit_per_trade = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
            
            # Estimate monthly volume (rough calculation)
            avg_volume_per_trade = avg_risk_amount * (1 + profit_factor) / 2
            estimated_monthly_volume = expected_trades * avg_volume_per_trade
            
            # Calculate estimated commissions
            monthly_volume_commission = estimated_monthly_volume * self.base_commission_rate
            expected_monthly_profit = expected_trades * avg_profit_per_trade
            monthly_profit_commission = max(0, expected_monthly_profit * self.profit_commission_rate)
            
            total_monthly_commission = monthly_volume_commission + monthly_profit_commission
            
            return {
                'estimation': {
                    'expected_monthly_trades': expected_trades,
                    'estimated_wins': int(expected_trades * win_rate),
                    'estimated_monthly_volume': round(estimated_monthly_volume, 2),
                    'estimated_monthly_profit': round(expected_monthly_profit, 2)
                },
                'commission_breakdown': {
                    'volume_commission': round(monthly_volume_commission, 2),
                    'profit_commission': round(monthly_profit_commission, 2),
                    'total_commission': round(total_monthly_commission, 2)
                },
                'per_trade_average': round(total_monthly_commission / expected_trades, 2) if expected_trades > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error estimating commission: {e}")
            raise

class CommissionSettlement:
    """Service for processing and settling commissions"""
    
    def __init__(self):
        self.calculator = CommissionCalculator()
    
    async def process_daily_commissions(self):
        """Process and settle daily pending commissions"""
        try:
            from app.core.database import get_db
            
            db = next(get_db())
            
            # Get pending commissions
            pending_commissions = db.query(Commission).filter(
                Commission.status == 'pending'
            ).all()
            
            processed_count = 0
            
            for commission in pending_commissions:
                try:
                    # Process each commission
                    await self._process_single_commission(commission, db)
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing commission {commission.id}: {e}")
                    commission.status = 'failed'
                    db.commit()
            
            db.close()
            logger.info(f"Processed {processed_count} commissions")
            
        except Exception as e:
            logger.error(f"Error in process_daily_commissions: {e}")
    
    async def _process_single_commission(self, commission: Commission, db: Session):
        """Process a single commission"""
        # Mark commission as processed
        commission.status = 'processed'
        commission.processed_at = datetime.utcnow()
        
        # Update user balance (this would integrate with payment system)
        # For now, just mark as processed
        logger.info(f"Commission {commission.id} processed: ${commission.amount}")
        
        # Generate commission invoice
        await self._generate_commission_invoice(commission, db)
    
    async def _generate_commission_invoice(self, commission: Commission, db: Session):
        """Generate commission invoice record"""
        try:
            # This would create an invoice record in a payment system
            # For now, just log the invoice
            logger.info(
                f"Invoice generated for commission {commission.id}: "
                f"${commission.amount} for user {commission.user_id}"
            )
            
        except Exception as e:
            logger.error(f"Error generating invoice: {e}")
    
    async def get_user_commission_summary(self, user_id: str, period_days: int = 30) -> dict:
        """Get commission summary for a user"""
        try:
            from app.core.database import get_db
            
            db = next(get_db())
            
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=period_days)
            
            # Get commissions for the period
            commissions = db.query(Commission).filter(
                Commission.user_id == user_id,
                Commission.created_at >= start_date,
                Commission.created_at <= end_date
            ).all()
            
            # Calculate summary
            total_amount = sum(c.amount for c in commissions)
            volume_commission = sum(c.volume_commission for c in commissions)
            profit_commission = sum(c.profit_commission for c in commissions)
            
            summary = {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': period_days
                },
                'summary': {
                    'total_commissions': len(commissions),
                    'total_amount': round(total_amount, 2),
                    'volume_commission': round(volume_commission, 2),
                    'profit_commission': round(profit_commission, 2)
                },
                'breakdown': [
                    {
                        'id': str(c.id),
                        'amount': float(c.amount),
                        'volume_commission': float(c.volume_commission),
                        'profit_commission': float(c.profit_commission),
                        'status': c.status,
                        'processed_at': c.processed_at.isoformat() if c.processed_at else None,
                        'created_at': c.created_at.isoformat()
                    }
                    for c in commissions
                ]
            }
            
            db.close()
            return summary
            
        except Exception as e:
            logger.error(f"Error getting user commission summary: {e}")
            raise
    
    async def get_platform_commission_stats(self, period_days: int = 30) -> dict:
        """Get platform-wide commission statistics"""
        try:
            from app.core.database import get_db
            
            db = next(get_db())
            
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=period_days)
            
            # Get all commissions for the period
            commissions = db.query(Commission).filter(
                Commission.created_at >= start_date,
                Commission.created_at <= end_date
            ).all()
            
            # Calculate statistics
            total_amount = sum(c.amount for c in commissions)
            volume_commission = sum(c.volume_commission for c in commissions)
            profit_commission = sum(c.profit_commission for c in commissions)
            
            # User breakdown
            user_stats = {}
            for commission in commissions:
                user_id = str(commission.user_id)
                if user_id not in user_stats:
                    user_stats[user_id] = {
                        'total_commission': 0,
                        'trade_count': 0
                    }
                user_stats[user_id]['total_commission'] += float(commission.amount)
                user_stats[user_id]['trade_count'] += 1
            
            # Sort users by commission amount
            top_users = sorted(
                user_stats.items(),
                key=lambda x: x[1]['total_commission'],
                reverse=True
            )[:10]
            
            stats = {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': period_days
                },
                'total_stats': {
                    'total_commissions': len(commissions),
                    'total_amount': round(total_amount, 2),
                    'volume_commission': round(volume_commission, 2),
                    'profit_commission': round(profit_commission, 2),
                    'average_commission': round(total_amount / len(commissions), 2) if commissions else 0
                },
                'unique_users': len(user_stats),
                'top_users': [
                    {
                        'user_id': user_id,
                        'total_commission': round(stats['total_commission'], 2),
                        'trade_count': stats['trade_count']
                    }
                    for user_id, stats in top_users
                ]
            }
            
            db.close()
            return stats
            
        except Exception as e:
            logger.error(f"Error getting platform commission stats: {e}")
            raise

# Global instances
commission_calculator = CommissionCalculator()
commission_settlement = CommissionSettlement()
