#!/usr/bin/env python3
"""
Show the actual administration staff from staff_contacts.json
"""

import json
from pathlib import Path

project_root = Path(__file__).parent.parent
json_path = project_root / "data" / "staff_contacts.json"

with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=" * 70)
print("ACTUAL ADMINISTRATION STAFF IN staff_contacts.json")
print("=" * 70)
print()

admin_staff = []
for dept_key, dept_info in data.get("departments", {}).items():
    if "administration" in dept_key.lower() or "administration" in dept_info.get("name", "").lower():
        admin_staff = dept_info.get("staff", [])
        break

if admin_staff:
    print(f"Found {len(admin_staff)} administration staff members:\n")
    for i, staff in enumerate(admin_staff, 1):
        print(f"{i}. {staff.get('name', 'N/A')}")
        print(f"   Position: {staff.get('position', 'N/A')}")
        print(f"   Email: {staff.get('email', 'N/A')}")
        print()
else:
    print("No administration staff found in staff_contacts.json")

print("=" * 70)
print("EXPECTED CHATBOT RESPONSE")
print("=" * 70)
print()
print("When asked about administration staff, the chatbot should ONLY list:")
print()
for staff in admin_staff:
    print(f"• {staff.get('name', 'N/A')} - {staff.get('position', 'N/A')}")
print()
print("The chatbot should NOT list:")
print("  - Generic roles without names (Office Manager, HR Officer, etc.)")
print("  - Department names as if they were people")
print("  - Positions that don't exist in the JSON file")
print("=" * 70)






