import io
import json
import re
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
import PyPDF2

A4_WIDTH, A4_HEIGHT = A4  # 595.27, 841.89 pts

FIELD_COORDS = {
    "date":                 {"x": 121, "y": 748, "max_width": 150, "font_size": 10},
    "ojt_timing_start":     {"x": 384, "y": 748, "max_width": 80, "font_size": 10},
    "ojt_timing_end":       {"x": 480, "y": 748, "max_width": 80, "font_size": 10},
    "department":           {"x": 150, "y": 718, "max_width": 150, "font_size": 10},
    "designation":          {"x": 404, "y": 718, "max_width": 150, "font_size": 10},
    "my_space":             {"x": 50,  "y": 650, "max_width": 490, "font_size": 9, "max_lines": 4},
    "tasks_carried_out":    {"x": 50,  "y": 460, "max_width": 490, "font_size": 9, "max_lines": 6},
    "key_learnings":        {"x": 50,  "y": 300, "max_width": 490, "font_size": 9, "max_lines": 5},
    "tools_used":           {"x": 53,  "y": 170, "max_width": 280, "font_size": 9, "max_lines": 4},
    "special_achievements": {"x": 320,  "y": 170, "max_width": 240, "font_size": 9, "max_lines": 3},
    "name":                 {"x": 163, "y": 285, "max_width": 300, "font_size": 11},
    "registration_number":  {"x": 163, "y": 255, "max_width": 300, "font_size": 11},
    "start_date":           {"x": 383, "y": 255, "max_width": 300, "font_size": 11},
    "program_name":         {"x": 163, "y": 225, "max_width": 300, "font_size": 11},
    "semester":             {"x": 135, "y": 193, "max_width": 300, "font_size": 11},
    "location":             {"x": 273, "y": 193, "max_width": 300, "font_size": 11},
    "industry_partner_name":{"x": 193, "y": 163.5, "max_width": 300, "font_size": 11},
    "phone_no":             {"x": 123, "y": 83, "max_width": 300, "font_size": 9},
    "email_id":             {"x": 298, "y": 83, "max_width": 300, "font_size": 9},
}

# Human-readable label patterns that map to field keys
LABEL_PATTERNS = {
    "date":                 ["date:"],
    "ojt_timing":           ["ojt timing:", "timing:", "ojt time:"],
    "department":           ["department:", "dept:"],
    "designation":          ["designation:", "position:"],
    "my_space":             ["my space:", "my space", "reflection:"],
    "tasks_carried_out":    ["tasks carried out:", "tasks:", "activities:", "work done:"],
    "key_learnings":        ["key learnings:", "learnings:", "observations:"],
    "tools_used":           ["tools used:", "tools:", "equipment used:", "technologies:"],
    "special_achievements": ["special achievements:", "achievements:", "milestones:"],
}


def clean_text_field(text: str) -> str:
    """
    Clean text field by converting JSON arrays to newline-separated text.
    Handles formats like: ['item1', 'item2', 'item3']
    """
    if not text:
        return ""
    
    text = str(text).strip()
    
    # Check if it looks like a JSON array
    if text.startswith('[') and text.endswith(']'):
        try:
            items = json.loads(text)
            if isinstance(items, list):
                # Join with newlines and clean up quotes
                return '\n'.join(str(item).strip() for item in items if item)
        except (json.JSONDecodeError, ValueError):
            pass
    
    # If it contains bullet points or dashes, clean them up
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        # Remove leading bullet characters
        line = re.sub(r'^[\-•*]\s*', '', line)
        if line:
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)


def parse_ojt_timing(timing_str: str) -> tuple:
    """
    Parse OJT timing string and return (start_time, end_time).
    Handles formats like "3:30 PM – 6:30 PM" or "3:30 PM-6:30 PM"
    
    Args:
        timing_str: Timing string like "3:30 PM – 6:30 PM"
    
    Returns:
        Tuple of (start_time, end_time) like ("3:30 PM", "6:30 PM")
    """
    if not timing_str:
        return "", ""
    
    # Split by common delimiters: –, -, or "to"
    import re
    parts = re.split(r'[–\-]|\bto\b', timing_str, flags=re.IGNORECASE)
    
    if len(parts) >= 2:
        start = parts[0].strip()
        end = parts[1].strip()
        return start, end
    
    return timing_str.strip(), ""


def detect_pdf_fields(pdf_bytes: bytes) -> dict:
    """Detect AcroForm fields in the PDF and return {field_name: page_index} mapping."""
    fields = {}
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        if reader.trailer.get("/Root") and reader.trailer["/Root"].get("/AcroForm"):
            acroform = reader.trailer["/Root"]["/AcroForm"]
            if "/Fields" in acroform:
                for field_ref in acroform["/Fields"]:
                    field = field_ref.get_object()
                    name = field.get("/T", "")
                    fields[str(name)] = field
    except Exception:
        pass
    return fields


def detect_field_positions_from_text(pdf_bytes: bytes) -> dict:
    """
    Stub function - field detection not needed on Vercel.
    Returns empty dict to use hardcoded coordinates.
    """
    return {}


def _wrap_text(text: str, font_name: str, font_size: float, max_width: float) -> list:
    """Wrap text to fit within max_width, return list of lines."""
    lines = []
    for paragraph in str(text).splitlines():
        if not paragraph.strip():
            lines.append("")
            continue
        wrapped = simpleSplit(paragraph, font_name, font_size, max_width)
        lines.extend(wrapped if wrapped else [""])
    return lines


def _build_overlay_page(c_canvas, page_data: dict, page_width: float, page_height: float,
                        detected_positions: dict, page_num: int):
    """Draw all fields onto the reportlab canvas for one page."""
    scale_x = page_width / A4_WIDTH
    scale_y = page_height / A4_HEIGHT

    font_name = "Helvetica"
    line_height_factor = 1.4

    # Parse ojt_timing if it contains a range (e.g., "3:30 PM – 6:30 PM")
    ojt_timing_str = page_data.get("ojt_timing", "")
    ojt_timing_start, ojt_timing_end = parse_ojt_timing(ojt_timing_str)

    fields_to_draw = {
        "date":                 page_data.get("date", ""),
        "ojt_timing_start":     ojt_timing_start,
        "ojt_timing_end":       ojt_timing_end,
        "department":           page_data.get("department", ""),
        "designation":          page_data.get("designation", ""),
        "my_space":             clean_text_field(page_data.get("my_space", "")),
        "tasks_carried_out":    clean_text_field(page_data.get("tasks_carried_out", "")),
        "key_learnings":        clean_text_field(page_data.get("key_learnings", "")),
        "tools_used":           clean_text_field(page_data.get("tools_used", "")),
        "special_achievements": clean_text_field(page_data.get("special_achievements", "")),
    }

    # Add the new person/program fields
    new_fields = ["name", "registration_number", "start_date", "program_name", "semester", "location", "industry_partner_name", "phone_no", "email_id"]
    for f in new_fields:
        if page_data.get(f):
            fields_to_draw[f] = page_data[f]

    for field_key, text_value in fields_to_draw.items():
        if not text_value:
            continue

        # Determine coordinates: prefer detected > hardcoded
        if field_key in detected_positions and detected_positions[field_key]["page"] == page_num:
            pos = detected_positions[field_key]
            x = pos["x"] * scale_x
            y = pos["y"] * scale_y
            max_width = FIELD_COORDS[field_key]["max_width"] * scale_x
            font_size = FIELD_COORDS[field_key]["font_size"]
            max_lines = FIELD_COORDS[field_key].get("max_lines", 1)
        else:
            coords = FIELD_COORDS[field_key]
            x = coords["x"] * scale_x
            y = coords["y"] * scale_y
            max_width = coords["max_width"] * scale_x
            font_size = coords["font_size"]
            max_lines = coords.get("max_lines", 1)

        c_canvas.setFont(font_name, font_size)
        c_canvas.setFillColorRGB(0, 0, 0)
        line_height = font_size * line_height_factor

        if max_lines == 1:
            # Single line: truncate if needed
            lines = _wrap_text(str(text_value), font_name, font_size, max_width)
            c_canvas.drawString(x, y, lines[0] if lines else str(text_value))
        else:
            lines = _wrap_text(str(text_value), font_name, font_size, max_width)
            lines = lines[:max_lines]
            for i, line in enumerate(lines):
                c_canvas.drawString(x, y - i * line_height, line)


def fill_pdf_with_overlay(pdf_bytes: bytes, pages_data: list, user_details=None, journal_start_page: int = 8, journal_end_page: int = None) -> bytes:
    """
    Fill the PDF template with journal data.

    Strategy:
    1. Fall back to scanning text labels for field positions.
    2. Fall back to hardcoded A4 coordinates.
    Always uses reportlab overlay merged with PyPDF2.

    Args:
        pdf_bytes: Original PDF template bytes.
        pages_data: List of dicts, one per output page, each with keys:
            date, ojt_timing, department, designation, my_space,
            tasks_carried_out, key_learnings, tools_used, special_achievements
        user_details: Dict of user details to place on the 3rd page.

    Returns:
        Filled PDF as bytes.
    """
    # --- Detect positions from text labels (best-effort) ---
    detected_positions = {}
    try:
        detected_positions = detect_field_positions_from_text(pdf_bytes)
    except Exception:
        pass

    # --- Get page count and sizes using PyPDF2 ---
    original_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
    num_template_pages = len(original_reader.pages)
    
    # Get page sizes - use A4 as default
    page_sizes = []
    for i in range(num_template_pages):
        try:
            page = original_reader.pages[i]
            # Get page mediabox dimensions
            mediabox = page.mediabox
            width = float(mediabox.width)
            height = float(mediabox.height)
            page_sizes.append((width, height))
        except Exception:
            page_sizes.append((A4_WIDTH, A4_HEIGHT))

    # Handle dynamic journal page offsets
    journal_start_idx = max(0, journal_start_page - 1)
    
    if journal_end_page is not None:
        max_journal_pages = max(0, journal_end_page - journal_start_page + 1)
        pages_data = pages_data[:max_journal_pages]

    # Number of output pages = max(template pages, len(pages_data) + journal_start_idx)
    num_output_pages = max(num_template_pages, len(pages_data) + journal_start_idx)

    # --- Build overlay PDF with reportlab ---
    overlay_buffer = io.BytesIO()
    c = canvas.Canvas(overlay_buffer)

    for page_idx in range(num_output_pages):
        # Determine page size (use template page size if available)
        if page_idx < len(page_sizes):
            pw, ph = page_sizes[page_idx]
        else:
            pw, ph = page_sizes[-1] if page_sizes else (A4_WIDTH, A4_HEIGHT)

        c.setPageSize((pw, ph))

        # Get data for this page
        page_data = {}
        if page_idx == 2 and user_details:
            page_data.update(user_details)
            
        if page_idx >= journal_start_idx:
            journal_idx = page_idx - journal_start_idx
            if journal_idx < len(pages_data):
                page_data.update(pages_data[journal_idx])

        _build_overlay_page(c, page_data, pw, ph, detected_positions, page_idx)
        c.showPage()

    c.save()
    overlay_buffer.seek(0)

    # --- Merge overlay with original PDF using PyPDF2 ---
    overlay_reader = PyPDF2.PdfReader(overlay_buffer)
    writer = PyPDF2.PdfWriter()

    for page_idx in range(num_output_pages):
        # Get original page (repeat last if template is shorter than data)
        if page_idx < len(original_reader.pages):
            orig_page = original_reader.pages[page_idx]
        elif original_reader.pages:
            # Clone last page
            orig_page = original_reader.pages[-1]
        else:
            orig_page = None

        overlay_page = overlay_reader.pages[page_idx]

        if orig_page is not None:
            orig_page.merge_page(overlay_page)
            writer.add_page(orig_page)
        else:
            writer.add_page(overlay_page)

    output_buffer = io.BytesIO()
    writer.write(output_buffer)
    output_buffer.seek(0)
    return output_buffer.read()
