"""
Test script to compare Static vs Dynamic Intent Classifier
Run this to see the differences in action.
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Import both versions
from src.nlp_intent_classifier import IntentClassifier as StaticClassifier, get_intent_classifier as get_static_classifier

# For dynamic version, you'll need to implement it first
# from nlp_intent_classifier_dynamic import IntentClassifier as DynamicClassifier, get_intent_classifier as get_dynamic_classifier


def test_static_classifier():
    """Test the STATIC version (current implementation)"""
    print("\n" + "="*70)
    print("TESTING STATIC CLASSIFIER (Current Implementation)")
    print("="*70)
    
    # Initialize static classifier
    print("\n1. Initializing Static Classifier...")
    static_clf = get_static_classifier()
    
    # Show hardcoded intents
    print("\n2. Hardcoded Intent Categories (from code):")
    print(f"   {static_clf.INTENT_CATEGORIES}")
    
    print("\n3. Hardcoded Intent Descriptions (from code):")
    for intent, desc in list(static_clf.INTENT_DESCRIPTIONS.items())[:3]:
        print(f"   - {intent}: {desc[:50]}...")
    print("   ...")
    
    # Test classification
    test_queries = [
        "What courses are available?",
        "How do I register for classes?",
        "When is the semester starting?",
        "Can I contact a professor?",
    ]
    
    print("\n4. Testing Classification:")
    results_static = {}
    for query in test_queries:
        intent, confidence, scores = static_clf.classify(query)
        results_static[query] = (intent, confidence)
        print(f"   Query: '{query}'")
        print(f"   → Intent: {intent} (confidence: {confidence:.3f})")
    
    # Try to add new intent (THIS WILL FAIL - it's static!)
    print("\n5. Attempting to add new intent at runtime...")
    try:
        # This won't work because intents are hardcoded
        static_clf.INTENT_CATEGORIES.append('new_intent')
        static_clf.INTENT_DESCRIPTIONS['new_intent'] = 'New intent description'
        print("   ⚠️  Modified class variables, but changes are temporary")
        print("   ⚠️  New instance will reset to original values")
        
        # Test with new intent
        test_query = "I want to apply for scholarship"
        intent, confidence, _ = static_clf.classify(test_query)
        print(f"   Query: '{test_query}'")
        print(f"   → Intent: {intent} (may not recognize new intent)")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return results_static


def test_dynamic_classifier():
    """Test the DYNAMIC version (proposed implementation)"""
    print("\n" + "="*70)
    print("TESTING DYNAMIC CLASSIFIER (Proposed Implementation)")
    print("="*70)
    
    # Create config file first
    config_path = Path(__file__).parent.parent / 'data' / 'intent_config.json'
    config_path.parent.mkdir(exist_ok=True)
    
    # Create initial config
    import json
    initial_config = {
        "intent_categories": [
            "course_info",
            "registration",
            "academic_schedule",
            "staff_contact",
            "facility_info",
            "program_info",
            "general_query"
        ],
        "intent_descriptions": {
            "course_info": "Questions about specific courses, course content, course requirements, or course details",
            "registration": "Questions about course registration, enrollment, application process, or registration deadlines",
            "academic_schedule": "Questions about academic calendar, semester dates, class schedules, or timetable",
            "staff_contact": "Questions about contacting staff members, faculty, professors, or getting contact information",
            "facility_info": "Questions about campus facilities, laboratories, buildings, or equipment",
            "program_info": "Questions about academic programs, degrees, requirements, program details, academic handbook, or student handbook",
            "general_query": "General questions, greetings, or unclear queries that don't fit other categories"
        },
        "keyword_patterns": {
            "course_info": ["course", "subject", "module", "curriculum", "class", "lecture"],
            "registration": ["register", "enroll", "enrollment", "admission", "apply", "sign up", "deadline"],
            "academic_schedule": ["schedule", "timetable", "calendar", "when", "time", "date", "semester"],
            "staff_contact": ["contact", "email", "phone", "number", "professor", "lecturer", "staff", "faculty"],
            "facility_info": ["lab", "laboratory", "facility", "equipment", "room", "building", "campus"],
            "program_info": ["program", "degree", "bachelor", "master", "requirement", "eligibility", "duration"]
        },
        "model_config": {
            "default_model": "facebook/bart-large-mnli",
            "use_zero_shot": True,
            "confidence_threshold": 0.3
        }
    }
    
    with open(config_path, 'w') as f:
        json.dump(initial_config, f, indent=2)
    print(f"\n1. Created config file at: {config_path}")
    
    # NOTE: Uncomment when dynamic version is implemented
    # print("\n2. Initializing Dynamic Classifier from config...")
    # dynamic_clf = get_dynamic_classifier(config_path=str(config_path))
    
    # print("\n3. Loaded Intent Categories (from JSON):")
    # print(f"   {dynamic_clf.intent_categories}")
    
    # Test classification
    test_queries = [
        "What courses are available?",
        "How do I register for classes?",
        "When is the semester starting?",
        "Can I contact a professor?",
    ]
    
    # print("\n4. Testing Classification:")
    # results_dynamic = {}
    # for query in test_queries:
    #     intent, confidence, scores = dynamic_clf.classify(query)
    #     results_dynamic[query] = (intent, confidence)
    #     print(f"   Query: '{query}'")
    #     print(f"   → Intent: {intent} (confidence: {confidence:.3f})")
    
    # Demonstrate dynamic update
    print("\n5. Adding new intent dynamically (NO CODE CHANGE NEEDED!)...")
    print("   Updating config file...")
    
    # Add new intent to config
    initial_config['intent_categories'].append('scholarship')
    initial_config['intent_descriptions']['scholarship'] = 'Questions about scholarships, financial aid, or funding'
    initial_config['keyword_patterns']['scholarship'] = ['scholarship', 'financial aid', 'funding', 'grant', 'bursary']
    
    with open(config_path, 'w') as f:
        json.dump(initial_config, f, indent=2)
    print("   ✓ Config file updated")
    
    # Reload classifier
    # dynamic_clf.reload_config(config_path=str(config_path))
    # print("   ✓ Classifier reloaded with new intent")
    
    # Test with new intent
    # test_query = "I want to apply for scholarship"
    # intent, confidence, _ = dynamic_clf.classify(test_query)
    # print(f"\n   Query: '{test_query}'")
    # print(f"   → Intent: {intent} (confidence: {confidence:.3f})")
    # print("   ✓ New intent recognized WITHOUT restarting application!")
    
    print("\n   [Dynamic version not yet implemented - see proposed code above]")
    
    return {}


def compare_results(static_results, dynamic_results):
    """Compare results from both classifiers"""
    print("\n" + "="*70)
    print("COMPARISON SUMMARY")
    print("="*70)
    
    print("\n📊 Classification Results Comparison:")
    print(f"{'Query':<40} {'Static Intent':<20} {'Dynamic Intent':<20}")
    print("-" * 80)
    
    for query in static_results.keys():
        static_intent, static_conf = static_results[query]
        dynamic_intent, dynamic_conf = dynamic_results.get(query, ('N/A', 0.0))
        match = "✓" if static_intent == dynamic_intent else "✗"
        print(f"{query[:38]:<40} {static_intent:<20} {dynamic_intent:<20} {match}")
    
    print("\n" + "="*70)
    print("KEY DIFFERENCES")
    print("="*70)
    print("""
STATIC VERSION:
  ❌ Intents hardcoded in Python code
  ❌ Must edit code to add/modify intents
  ❌ Requires application restart for changes
  ❌ Only one global instance
  ❌ No runtime configuration updates

DYNAMIC VERSION:
  ✅ Intents loaded from JSON config file
  ✅ Edit JSON file to add/modify intents (no code change)
  ✅ Can reload config at runtime (no restart needed)
  ✅ Multiple instances with different configs
  ✅ Runtime updates via update_intents() method
    """)


def main():
    """Run comparison tests"""
    print("\n" + "="*70)
    print("STATIC vs DYNAMIC INTENT CLASSIFIER COMPARISON")
    print("="*70)
    
    # Test static version
    static_results = test_static_classifier()
    
    # Test dynamic version
    dynamic_results = test_dynamic_classifier()
    
    # Compare (when both are available)
    if dynamic_results:
        compare_results(static_results, dynamic_results)
    else:
        print("\n" + "="*70)
        print("NOTE: Dynamic version needs to be implemented first")
        print("="*70)
        print("\nTo implement dynamic version:")
        print("1. Create data/intent_config.json (see example above)")
        print("2. Update nlp_intent_classifier.py with dynamic code")
        print("3. Run this test again to see full comparison")


if __name__ == "__main__":
    main()
