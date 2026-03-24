#!/usr/bin/env python3
"""
Test script to verify PDF filler functionality.
Fills ojt_template.pdf with test data for all fields and saves output as abc_filled.pdf
"""

import os
from pdf_filler import fill_pdf_with_overlay

def test_pdf_filler():
    """Test filling PDF with sample data for all fields."""
    
    # Check if ojt_template.pdf exists
    pdf_path = "ojt_template.pdf"
    if not os.path.exists(pdf_path):
        print(f"❌ Error: {pdf_path} not found in current directory")
        return False
    
    print(f"✓ Found {pdf_path}")
    
    # Read the PDF template
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    print(f"✓ Loaded PDF ({len(pdf_bytes)} bytes)")
    
    # Create test data for all fields
    test_data = [
        {
            "date": "23-3-2026",
            "ojt_timing": "3:30 PM – 6:30 PM",
            "department": "IT Department",
            "designation": "Junior Developer",
            "my_space": "This is my reflection on the OJT experience. I learned valuable skills and gained practical knowledge in real-world scenarios.",
            "tasks_carried_out": "Developed web applications, debugged code, participated in team meetings, wrote unit tests, reviewed code from peers, and assisted in deployment processes.",
            "key_learnings": "Learned modern web development practices, improved problem-solving skills, understood agile methodology, enhanced collaboration abilities, and gained insights into software architecture.",
            "tools_used": "VS Code, Git, Python, JavaScript, React, PostgreSQL, Docker",
            "special_achievements": "Successfully completed 2 projects ahead of schedule and received positive feedback from mentors.",
        }
    ]
    
    print("\n📝 Test data fields:")
    for key, value in test_data[0].items():
        preview = value[:50] + "..." if len(value) > 50 else value
        print(f"  • {key}: {preview}")
    
    # Fill the PDF
    try:
        filled_pdf = fill_pdf_with_overlay(pdf_bytes, test_data)
        print(f"\n✓ PDF filled successfully ({len(filled_pdf)} bytes)")
    except Exception as e:
        print(f"\n❌ Error filling PDF: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Save the filled PDF
    output_path = "abc_filled.pdf"
    with open(output_path, "wb") as f:
        f.write(filled_pdf)
    print(f"✓ Saved filled PDF to {output_path}")
    
    print("\n✅ Test completed successfully!")
    print(f"\nNext steps:")
    print(f"1. Open {output_path} to verify fields are filled correctly")
    print(f"2. Check that all text is visible and properly positioned")
    print(f"3. Verify text wrapping for multi-line fields (my_space, tasks_carried_out, etc.)")
    
    return True

if __name__ == "__main__":
    test_pdf_filler()
