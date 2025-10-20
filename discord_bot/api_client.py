"""
API Client for Discord Bot
Handles communication with FastAPI backend
"""
import aiohttp
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger('api_client')


class APIClient:
    """API Client for backend communication"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Login to the API
        
        Returns:
            {
                'success': bool,
                'token': str (if success),
                'error': str (if failure)
            }
        """
        try:
            session = await self._get_session()
            
            # Prepare form data
            data = aiohttp.FormData()
            data.add_field('username', email)  # FastAPI OAuth2 uses 'username' field
            data.add_field('password', password)
            
            async with session.post(
                f'{self.base_url}/api/v1/auth/login',
                data=data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        'success': True,
                        'token': result['access_token']
                    }
                else:
                    error_data = await response.json()
                    return {
                        'success': False,
                        'error': error_data.get('detail', 'Login failed')
                    }
        except Exception as e:
            logger.error(f'Login error: {e}')
            return {
                'success': False,
                'error': str(e)
            }
    
    async def upload_receipt(
        self,
        image_data: bytes,
        filename: str,
        token: str
    ) -> Dict[str, Any]:
        """
        Upload receipt image
        
        Returns:
            {
                'success': bool,
                'data': dict (if success),
                'error': str (if failure)
            }
        """
        try:
            session = await self._get_session()
            
            # Prepare multipart form data
            data = aiohttp.FormData()
            data.add_field(
                'file',
                image_data,
                filename=filename,
                content_type='image/jpeg'
            )
            
            headers = {
                'Authorization': f'Bearer {token}'
            }
            
            async with session.post(
                f'{self.base_url}/api/v1/receipts/upload',
                data=data,
                headers=headers
            ) as response:
                result = await response.json()
                
                if response.status in [200, 201, 202]:  # Added 202 Accepted for async processing
                    # Wait a bit for processing (longer for async)
                    import asyncio
                    await asyncio.sleep(5)  # Increased wait time for background processing
                    
                    # Get the receipt details
                    receipt_id = result.get('id')
                    if receipt_id:
                        receipt_data = await self.get_receipt(receipt_id, token)
                        if receipt_data['success']:
                            return {
                                'success': True,
                                'data': receipt_data['data']
                            }
                    
                    return {
                        'success': True,
                        'data': result
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('detail', 'Upload failed')
                    }
        except Exception as e:
            logger.error(f'Upload error: {e}')
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_receipts(
        self,
        token: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        vendor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get list of receipts
        
        Returns:
            {
                'success': bool,
                'data': dict (if success),
                'error': str (if failure)
            }
        """
        try:
            session = await self._get_session()
            
            params = {
                'page': page,
                'page_size': page_size
            }
            if status:
                params['status'] = status
            if vendor:
                params['vendor'] = vendor
            
            headers = {
                'Authorization': f'Bearer {token}'
            }
            
            async with session.get(
                f'{self.base_url}/api/v1/receipts',
                params=params,
                headers=headers
            ) as response:
                result = await response.json()
                
                if response.status == 200:
                    return {
                        'success': True,
                        'data': result
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('detail', 'Failed to fetch receipts')
                    }
        except Exception as e:
            logger.error(f'Get receipts error: {e}')
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_receipt(self, receipt_id: str, token: str) -> Dict[str, Any]:
        """
        Get specific receipt details
        
        Returns:
            {
                'success': bool,
                'data': dict (if success),
                'error': str (if failure)
            }
        """
        try:
            session = await self._get_session()
            
            headers = {
                'Authorization': f'Bearer {token}'
            }
            
            async with session.get(
                f'{self.base_url}/api/v1/receipts/{receipt_id}',
                headers=headers
            ) as response:
                result = await response.json()
                
                if response.status == 200:
                    return {
                        'success': True,
                        'data': result
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('detail', 'Receipt not found')
                    }
        except Exception as e:
            logger.error(f'Get receipt error: {e}')
            return {
                'success': False,
                'error': str(e)
            }
    
    async def search_receipts(
        self,
        token: str,
        vendor: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search receipts
        
        Returns:
            {
                'success': bool,
                'data': dict (if success),
                'error': str (if failure)
            }
        """
        params = {}
        if vendor:
            params['vendor'] = vendor
        if category:
            params['category'] = category
        
        return await self.get_receipts(token, page=1, page_size=50, **params)
    
    async def delete_receipt(
        self,
        receipt_id: str,
        token: str
    ) -> Dict[str, Any]:
        """
        Delete a receipt
        
        Returns:
            {
                'success': bool,
                'error': str (if failure)
            }
        """
        try:
            session = await self._get_session()
            
            headers = {
                'Authorization': f'Bearer {token}'
            }
            
            async with session.delete(
                f'{self.base_url}/api/v1/receipts/{receipt_id}',
                headers=headers
            ) as response:
                if response.status == 204:  # No Content - successful deletion
                    return {'success': True}
                elif response.status == 200:
                    result = await response.json()
                    return {'success': True, 'data': result}
                else:
                    result = await response.json()
                    return {
                        'success': False,
                        'error': result.get('detail', 'Failed to delete receipt')
                    }
        except Exception as e:
            logger.error(f'Delete receipt error: {e}')
            return {
                'success': False,
                'error': str(e)
            }
