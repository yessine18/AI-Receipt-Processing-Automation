"""
Database module for Discord Bot
Direct database access for advanced queries
"""
import os
import asyncpg
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger('database')


class Database:
    """Database connection and queries"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.pool = None
    
    async def connect(self):
        """Create database connection pool"""
        if not self.pool:
            try:
                self.pool = await asyncpg.create_pool(self.database_url)
                logger.info('Database pool created')
            except Exception as e:
                logger.error(f'Failed to create database pool: {e}')
                raise
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info('Database pool closed')
    
    async def get_user_receipts(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's receipts"""
        try:
            if not self.pool:
                await self.connect()
            
            query = """
                SELECT 
                    id, vendor, date, total_amount, currency,
                    tax_amount, category, processing_status,
                    created_at, processed_at
                FROM receipts
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """
            
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, user_id, limit, offset)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f'Error fetching user receipts: {e}')
            return []
    
    async def get_receipt_by_id(
        self,
        receipt_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get specific receipt"""
        try:
            if not self.pool:
                await self.connect()
            
            query = """
                SELECT *
                FROM receipts
                WHERE id = $1 AND user_id = $2
            """
            
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, receipt_id, user_id)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f'Error fetching receipt: {e}')
            return None
    
    async def search_receipts(
        self,
        user_id: str,
        vendor: Optional[str] = None,
        category: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search receipts with filters"""
        try:
            if not self.pool:
                await self.connect()
            
            conditions = ['user_id = $1']
            params = [user_id]
            param_count = 1
            
            if vendor:
                param_count += 1
                conditions.append(f'vendor ILIKE ${param_count}')
                params.append(f'%{vendor}%')
            
            if category:
                param_count += 1
                conditions.append(f'category ILIKE ${param_count}')
                params.append(f'%{category}%')
            
            if date_from:
                param_count += 1
                conditions.append(f'date >= ${param_count}')
                params.append(date_from)
            
            if date_to:
                param_count += 1
                conditions.append(f'date <= ${param_count}')
                params.append(date_to)
            
            param_count += 1
            params.append(limit)
            
            query = f"""
                SELECT 
                    id, vendor, date, total_amount, currency,
                    tax_amount, category, processing_status,
                    created_at
                FROM receipts
                WHERE {' AND '.join(conditions)}
                ORDER BY date DESC
                LIMIT ${param_count}
            """
            
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f'Error searching receipts: {e}')
            return []
    
    async def get_expense_summary(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get expense summary for a period"""
        try:
            if not self.pool:
                await self.connect()
            
            date_from = datetime.now() - timedelta(days=days)
            
            query = """
                SELECT 
                    COUNT(*) as total_count,
                    COALESCE(SUM(total_amount), 0) as total_amount,
                    COALESCE(SUM(tax_amount), 0) as total_tax,
                    COALESCE(AVG(total_amount), 0) as avg_amount,
                    category,
                    COUNT(*) as category_count,
                    SUM(total_amount) as category_total
                FROM receipts
                WHERE user_id = $1 
                    AND created_at >= $2
                    AND processing_status = 'done'
                GROUP BY category
                ORDER BY category_total DESC
            """
            
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, user_id, date_from)
                
                # Calculate totals
                total_count = sum(row['category_count'] for row in rows)
                total_amount = sum(row['category_total'] for row in rows)
                total_tax = sum(float(row.get('total_tax', 0)) for row in rows)
                
                categories = [
                    {
                        'category': row['category'] or 'Uncategorized',
                        'count': row['category_count'],
                        'total': float(row['category_total'])
                    }
                    for row in rows
                ]
                
                return {
                    'total_receipts': total_count,
                    'total_amount': float(total_amount),
                    'total_tax': float(total_tax),
                    'categories': categories,
                    'period_days': days
                }
        except Exception as e:
            logger.error(f'Error getting expense summary: {e}')
            return {
                'total_receipts': 0,
                'total_amount': 0,
                'total_tax': 0,
                'categories': [],
                'period_days': days
            }
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            if not self.pool:
                await self.connect()
            
            query = """
                SELECT id, email, full_name, is_active, created_at
                FROM users
                WHERE email = $1
            """
            
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, email)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f'Error fetching user: {e}')
            return None
