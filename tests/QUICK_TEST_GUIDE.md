# Quick Testing Guide

## 🚀 Quick Start Testing

### 1. Standalone Tests (No Django Required)

Test components directly:

```bash
python tests/test_chatbot_standalone.py
```

**What it tests**:
- ✅ Language detection
- ✅ Intent detection  
- ✅ Query processing
- ✅ Performance (caching)
- ✅ Response times

### 2. Full Integration Tests (Django Required)

First, start Django server:
```bash
python manage.py runserver
```

Then in another terminal:
```bash
python tests/test_chatbot_performance.py
```

**What it tests**:
- ✅ API endpoints
- ✅ Response caching
- ✅ Multi-language support
- ✅ Agent routing
- ✅ Error handling

---

## 🧪 Manual Testing

### Option 1: Browser Testing

1. Start server:
   ```bash
   python manage.py runserver
   ```

2. Open browser:
   ```
   http://localhost:8000
   ```

3. Test queries:
   - "Hello"
   - "What programs does FAIX offer?"
   - "Who can I contact about AI?"
   - "Apakah program yang ditawarkan?" (Malay)
   - "FAIX提供什么课程？" (Chinese)

### Option 2: Python Script

Create `test_quick.py`:

```python
import requests

url = "http://localhost:8000/api/chat/"

queries = [
    "Hello",
    "What programs does FAIX offer?",
    "Who can I contact?",
]

for query in queries:
    response = requests.post(url, json={
        "message": query,
        "agent_id": "faq"
    })
    data = response.json()
    print(f"\nQ: {query}")
    print(f"A: {data['response'][:100]}...")
```

Run:
```bash
python test_quick.py
```

### Option 3: cURL

```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "What programs does FAIX offer?", "agent_id": "faq"}'
```

---

## 📊 Performance Testing

### Test Caching

```python
import requests
import time

url = "http://localhost:8000/api/chat/"

# First request
start = time.time()
r1 = requests.post(url, json={"message": "Hello", "agent_id": "faq"})
time1 = time.time() - start

# Second request (should be cached)
start = time.time()
r2 = requests.post(url, json={"message": "Hello", "agent_id": "faq"})
time2 = time.time() - start

print(f"First: {time1:.3f}s")
print(f"Second: {time2:.3f}s")
print(f"Speedup: {time1/time2:.2f}x")
```

**Expected**: Second request should be 10-100x faster.

---

## ✅ Testing Checklist

### Basic Functionality
- [ ] Chat API responds
- [ ] Multi-language works
- [ ] Intent detection works
- [ ] Agent routing works

### Performance
- [ ] Caching works (second request faster)
- [ ] Response times acceptable:
  - Greetings: < 0.1s
  - FAQ: < 2.0s
  - Staff queries: < 3.0s

### Integration
- [ ] Frontend connects to backend
- [ ] Session management works
- [ ] Error handling works

---

## 🔍 Debugging

### Check Django Server
```bash
# Start server with verbose logging
python manage.py runserver --verbosity 2
```

### Check Cache
```python
from django.core.cache import cache
cache.clear()  # Clear cache
```

### Check Logs
Look for debug prints in terminal running Django server.

---

## 📚 More Information

- Full guide: `tests/CHATBOT_TESTING_GUIDE.md`
- Performance tests: `tests/test_chatbot_performance.py`
- Standalone tests: `tests/test_chatbot_standalone.py`

