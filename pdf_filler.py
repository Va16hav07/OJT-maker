import io
import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
import PyPDF2

A4_WIDTH, A4_HEIGHT = A4  # 595.27, 841.89 pts

FIELD_COORDS = {
    "date":                 {"x": 420, "y": 790, "max_width": 150, "font_size": 10},
    "ojt_timing":           {"x": 420, "y": 770, "max_width": 150, "font_size": 10},
    "department":           {"x": 420, "y": 750, "max_width": 150, "font_size": 10},
    "designation":          {"x": 420, "y": 730, "max_width": 150, "font_size": 10},
    "my_space":             {"x": 50,  "y": 680, "max_width": 490, "font_size": 9, "max_lines": 4},
    "tasks_carried_out":    {"x": 50,  "y": 580, "max_width": 490, "font_size": 9, "max_lines": 6},
    "key_learnings":        {"x": 50,  "y": 460, "max_width": 490, "font_size": 9, "max_lines": 5},
    "tools_used":           {"x": 50,  "y": 340, "max_width": 490, "font_size": 9, "max_lines": 4},
    "special_achievements": {"x": 50,  "y": 220, "max_width": 490, "font_size": 9, "max_lines": 3},
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
    Scan PDF text for known field labels and return their approximate bounding boxes.
    Returns {field_key: {"page": int, "x": float, "y": float}} where y is from bottom.
    """
    positions = {}
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_h = page.rect.height
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text_lower = span["text"].strip().lower()
                        bbox = span["bbox"]  # (x0, y0, x1, y1) from top-left
                        for field_key, patterns in LABEL_PATTERNS.items():
                            if field_key in positions:
                                continue
                            for pat in patterns:
                                if text_lower.startswith(pat) or text_lower == pat.rstrip(":"):
                                    # Convert y from top-left to bottom-left origin
                                    y_bottom = page_h - bbox[3]
                                    positions[field_key] = {
                                        "page": page_num,
                                        "x": bbox[2] + 4,   # just right of the label
                                        "y": y_bottom,
                                    }
                                    break
    finally:
        doc.close()
    return positions


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

    fields_to_draw = {
        "date":                 page_data.get("date", ""),
        "ojt_timing":           page_data.get("ojt_timing", ""),
        "department":           page_data.get("department", ""),
        "designation":          page_data.get("designation", ""),
        "my_space":             page_data.get("my_space", ""),
        "tasks_carried_out":    page_data.get("tasks_carried_out", ""),
        "key_learnings":        page_data.get("key_learnings", ""),
        "tools_used":           page_data.get("tools_used", ""),
        "special_achievements": page_data.get("special_achievements", ""),
    }

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


def fill_pdf_with_overlay(pdf_bytes: bytes, pages_data: list) -> bytes:
    """
    Fill the PDF template with journal data.

    Strategy:
    1. Try AcroForm field filling first.
    2. Fall back to scanning text labels for field positions.
    3. Fall back to hardcoded A4 coordinates.
    Always uses reportlab overlay merged with PyPDF2.

    Args:
        pdf_bytes: Original PDF template bytes.
        pages_data: List of dicts, one per output page, each with keys:
            date, ojt_timing, department, designation, my_space,
            tasks_carried_out, key_learnings, tools_used, special_achievements

    Returns:
        Filled PDF as bytes.
    """
    # --- Detect positions from text labels (best-effort) ---
    detected_positions = {}
    try:
        detected_positions = detect_field_positions_from_text(pdf_bytes)
    except Exception:
        pass

    # --- Open original PDF with fitz to get page sizes ---
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    num_template_pages = len(doc)
    page_sizes = []
    for i in range(num_template_pages):
        r = doc[i].rect
        page_sizes.append((r.width, r.height))
    doc.close()

    # Number of output pages = max(template pages, data pages)
    num_output_pages = max(num_template_pages, len(pages_data))

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

        # Get data for this page (repeat last entry if fewer data than pages)
        if page_idx < len(pages_data):
            page_data = pages_data[page_idx]
        elif pages_data:
            page_data = pages_data[-1]
        else:
            page_data = {}

        _build_overlay_page(c, page_data, pw, ph, detected_positions, page_idx)
        c.showPage()

    c.save()
    overlay_buffer.seek(0)

    # --- Merge overlay with original PDF using PyPDF2 ---
    original_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
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
