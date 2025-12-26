#!/usr/bin/env python3
"""
Script to import staff data from CSV file and update staff_contacts.json
"""

import json
import csv
import sys
from pathlib import Path

# Get project root directory
project_root = Path(__file__).parent.parent
data_dir = project_root / "data"
csv_path = Path(r"c:\Users\wongs\Downloads\satff faix.csv")
json_path = data_dir / "staff_contacts.json"


def parse_csv(csv_file_path):
    """Parse the CSV file and extract academicians and administration staff."""
    academicians = []
    administration = []
    
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    current_section = None
    header_skipped = False
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        # Detect section headers
        if line.startswith("Academician"):
            current_section = "academician"
            header_skipped = False
            continue
        elif line.startswith("Administration"):
            current_section = "administration"
            header_skipped = False
            continue
        
        # Skip header lines (Name,Position,Email)
        if line.startswith("Name,Position") or line == "Name,Position,Email":
            header_skipped = True
            continue
        
        # Parse data rows
        if current_section == "academician" and header_skipped:
            parts = line.split(',')
            if len(parts) >= 3:
                name = parts[0].strip()
                position = parts[1].strip()
                email = parts[2].strip()
                if name and position and email:
                    academicians.append({
                        "name": name,
                        "position": position,
                        "email": email
                    })
        
        elif current_section == "administration" and header_skipped:
            parts = line.split(',')
            if len(parts) >= 3:
                name = parts[0].strip()
                position = parts[1].strip()
                email = parts[2].strip()
                if name and position and email:
                    administration.append({
                        "name": name,
                        "position": position,
                        "email": email
                    })
    
    return academicians, administration


def generate_keywords(name, position):
    """Generate keywords based on name and position."""
    keywords = []
    
    # Add position-based keywords
    position_lower = position.lower()
    if "professor" in position_lower:
        keywords.append("professor")
    if "associate professor" in position_lower:
        keywords.append("associate professor")
    if "lecturer" in position_lower:
        keywords.append("lecturer")
    if "senior lecturer" in position_lower:
        keywords.append("senior lecturer")
    if "registrar" in position_lower:
        keywords.append("registrar")
    if "administrative" in position_lower or "admin" in position_lower:
        keywords.append("admin")
    if "secretary" in position_lower:
        keywords.append("secretary")
    
    # Add name parts as keywords (first name, last name)
    name_parts = name.lower().split()
    if len(name_parts) > 0:
        keywords.append(name_parts[0])  # First name
    if len(name_parts) > 1:
        keywords.append(name_parts[-1])  # Last name
    
    return list(set(keywords))  # Remove duplicates


def load_existing_json():
    """Load existing staff_contacts.json file."""
    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # Return default structure if file doesn't exist
        return {
            "faculty": "Faculty of Artificial Intelligence and Cyber Security (FAIX)",
            "university": "Universiti Teknikal Malaysia Melaka (UTeM)",
            "departments": {}
        }


def get_existing_emails(data):
    """Get set of existing email addresses to avoid duplicates."""
    emails = set()
    if "departments" in data:
        for dept_key, dept_info in data["departments"].items():
            if isinstance(dept_info, dict) and "staff" in dept_info:
                for staff in dept_info["staff"]:
                    if isinstance(staff, dict) and "email" in staff:
                        emails.add(staff["email"].lower())
    return emails


def get_max_id_across_all_departments(data):
    """Get the maximum ID across all departments to ensure unique IDs."""
    max_id = 0
    if "departments" in data:
        for dept_key, dept_info in data["departments"].items():
            if isinstance(dept_info, dict) and "staff" in dept_info:
                for staff in dept_info["staff"]:
                    if isinstance(staff, dict) and "id" in staff:
                        max_id = max(max_id, staff.get("id", 0))
    return max_id


def update_staff_data(existing_data, academicians, administration):
    """Update the staff data structure with new entries."""
    existing_emails = get_existing_emails(existing_data)
    
    # Get the maximum ID across ALL departments to ensure uniqueness
    next_id = get_max_id_across_all_departments(existing_data) + 1
    
    # Ensure departments structure exists
    if "departments" not in existing_data:
        existing_data["departments"] = {}
    
    # Update administration department
    if "administration" not in existing_data["departments"]:
        existing_data["departments"]["administration"] = {
            "name": "Faculty Administration",
            "staff": []
        }
    
    admin_staff = existing_data["departments"]["administration"]["staff"]
    
    for admin in administration:
        email_lower = admin["email"].lower()
        if email_lower not in existing_emails:
            admin_staff.append({
                "id": next_id,
                "name": admin["name"],
                "position": admin["position"],
                "email": admin["email"],
                "phone": "-",
                "office": "-",
                "keywords": generate_keywords(admin["name"], admin["position"])
            })
            next_id += 1
            existing_emails.add(email_lower)
    
    # Update academic department (create if doesn't exist)
    if "academic" not in existing_data["departments"]:
        existing_data["departments"]["academic"] = {
            "name": "Academic Staff",
            "staff": []
        }
    
    academic_staff = existing_data["departments"]["academic"]["staff"]
    
    for academic in academicians:
        email_lower = academic["email"].lower()
        if email_lower not in existing_emails:
            academic_staff.append({
                "id": next_id,
                "name": academic["name"],
                "position": academic["position"],
                "email": academic["email"],
                "phone": "-",
                "office": "-",
                "keywords": generate_keywords(academic["name"], academic["position"])
            })
            next_id += 1
            existing_emails.add(email_lower)
    
    return existing_data


def main():
    """Main function to import CSV and update JSON."""
    print(f"Reading CSV from: {csv_path}")
    
    if not csv_path.exists():
        print(f"Error: CSV file not found at {csv_path}")
        sys.exit(1)
    
    # Parse CSV
    academicians, administration = parse_csv(csv_path)
    print(f"Found {len(academicians)} academicians and {len(administration)} administration staff")
    
    # Load existing JSON
    existing_data = load_existing_json()
    print(f"Loaded existing staff data from {json_path}")
    
    # Update with new data
    updated_data = update_staff_data(existing_data, academicians, administration)
    
    # Save updated JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(updated_data, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully updated {json_path}")
    
    # Print summary
    total_staff = 0
    for dept_key, dept_info in updated_data["departments"].items():
        staff_count = len(dept_info.get("staff", []))
        total_staff += staff_count
        print(f"  {dept_info.get('name', dept_key)}: {staff_count} staff")
    
    print(f"\nTotal staff members: {total_staff}")


if __name__ == "__main__":
    main()

