# Multiple Language Testing Guide

This guide explains how to test the multiple language support in the FAIX chatbot.

## Overview

The chatbot now supports 4 languages:
- **English** (`en`)
- **Bahasa Malaysia** (`ms`)
- **Chinese** (`zh`)
- **Arabic** (`ar`)

## Running the Tests

### Basic Test Run

```bash
python -X utf8 tests/test_multiple_language.py
```

The `-X utf8` flag ensures proper Unicode handling on Windows.

### Test Coverage

The test suite includes:

1. **Language Detection Tests** - Tests automatic language detection
2. **Intent Detection Tests** - Tests intent classification in different languages
3. **Tokenization Tests** - Tests text tokenization for each language
4. **Preprocessing Tests** - Tests text cleaning and normalization
5. **End-to-End Processing Tests** - Tests complete query processing pipeline
6. **Mixed Language Tests** - Tests handling of mixed-language queries
7. **Edge Cases Tests** - Tests edge cases (empty strings, special characters, etc.)

## Test Results Interpretation

### Expected Results

- **Language Detection**: Should detect the correct language for most queries
- **Tokenization**: Should correctly tokenize text in all languages
- **Mixed Language**: Should handle mixed-language queries gracefully
- **Edge Cases**: Should not crash on edge cases

### Known Issues

Some tests may fail due to:

1. **Arabic Intent Detection**: Arabic keyword patterns may need refinement
2. **Preprocessing**: Punctuation handling may need improvement
3. **Language Detection**: Some queries with mixed content may be ambiguous

## Manual Testing

### Test Language Detection

```python
from src.query_preprocessing import QueryProcessor

processor = QueryProcessor()
result = processor.process_query("What programs does FAIX offer?")
print(result['language'])  # Should show English

result = processor.process_query("Apakah program yang ditawarkan?")
print(result['language'])  # Should show Bahasa Malaysia

result = processor.process_query("FAIX提供什么课程？")
print(result['language'])  # Should show Chinese

result = processor.process_query("ما هي البرامج المتاحة؟")
print(result['language'])  # Should show Arabic
```

### Test Intent Detection

```python
from src.query_preprocessing import QueryProcessor

processor = QueryProcessor()

# English
intent, conf = processor.detect_intent("How to register?", "en")
print(f"Intent: {intent}, Confidence: {conf}")

# Malay
intent, conf = processor.detect_intent("Bagaimana untuk mendaftar?", "ms")
print(f"Intent: {intent}, Confidence: {conf}")

# Chinese
intent, conf = processor.detect_intent("如何注册？", "zh")
print(f"Intent: {intent}, Confidence: {conf}")

# Arabic
intent, conf = processor.detect_intent("كيف أسجل؟", "ar")
print(f"Intent: {intent}, Confidence: {conf}")
```

## Test Output Format

The test suite provides color-coded output:

- ✓ Green: Test passed
- ✗ Red: Test failed
- ℹ Yellow: Information message

## Improving Test Coverage

To add more test cases:

1. Edit `tests/test_multiple_language.py`
2. Add test cases to the appropriate test function
3. Run the tests again

## Troubleshooting

### Unicode Errors on Windows

If you encounter Unicode errors, use:
```bash
python -X utf8 tests/test_multiple_language.py
```

### Import Errors

Make sure you're running from the project root:
```bash
cd C:\Users\wongs\Documents\GitHub\workshop2
python -X utf8 tests/test_multiple_language.py
```

### Language Detection Issues

If language detection fails:
1. Check if the query contains language-specific keywords
2. Verify the language patterns in `src/query_preprocessing.py`
3. Test with more explicit language indicators

## Next Steps

1. **Refine Arabic Keywords**: Add more Arabic keywords for better intent detection
2. **Improve Preprocessing**: Better handling of punctuation and special characters
3. **Add More Test Cases**: Include more edge cases and real-world queries
4. **Performance Testing**: Test with larger datasets

## Related Files

- `src/query_preprocessing.py` - Main language processing module
- `django_app/views.py` - API endpoint that uses language detection
- `src/prompt_builder.py` - Prompt builder that uses language information

