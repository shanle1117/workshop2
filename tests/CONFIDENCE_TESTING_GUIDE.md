# Confidence Testing Guide

This guide explains how to use the confidence testing module to validate and analyze confidence scores throughout the chatbot system.

## Overview

The confidence testing module (`test_confidence.py`) provides comprehensive testing of confidence score calculation and usage. It tests:

- Confidence calculation for different query types (short, long, edge cases)
- Confidence thresholds and their impact on routing decisions
- Confidence scores across different intents and languages
- Confidence level categorization (high, medium, low, very low)
- Integration with intent classification and query preprocessing
- Confidence-based routing and fallback mechanisms

## Quick Start

### Run All Tests

```bash
python tests/test_confidence.py
```

### Run Specific Test Category

```bash
# Test short queries (1-2 words)
python tests/test_confidence.py --category short_queries

# Test long queries (4+ words)
python tests/test_confidence.py --category long_queries

# Test priority patterns (should get high confidence)
python tests/test_confidence.py --category priority_patterns

# Test low confidence scenarios
python tests/test_confidence.py --category low_confidence

# Test multilingual confidence
python tests/test_confidence.py --category multilingual

# Test confidence thresholds
python tests/test_confidence.py --category thresholds

# Test intent confidence distribution
python tests/test_confidence.py --category intent_distribution
```

### Verbose Output

Show detailed information for each test case:

```bash
python tests/test_confidence.py --verbose
```

### Export Results

Save test results to a JSON file for further analysis:

```bash
python tests/test_confidence.py --output confidence_results.json
```

## Test Categories

### 1. Short Queries (`short_queries`)

Tests confidence calculation for queries with 1-2 words. Short queries often require different confidence calculation strategies compared to longer queries.

**Example test cases:**
- Single words: "hello", "programs", "fees"
- Two words: "BCSAI program", "tuition fees"

**What it validates:**
- Short queries should receive reasonable confidence scores (not overly penalized)
- Intent detection works correctly for minimal input
- Confidence scaling is appropriate for short queries

### 2. Long Queries (`long_queries`)

Tests confidence calculation for longer, more descriptive queries (4+ words). These typically provide more context and should achieve higher confidence scores.

**Example test cases:**
- "What programs does FAIX offer for undergraduate students?"
- "How much are the tuition fees for the BCSAI program?"

**What it validates:**
- Longer queries achieve appropriate confidence scores
- More specific queries get higher confidence
- Intent detection benefits from additional context

### 3. Priority Patterns (`priority_patterns`)

Tests queries that match priority patterns, which should receive high confidence scores (typically ≥0.8).

**Example test cases:**
- "when was faix established"
- "what programs does faix offer"
- "who can i contact"

**What it validates:**
- Priority patterns are correctly identified
- High confidence scores are assigned to priority patterns
- Intent classification works correctly for common queries

### 4. Low Confidence Scenarios (`low_confidence`)

Tests queries that should result in low confidence scores - ambiguous, unclear, or nonsensical input.

**Example test cases:**
- "random text xyz"
- "asdfghjkl"
- Empty or meaningless queries

**What it validates:**
- System correctly identifies unclear queries
- Low confidence triggers appropriate fallback mechanisms
- System gracefully handles edge cases

### 5. Multilingual Confidence (`multilingual`)

Tests confidence calculation across different languages (English, Malay, Chinese, etc.).

**Example test cases:**
- Malay: "program apa yang ditawarkan"
- Chinese: "程序" (program)

**What it validates:**
- Confidence calculation works across languages
- Language-specific patterns are handled correctly
- Minimum confidence thresholds are maintained for all languages

### 6. Confidence Thresholds (`thresholds`)

Tests that confidence thresholds work correctly and trigger appropriate behaviors:
- High (≥0.8): Direct routing
- Medium (0.5-0.8): Routing with potential clarification
- Low (0.3-0.5): May need fallback
- Very Low (<0.3): Should use fallback

**What it validates:**
- Thresholds are correctly applied
- Routing decisions align with confidence levels
- Fallback mechanisms activate appropriately

### 7. Intent Distribution (`intent_distribution`)

Tests confidence scores across different intent categories to ensure balanced performance.

**What it validates:**
- Confidence scores are consistent across different intents
- No intent category systematically receives low confidence
- Intent detection is balanced and fair

## Understanding Results

### Test Result Status

- ✓ (Green): Test passed - confidence and intent match expectations
- ✗ (Red): Test failed - either intent mismatch or confidence out of expected range

### Confidence Levels

The module categorizes confidence scores into levels:
- **High** (≥0.8): Strong match, direct routing
- **Medium** (0.5-0.8): Good match, may need clarification
- **Low** (0.3-0.5): Weak match, consider fallback
- **Very Low** (<0.3): Very weak match, use fallback

### Summary Statistics

The test output includes:
- **Total Tests**: Number of test cases executed
- **Pass/Fail Rates**: Percentage of tests that passed
- **Average Confidence**: Mean confidence across all tests
- **Min/Max Confidence**: Range of confidence scores observed
- **Confidence Distribution**: Breakdown by confidence level

## Interpreting Test Failures

Test failures can indicate:

1. **Intent Mismatch**: The detected intent doesn't match the expected intent
   - May indicate keyword pattern issues
   - Could suggest intent mapping problems

2. **Confidence Out of Range**: Confidence score is outside expected range
   - Too high: May indicate over-confidence in ambiguous cases
   - Too low: May indicate under-confidence for clear queries
   - Could suggest confidence calculation needs adjustment

3. **System Errors**: Exceptions during processing
   - Check system configuration
   - Verify dependencies are installed
   - Review error messages for clues

## Best Practices

1. **Run Tests Regularly**: Include confidence tests in your testing workflow
2. **Review Failures**: Analyze failed tests to identify patterns
3. **Adjust Expectations**: Update expected ranges based on actual system behavior
4. **Export Results**: Save results for trend analysis over time
5. **Test Edge Cases**: Pay special attention to low confidence and multilingual tests

## Example Output

```
Testing Short Queries (1-2 words)
  ✓ hello
    Intent: greeting | Confidence: 0.70 (medium)
    Expected Intent: greeting ✓
    Expected Range: (0.5, 1.0) ✓
  ✗ programs
    Intent: about_faix | Confidence: 0.40 (low)
    Expected Intent: program_info ✗
    Expected Range: (0.4, 1.0) ✓
    Error: Intent mismatch: expected 'program_info', got 'about_faix'

Overall Summary
============================================================
Total Tests: 50
Passed: 42 (84.0%)
Failed: 8 (16.0%)
Overall Average Confidence: 0.65

Confidence Distribution:
  High (≥0.8): 15 (30.0%)
  Medium (0.5-0.8): 20 (40.0%)
  Low (0.3-0.5): 12 (24.0%)
  Very Low (<0.3): 3 (6.0%)
```

## Troubleshooting

### Module Import Errors

If you see import errors, ensure you're running from the project root:

```bash
cd /path/to/workshop2
python tests/test_confidence.py
```

### Missing Dependencies

Some features require optional dependencies:
- `transformers`: For NLP-based intent classification
- `sentence-transformers`: For semantic search

The tests will run with fallback methods if these are not installed.

### Low Pass Rates

If many tests fail:
1. Review the confidence calculation logic in `query_preprocessing.py`
2. Check intent keyword patterns in `intent_config.json`
3. Verify expected ranges are realistic for your system
4. Consider updating test expectations to match actual behavior

## Integration with CI/CD

You can integrate confidence tests into your CI/CD pipeline:

```bash
# Run tests and fail on low pass rate
python tests/test_confidence.py --output results.json
# Add assertions based on pass rate or confidence metrics
```

## Extending Tests

To add custom test cases, edit `test_confidence.py` and add test cases to the appropriate method:

```python
def test_custom_scenario(self) -> ConfidenceTestSuite:
    test_cases = [
        ("your query", "en", "expected_intent", (min_conf, max_conf)),
        # Add more test cases
    ]
    # ... rest of implementation
```

## Related Documentation

- `CHATBOT_TESTING_GUIDE.md`: General chatbot testing guide
- `README_TEST_QUESTIONS.md`: Test question documentation
- `src/query_preprocessing.py`: Confidence calculation implementation
- `src/nlp_intent_classifier.py`: Intent classification with confidence
