#!/usr/bin/env python3
"""
Test script to verify the admin normalization bug is fixed
"""

import sys
import re
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import the ShortFormProcessor
from src.query_preprocessing import ShortFormProcessor

def test_admin_bug():
    """Test that 'administration' doesn't become 'administrationstration'"""
    processor = ShortFormProcessor()
    
    test_cases = [
        "who work in administration",
        "administration staff",
        "contact admin",
        "admin office",
        "the administration department",
    ]
    
    print("=" * 70)
    print("TESTING ADMIN NORMALIZATION BUG FIX")
    print("=" * 70)
    print()
    
    for query in test_cases:
        result = processor.expand_short_forms(query, "en")
        print(f"Query: '{query}'")
        print(f"Result: '{result}'")
        
        # Check for the bug
        if "administrationstration" in result:
            print("  [BUG] Found 'administrationstration' - bug still exists!")
        elif "admin" in query.lower() and "administration" in query.lower():
            # If query already contains both, result should be unchanged
            if result == query:
                print("  [OK] Correctly left unchanged")
            else:
                print(f"  [WARNING] Changed from '{query}' to '{result}'")
        elif "admin" in query.lower() and "admin" not in result.lower():
            # If query had 'admin' standalone, it should be expanded
            print("  [OK] Correctly expanded 'admin' to 'administration'")
        else:
            print("  [OK] No changes needed")
        print()

if __name__ == "__main__":
    test_admin_bug()




