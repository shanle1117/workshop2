#!/usr/bin/env python3
"""
Script to fix duplicate IDs in staff_contacts.json
"""

import json
from pathlib import Path

project_root = Path(__file__).parent.parent
json_path = project_root / "data" / "staff_contacts.json"


def fix_duplicate_ids():
    """Fix duplicate IDs by reassigning them sequentially across all departments."""
    print("Fixing duplicate IDs in staff_contacts.json...")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    departments = data.get("departments", {})
    next_id = 1
    
    # Collect all staff from all departments
    all_staff = []
    for dept_key, dept_info in departments.items():
        if isinstance(dept_info, dict) and "staff" in dept_info:
            for staff in dept_info["staff"]:
                all_staff.append((dept_key, staff))
    
    # Clear all staff lists
    for dept_key, dept_info in departments.items():
        if isinstance(dept_info, dict) and "staff" in dept_info:
            dept_info["staff"] = []
    
    # Reassign IDs sequentially
    for dept_key, staff in all_staff:
        staff["id"] = next_id
        next_id += 1
        departments[dept_key]["staff"].append(staff)
    
    # Save the fixed data
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Fixed IDs: reassigned {len(all_staff)} staff members with IDs 1-{next_id-1}")
    print("File saved successfully!")


if __name__ == "__main__":
    fix_duplicate_ids()

