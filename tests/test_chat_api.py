# tests/test_chat_api.py - IMPROVED

import pytest
from django.test import AsyncClient
from unittest.mock import patch, MagicMock

@pytest.mark.django_db
class TestChatAPI:
    @pytest.fixture
    def client(self):
        return AsyncClient()
    
    async def test_greeting_response(self, client):
        response = await client.post('/api/chat/', 
            data={'message': 'Hello'},
            content_type='application/json'
        )
        assert response.status_code == 200
        assert 'Hello' in response.json()['response']
    
    async def test_rate_limiting(self, client):
        # Send 31 requests (over limit)
        for _ in range(31):
            await client.post('/api/chat/', 
                data={'message': 'test'},
                content_type='application/json'
            )
        # 31st should be rate limited
        response = await client.post('/api/chat/', 
            data={'message': 'test'},
            content_type='application/json'
        )
        assert response.status_code == 429
    
    async def test_input_validation(self, client):
        # Test empty message
        response = await client.post('/api/chat/', 
            data={'message': ''},
            content_type='application/json'
        )
        assert response.status_code == 400
        
        # Test oversized message
        response = await client.post('/api/chat/', 
            data={'message': 'x' * 10001},  # Over 10k chars
            content_type='application/json'
        )
        assert response.status_code == 400