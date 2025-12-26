#!/usr/bin/env python3
"""
Script to validate staff_contacts.json file structure and data integrity
"""

import json
from pathlib import Path

project_root = Path(__file__).parent.parent
json_path = project_root / "data" / "staff_contacts.json"


def validate_staff_json():
    """Validate the staff_contacts.json file."""
    print("=" * 70)
    print("STAFF CONTACTS JSON VALIDATION")
    print("=" * 70)
    print()
    
    if not json_path.exists():
        print(f"[ERROR] File not found at {json_path}")
        return False
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON format - {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to read file - {e}")
        return False
    
    # Check top-level structure
    print("Structure Check:")
    required_fields = ["faculty", "university", "departments"]
    for field in required_fields:
        if field in data:
            print(f"  [OK] {field}: {data[field] if field != 'departments' else 'present'}")
        else:
            print(f"  [ERROR] Missing required field: {field}")
            return False
    
    print()
    
    # Check departments
    departments = data.get("departments", {})
    if not isinstance(departments, dict):
        print("[ERROR] 'departments' must be a dictionary")
        return False
    
    print(f"Departments: {len(departments)}")
    total_staff = 0
    all_emails = []
    all_ids = []
    issues = []
    
    for dept_key, dept_info in departments.items():
        if not isinstance(dept_info, dict):
            issues.append(f"Department '{dept_key}' is not a dictionary")
            continue
        
        dept_name = dept_info.get("name", dept_key)
        staff_list = dept_info.get("staff", [])
        
        if not isinstance(staff_list, list):
            issues.append(f"Department '{dept_key}' staff is not a list")
            continue
        
        print(f"  • {dept_name}: {len(staff_list)} staff")
        total_staff += len(staff_list)
        
        # Validate each staff member
        for idx, staff in enumerate(staff_list):
            if not isinstance(staff, dict):
                issues.append(f"Department '{dept_key}', staff #{idx+1} is not a dictionary")
                continue
            
            # Check required fields
            name = staff.get("name", "").strip()
            email = staff.get("email", "").strip()
            position = staff.get("position", "").strip()
            staff_id = staff.get("id")
            
            if not name:
                issues.append(f"Department '{dept_key}', staff #{idx+1} has no name")
            
            if not email or email == "-":
                issues.append(f"Department '{dept_key}', '{name}' has no email")
            else:
                email_lower = email.lower()
                if email_lower in all_emails:
                    issues.append(f"Duplicate email: {email} (found in '{name}')")
                all_emails.append(email_lower)
            
            if not position:
                issues.append(f"Department '{dept_key}', '{name}' has no position")
            
            if staff_id is None:
                issues.append(f"Department '{dept_key}', '{name}' has no ID")
            else:
                if staff_id in all_ids:
                    issues.append(f"Duplicate ID: {staff_id} (found in '{name}')")
                all_ids.append(staff_id)
            
            # Check optional fields
            phone = staff.get("phone", "-")
            office = staff.get("office", "-")
            keywords = staff.get("keywords", [])
            
            if not isinstance(keywords, list):
                issues.append(f"Department '{dept_key}', '{name}' keywords is not a list")
    
    print()
    print(f"Summary:")
    print(f"  Total departments: {len(departments)}")
    print(f"  Total staff members: {total_staff}")
    print(f"  Unique emails: {len(set(all_emails))}")
    print(f"  Unique IDs: {len(set(all_ids))}")
    print()
    
    if issues:
        print(f"[WARNING] Issues Found ({len(issues)}):")
        for issue in issues[:20]:  # Show first 20 issues
            print(f"  - {issue}")
        if len(issues) > 20:
            print(f"  ... and {len(issues) - 20} more issues")
        print()
        return False
    else:
        print("[SUCCESS] No issues found! File structure is valid.")
        print()
        return True


if __name__ == "__main__":
    success = validate_staff_json()
    exit(0 if success else 1)

