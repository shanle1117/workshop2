# Bug Fix: UnboundLocalError for `answer` Variable

## Problem

The chatbot was crashing with an `UnboundLocalError` when processing staff queries:

```
UnboundLocalError: cannot access local variable 'answer' where it is not associated with a value
```

**Error Location:** Line 1408 (now 1411) in `django_app/views.py`

**Error Message:**
```python
if agent_id == 'staff' and (not answer or len(answer.strip()) < 20):
                                    ^^^^^^
UnboundLocalError: cannot access local variable 'answer' where it is not associated with a value
```

## Root Cause

The problem had **two parts**:

### 1. **Indentation Error** (Primary Issue)

The timeout handler and LLM call code was incorrectly indented **inside** the `else` block:

```python
if agent_id == 'staff':
    max_tokens = 250
elif intent in ['program_info', 'admission']:
    max_tokens = 300
else:
    max_tokens = 200
    
    # ❌ PROBLEM: This code was inside the else block!
    # TIMEOUT HANDLING: ...
    @contextmanager
    def timeout_handler(timeout_seconds):
        ...
    
    try:
        llm_response = llm_client.chat(...)
        answer = llm_response.content  # Only runs if else branch executes!
```

**Impact:**
- When `agent_id == 'staff'`: The LLM call code **never executed** because it was inside the `else` block
- When `intent in ['program_info', 'admission']`: Same issue - LLM call didn't run
- Only when `agent_id != 'staff'` AND `intent not in ['program_info', 'admission']` did the LLM call run

### 2. **Variable Not Initialized** (Secondary Issue)

Even after fixing indentation, `answer` could be `None` if:
- The LLM call failed before setting `answer`
- An exception occurred before the inner `try` block
- The code checked `answer.strip()` when `answer` was `None`

## Solution

### Fix 1: Correct Indentation

Moved timeout handler and LLM call code **outside** the `else` block:

```python
if agent_id == 'staff':
    max_tokens = 250
elif intent in ['program_info', 'admission']:
    max_tokens = 300
else:
    max_tokens = 200

# ✅ FIXED: Now at same indentation level
# TIMEOUT HANDLING: ...
@contextmanager
def timeout_handler(timeout_seconds):
    ...

try:
    llm_response = llm_client.chat(...)
    answer = llm_response.content  # Now runs for all cases!
```

### Fix 2: Initialize Variable Early

Initialize `answer = None` **before** the try block:

```python
# Initialize answer variable before LLM call (must be outside try block)
answer = None

try:
    llm_client = get_llm_client()
    ...
    answer = llm_response.content
```

### Fix 3: Safe Null Checks

Added null checks before accessing `answer`:

```python
# Before (unsafe):
if agent_id == 'staff' and (not answer or len(answer.strip()) < 20):

# After (safe):
if agent_id == 'staff' and (not answer or (answer and len(answer.strip()) < 20)):
```

### Fix 4: Safe String Concatenation

Fixed `answer +=` to handle `None`:

```python
# Before (unsafe):
answer += "\n\n📚 The Academic Handbook..."

# After (safe):
if answer:
    answer += "\n\n📚 The Academic Handbook..."
else:
    answer = "📚 The Academic Handbook..."
```

## Testing

After the fix, test these scenarios:

1. **Staff queries:** `"who is dr choo"` → Should work without error
2. **Program queries:** `"tell me about BCSAI"` → Should work without error  
3. **Admission queries:** `"what are admission requirements"` → Should work without error
4. **General queries:** `"what can you do"` → Should work without error

## Prevention

To prevent similar issues:

1. **Always initialize variables** before use, especially in try-except blocks
2. **Check indentation carefully** - Python's indentation can hide bugs
3. **Use type hints** to catch variable usage issues early
4. **Add null checks** before string operations (`strip()`, `+=`, etc.)
5. **Test all code paths** - especially exception handlers

## Related Files

- `django_app/views.py` - Main fix location (lines 1264-1411)
- All exception handlers ensure `answer` is set before use

