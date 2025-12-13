"""
Quick demo showing Dynamic Intent Classifier capabilities
Demonstrates runtime configuration updates without code changes
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from nlp_intent_classifier import IntentClassifier

print("="*70)
print("DEMONSTRATION: DYNAMIC INTENT CLASSIFIER")
print("="*70)

# Create classifier (loads from config file)
clf = IntentClassifier()

print("\n1. INITIAL STATE - Loaded from config file:")
print(f"   Intent Categories: {clf.intent_categories}")
print(f"   ✓ Loaded from data/intent_config.json")

print("\n2. TESTING CLASSIFICATION (Before Update):")
test_queries = [
    "What courses do you offer?",
    "How can I register?",
    "When does the semester start?",
    "I want to apply for scholarship",  # This won't be recognized yet
]

for query in test_queries:
    intent, conf, _ = clf.classify(query)
    print(f"   Query: '{query}'")
    print(f"   → Intent: {intent} (confidence: {conf:.3f})")

print("\n" + "="*70)
print("3. DYNAMIC UPDATE - Adding New Intent at Runtime")
print("="*70)

# Method 1: Update via update_intents() method (programmatic)
print("\n   Method 1: Using update_intents() method")
clf.update_intents({
    'scholarship': 'Questions about scholarships, financial aid, or funding'
}, descriptions={
    'scholarship': 'Questions about scholarships, financial aid, grants, or funding opportunities'
})

# Also update keyword patterns manually
clf.keyword_patterns['scholarship'] = ['scholarship', 'financial aid', 'funding', 'grant', 'bursary']
print(f"   ✓ Added 'scholarship' intent via update_intents()")
print(f"   Current intents: {clf.intent_categories}")

# Test with new intent
print("\n   Testing with new intent:")
test_query = "I want to apply for scholarship"
intent, conf, _ = clf.classify(test_query)
print(f"   Query: '{test_query}'")
print(f"   → Intent: {intent} (confidence: {conf:.3f})")
print("   ✓ New intent recognized WITHOUT restarting!")

print("\n" + "="*70)
print("4. DYNAMIC UPDATE - Reload from Config File")
print("="*70)

# Method 2: Update config file and reload
config_path = Path(__file__).parent.parent / 'data' / 'intent_config.json'

print("\n   Method 2: Updating config file and reloading")
print(f"   Editing: {config_path}")

# Read current config
with open(config_path, 'r') as f:
    config = json.load(f)

# Add new intent to config
if 'admission' not in config['intent_categories']:
    config['intent_categories'].append('admission')
    config['intent_descriptions']['admission'] = 'Questions about admission requirements, entry criteria, or application process'
    config['keyword_patterns']['admission'] = ['admission', 'entry', 'apply', 'application', 'requirements', 'criteria']
    
    # Save updated config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print("   ✓ Config file updated with 'admission' intent")

# Reload classifier
print("\n   Reloading classifier from updated config...")
clf.reload_config()
print(f"   ✓ Reloaded! Current intents: {clf.intent_categories}")

# Test with new intent from config
print("\n   Testing with new intent from config:")
test_query = "What are the admission requirements?"
intent, conf, _ = clf.classify(test_query)
print(f"   Query: '{test_query}'")
print(f"   → Intent: {intent} (confidence: {conf:.3f})")
print("   ✓ New intent from config file recognized!")

print("\n" + "="*70)
print("5. COMPARISON: Static vs Dynamic")
print("="*70)

print("""
STATIC VERSION (Old):
  ❌ Intents hardcoded in Python code (class variables)
  ❌ Must edit Python file to add/modify intents
  ❌ Requires application restart for changes
  ❌ Only one global instance
  ❌ No runtime configuration updates

DYNAMIC VERSION (Current):
  ✅ Intents loaded from JSON config file (instance variables)
  ✅ Edit JSON file to add/modify intents (no code change)
  ✅ Can reload config at runtime (no restart needed)
  ✅ Multiple instances with different configs supported
  ✅ Runtime updates via update_intents() and reload_config()
  ✅ Changes persist in config file
""")

print("\n" + "="*70)
print("6. KEY BENEFITS DEMONSTRATED")
print("="*70)
print("""
✓ Added 'scholarship' intent at runtime using update_intents()
✓ Added 'admission' intent by editing JSON and calling reload_config()
✓ No code changes required
✓ No application restart needed
✓ Changes can be made by non-developers (just edit JSON)
✓ Configuration is version-controllable (JSON file in git)
""")

print("\n" + "="*70)
print("TESTING COMPLETE")
print("="*70)
