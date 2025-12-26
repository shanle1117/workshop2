# Chatbot Testing Guide

Complete guide for testing the FAIX Chatbot performance, functionality, and integration.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Running Tests](#running-tests)
3. [Manual Testing](#manual-testing)
4. [API Testing](#api-testing)
5. [Performance Testing](#performance-testing)
6. [Browser Testing](#browser-testing)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

1. **Start Django Server**:
   ```bash
   python manage.py runserver
   ```

2. **Ensure Ollama is Running** (for LLM features):
   ```bash
   # Check if Ollama is running
   curl http://localhost:11434/api/tags
   
   # If not, start Ollama
   ollama serve
   ```

3. **Ensure Database is Migrated**:
   ```bash
   python manage.py migrate
   ```

---

## Running Tests

### 1. Performance & Integration Tests

Run the comprehensive test suite:

```bash
python tests/test_chatbot_performance.py
```

**What it tests**:
- ✅ Chat API endpoint functionality
- ✅ Response caching performance
- ✅ Response times for different query types
- ✅ Multi-language support
- ✅ Agent routing (FAQ, Staff, Schedule)
- ✅ Error handling
- ✅ Query processor
- ✅ Knowledge base retrieval

**Expected Output**:
```
================================================================================
                    CHATBOT PERFORMANCE & INTEGRATION TESTS
================================================================================

→ Testing: Query Processor
  ✓ PASS Language detection: en
  ✓ PASS Intent detection: program_info

→ Testing: Performance: Caching
  ✓ PASS First request: 0.850s
  ✓ PASS Second request (cached): 0.012s
  ✓ PASS Speedup: 70.83x
  ✓ PASS Caching is working effectively!

...
```

### 2. Multi-Language Tests

Test language detection and processing:

```bash
python -X utf8 tests/test_multiple_language.py
```

**What it tests**:
- Language detection (English, Malay, Chinese, Arabic)
- Intent detection in different languages
- Query processing pipeline
- Tokenization and preprocessing

### 3. Specific Feature Tests

```bash
# Speech-to-Text tests
python tests/test_speech_to_text.py

# Dynamic features tests
python tests/test_dynamic_features.py

# Agent and prompt tests
python tests/test_agents_and_prompts.py
```

---

## Manual Testing

### 1. Test via Browser

1. **Start Django server**:
   ```bash
   python manage.py runserver
   ```

2. **Open browser**:
   Navigate to `http://localhost:8000`

3. **Test queries**:

   **English**:
   - "Hello"
   - "What programs does FAIX offer?"
   - "How do I register?"
   - "Who can I contact about AI?"

   **Malay**:
   - "Apakah program yang ditawarkan FAIX?"
   - "Bagaimana saya boleh mendaftar?"

   **Chinese**:
   - "FAIX提供什么课程？"
   - "如何注册？"

   **Arabic**:
   - "ما هي البرامج التي تقدمها FAIX؟"

### 2. Test via Python Script

Create a test script `test_manual.py`:

```python
import requests
import json

# Test the chat API
def test_chat_api():
    url = "http://localhost:8000/api/chat/"
    
    test_queries = [
        "Hello",
        "What programs does FAIX offer?",
        "Who can I contact about AI?",
        "What are the tuition fees?",
    ]
    
    session_id = None
    
    for query in test_queries:
        payload = {
            "message": query,
            "agent_id": "faq"
        }
        
        if session_id:
            payload["session_id"] = session_id
        
        response = requests.post(url, json=payload)
        data = response.json()
        
        print(f"\nQuery: {query}")
        print(f"Response: {data.get('response', 'No response')[:100]}...")
        print(f"Intent: {data.get('intent')}")
        print(f"Confidence: {data.get('confidence', 0)}")
        
        if 'session_id' in data:
            session_id = data['session_id']

if __name__ == "__main__":
    test_chat_api()
```

Run it:
```bash
python test_manual.py
```

### 3. Test via cURL

```bash
# Basic test
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What programs does FAIX offer?",
    "agent_id": "faq"
  }'

# With session
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me more",
    "session_id": "YOUR_SESSION_ID",
    "agent_id": "faq"
  }'
```

---

## API Testing

### Using Python Requests

```python
import requests
import time

BASE_URL = "http://localhost:8000/api/chat/"

def test_api_performance():
    """Test API response times"""
    
    queries = [
        "Hello",
        "What programs does FAIX offer?",
        "Who can I contact?",
    ]
    
    for query in queries:
        start = time.time()
        
        response = requests.post(
            BASE_URL,
            json={
                "message": query,
                "agent_id": "faq"
            }
        )
        
        elapsed = time.time() - start
        
        print(f"Query: {query}")
        print(f"Time: {elapsed:.3f}s")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json().get('response', '')[:50]}...")
        print()

test_api_performance()
```

### Using Postman

1. **Create a POST request**:
   - URL: `http://localhost:8000/api/chat/`
   - Method: POST
   - Headers:
     - `Content-Type: application/json`
   - Body (raw JSON):
     ```json
     {
       "message": "What programs does FAIX offer?",
       "agent_id": "faq"
     }
     ```

2. **Test different queries**:
   - Change the `message` field
   - Test different `agent_id` values: `"faq"`, `"staff"`, `"schedule"`

---

## Performance Testing

### 1. Test Response Caching

```python
import requests
import time

def test_caching():
    url = "http://localhost:8000/api/chat/"
    query = "What programs does FAIX offer?"
    
    # First request (cold cache)
    start = time.time()
    r1 = requests.post(url, json={"message": query, "agent_id": "faq"})
    time1 = time.time() - start
    
    # Second request (warm cache)
    start = time.time()
    r2 = requests.post(url, json={"message": query, "agent_id": "faq"})
    time2 = time.time() - start
    
    print(f"First request:  {time1:.3f}s")
    print(f"Second request: {time2:.3f}s")
    print(f"Speedup: {time1/time2:.2f}x")
    
    # Verify responses are identical
    assert r1.json()["response"] == r2.json()["response"]
    print("✓ Responses match")

test_caching()
```

**Expected**: Second request should be 10-100x faster if caching is working.

### 2. Test Response Times

Monitor response times for different query types:

```python
import requests
import time
from statistics import mean

def benchmark_queries():
    url = "http://localhost:8000/api/chat/"
    
    test_cases = [
        ("Greeting", "Hello"),
        ("FAQ", "What programs does FAIX offer?"),
        ("Staff", "Who can I contact about AI?"),
        ("Fee", "What are the tuition fees?"),
    ]
    
    results = {}
    
    for name, query in test_cases:
        times = []
        
        for _ in range(5):  # Run 5 times
            start = time.time()
            response = requests.post(
                url,
                json={"message": query, "agent_id": "faq"}
            )
            elapsed = time.time() - start
            times.append(elapsed)
        
        avg_time = mean(times)
        results[name] = avg_time
        print(f"{name:10} {avg_time:.3f}s (avg of 5)")
    
    print("\nPerformance Summary:")
    for name, avg_time in sorted(results.items(), key=lambda x: x[1]):
        print(f"  {name:10} {avg_time:.3f}s")

benchmark_queries()
```

**Target Performance**:
- Greeting: < 0.1s (cached)
- Fee query: < 0.5s (direct link)
- FAQ query: < 2.0s
- Staff query: < 3.0s (LLM)

---

## Browser Testing

### 1. Open Developer Tools

1. Open the chatbot in browser (`http://localhost:8000`)
2. Press `F12` to open Developer Tools
3. Go to **Network** tab

### 2. Monitor API Calls

1. Send a message in the chatbot
2. Look for the `/api/chat/` request
3. Check:
   - **Status**: Should be `200 OK`
   - **Time**: Response time
   - **Response**: JSON with `response`, `intent`, `confidence`

### 3. Check Console for Errors

- Go to **Console** tab
- Look for any JavaScript errors
- Check for API errors

### 4. Test Different Scenarios

**Test Cache Hits**:
1. Send the same query twice
2. Check Network tab - second request should be faster

**Test Multi-Language**:
1. Send queries in different languages
2. Verify responses are appropriate

**Test Agent Routing**:
1. Send staff-related queries → should route to staff agent
2. Send schedule queries → should route to schedule agent
3. Send FAQ queries → should route to FAQ agent

---

## Testing Checklist

### Functionality
- [ ] Chat API responds correctly
- [ ] Multi-language support works
- [ ] Intent detection works
- [ ] Agent routing works correctly
- [ ] Error handling works

### Performance
- [ ] Caching works (second request is faster)
- [ ] Response times are acceptable:
  - Greetings: < 0.1s
  - Simple queries: < 1.0s
  - Complex queries: < 3.0s
- [ ] Database queries are optimized
- [ ] LLM calls are optimized

### Integration
- [ ] Frontend can communicate with backend
- [ ] Session management works
- [ ] Conversation history is saved
- [ ] Error messages are user-friendly

---

## Troubleshooting

### Issue: Tests fail with "Django not available"

**Solution**:
```bash
# Make sure you're in the project root
cd /path/to/workshop2

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate
```

### Issue: API returns 500 error

**Check**:
1. Django server is running
2. Database is migrated
3. Check Django logs for errors
4. Check if Ollama is running (for LLM features)

### Issue: Slow response times

**Check**:
1. Cache is working (run caching test)
2. Database queries are optimized
3. LLM is running locally
4. Network latency

### Issue: Multi-language not working

**Check**:
1. Query preprocessing is working
2. Language detection is functioning
3. Check console for encoding errors (Windows)

---

## Advanced Testing

### Load Testing

Test the chatbot under load:

```python
import requests
from concurrent.futures import ThreadPoolExecutor
import time

def send_request(query):
    response = requests.post(
        "http://localhost:8000/api/chat/",
        json={"message": query, "agent_id": "faq"},
        timeout=10
    )
    return response.status_code

def load_test(num_requests=10):
    queries = ["Hello"] * num_requests
    
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(send_request, queries))
    
    elapsed = time.time() - start
    
    success = sum(1 for r in results if r == 200)
    
    print(f"Requests: {num_requests}")
    print(f"Success: {success}/{num_requests}")
    print(f"Time: {elapsed:.2f}s")
    print(f"RPS: {num_requests/elapsed:.2f}")

load_test(20)
```

### Integration Testing

Test the full stack:

```python
def test_full_stack():
    """Test frontend → backend → database → LLM"""
    
    # 1. Send request
    response = requests.post(
        "http://localhost:8000/api/chat/",
        json={
            "message": "What programs does FAIX offer?",
            "agent_id": "faq"
        }
    )
    
    # 2. Verify response
    assert response.status_code == 200
    data = response.json()
    
    # 3. Verify fields
    assert "response" in data
    assert "intent" in data
    assert "confidence" in data
    
    # 4. Verify response quality
    assert len(data["response"]) > 0
    assert data["confidence"] > 0
    
    print("✓ Full stack test passed")

test_full_stack()
```

---

## Next Steps

1. **Monitor Performance**: Set up logging to track response times
2. **A/B Testing**: Test different configurations
3. **User Testing**: Get real user feedback
4. **Continuous Testing**: Set up automated tests in CI/CD

For more information, see:
- `tests/test_chatbot_performance.py` - Performance tests
- `tests/test_multiple_language.py` - Language tests
- `README.md` - General documentation

