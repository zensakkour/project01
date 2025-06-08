import os
import re

# Helper function to identify math blocks
def is_math_block(text_block: str) -> bool:
    """
    Checks if a text block is likely a mathematical formula.
    """
    # Remove leading/trailing whitespace
    text_block = text_block.strip()
    if not text_block:
        return False

    # Check for common LaTeX math keywords
    math_keywords = [
        r'\\sum', r'\\int', r'\\frac', r'\\sqrt', r'\\lim', r'\\sin', r'\\cos', r'\\log',
        r'\\alpha', r'\\beta', r'\\gamma', r'\\delta', r'\\epsilon', r'\\omega', r'\\phi', r'\\pi', r'\\theta',
        # Add more as needed, e.g., matrix environments
        r'\\begin\{array\}', r'\\begin\{matrix\}', r'\\begin\{pmatrix\}', r'\\begin\{bmatrix\}',
        r'\\begin\{vmatrix\}', r'\\begin\{Vmatrix\}'
    ]
    # Ensure keywords are treated as raw strings for regex
    if any(re.search(keyword, text_block) for keyword in math_keywords):
        return True

    # Check for patterns like lines dominated by alphanumeric characters mixed with math symbols
    # This regex looks for lines that have a high proportion of math-related characters.
    # It's a heuristic and might need refinement.
    # Count lines
    lines = text_block.split('\n')
    if not lines:
        return False

    math_char_ratio_threshold = 0.5  # More than 50% of non-whitespace chars are math-like
    min_math_chars_on_line = 3 # At least 3 math-like characters on a line to be considered

    math_lines_count = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue

        non_whitespace_chars = ''.join(line.split())
        if not non_whitespace_chars:
            continue

        # More comprehensive set of typical math characters
        math_like_chars = re.findall(r'[a-zA-Z0-9\+\-\*/=<>^_\(\)\[\]\{\}\\\.,;:!\?]', non_whitespace_chars)

        # Additional check for operators or structures that are highly indicative of math
        # e.g., `... = ...`, `... + ...`, `.../...` (more than one letter), `X^{...}`
        operator_pattern = r'([a-zA-Z0-9]\s*[\+\-\*/=<>]+\s*[a-zA-Z0-9])|(\w\^\{.*\})|(\\[a-zA-Z]+)'
        if re.search(operator_pattern, line) and len(math_like_chars) >= min_math_chars_on_line :
             math_lines_count +=1
             continue


        if len(math_like_chars) >= min_math_chars_on_line and \
           (len(math_like_chars) / len(non_whitespace_chars)) >= math_char_ratio_threshold:
            math_lines_count += 1

    # If a significant portion of lines look like math, consider the block as math
    # This threshold can be adjusted. E.g. if more than half the lines are mathy.
    if len(lines) > 0 and (math_lines_count / len(lines)) >= 0.4: # Adjusted threshold
        return True

    # Heuristic: if a block has $$...$$ or \[...\] it's definitely math
    if (text_block.startswith("$$") and text_block.endswith("$$")) or \
       (text_block.startswith("\\[") and text_block.endswith("\\]")):
        return True

    return False

def generate_latex_document(content: dict, pdf_filename_no_ext: str) -> str:
    """
    Generates a LaTeX document string from extracted text, image paths, and margins.

    Args:
        content: A dictionary with 'text' (str), 'image_paths' (list of str),
                 and 'margins' (dict with cm values for left, right, top, bottom, width, height).
        pdf_filename_no_ext: The original PDF filename without the extension.

    Returns:
        A string containing the full LaTeX document.
    """

    # Handle margins first to build the geometry package string
    margins = content.get('margins')
    geometry_package_str = "\\usepackage[a4paper, margin=2cm]{geometry}" # Default
    if margins and all(k in margins for k in ['left', 'right', 'top', 'bottom']):
        try:
            # Ensure margin values are positive or zero
            m_left = max(0, float(margins['left']))
            m_right = max(0, float(margins['right']))
            m_top = max(0, float(margins['top']))
            m_bottom = max(0, float(margins['bottom']))

            geometry_package_str = (
                f"\\usepackage[left={m_left:.2f}cm,"
                f"right={m_right:.2f}cm,"
                f"top={m_top:.2f}cm,"
                f"bottom={m_bottom:.2f}cm,"
                f"includefoot, headheight=13.6pt]{{geometry}}" # includefoot and headheight are often useful
            )
        except (ValueError, TypeError) as e:
            print(f"Error processing margin values: {e}. Using default geometry.")
            # Fallback to default if margin values are not valid numbers

    latex_parts = [
        "\\documentclass{article}",
        "\\usepackage{graphicx}",
        "\\usepackage{amsmath}",
        "\\usepackage[utf8]{inputenc}",
        geometry_package_str, # Use the dynamically generated or default string
        "\\usepackage{hyperref}",
        "\\hypersetup{colorlinks=true, linkcolor=blue, filecolor=magenta, urlcolor=cyan, pdftitle={" +
            pdf_filename_no_ext.replace('_', ' ').title() + "}, pdfauthor={PDF Conversion Service}}",
        "\\title{" + pdf_filename_no_ext.replace('_', ' ').title() + "}",
        "\\author{PDF Conversion Service}",
        "\\date{\\today}",
        "\\begin{document}",
        "\\maketitle",
    ]

    extracted_text = content.get('text', '')
    # Apply LaTeX special character escaping first
    replacements = {
        "\\": "\\textbackslash{}", # Must be first
        "{": "\\{", "}": "\\}", "_": "\\_", "^": "\\textasciicircum{}",
        "~": "\\textasciitilde{}", "&": "\\&", "$": "\\$", "#": "\\#",
        "%": "\\%",
        "“": "``", "”": "''", "‘": "`", "’": "'",
        "—": "---", "–": "--",
        "…": "\\dots{}",
    }
    # It is important that the backslash replacement is done first.
    # Otherwise, if some other replacement string contains a backslash,
    # that backslash will be replaced as well.
    # For example, if we have "%": "\\%" and we replace backslashes first,
    # then it becomes "%": "\\textbackslash{}".
    # If we replace backslashes last, then it becomes "%": "\\\\%". This is wrong.
    # The order of other replacements does not matter.

    # Ensure backslash is replaced first
    if '\\' in replacements:
      extracted_text = extracted_text.replace('\\', replacements['\\'])
    for char, latex_char in replacements.items():
        if char == '\\': # Already handled
            continue
        extracted_text = extracted_text.replace(char, latex_char)

    paragraphs = extracted_text.split('\n\n')
    processed_latex_parts = []
    for para_text in paragraphs:
        # Pass the raw paragraph (with LaTeX escapes already applied) to is_math_block
        if is_math_block(para_text):
            # For math blocks, trim whitespace and wrap in $$ ... $$
            # Original newlines within the math block are preserved.
            processed_latex_parts.append(f"$$\n{para_text.strip()}\n$$")
        else:
            # For non-math blocks, convert single newlines to LaTeX line breaks \\
            # and ensure it's not just whitespace.
            if para_text.strip():
                processed_latex_parts.append(para_text.replace('\n', ' \\\\ '))
            elif para_text: # Preserve paragraphs that are only whitespace (e.g. multiple newlines)
                 processed_latex_parts.append(para_text)


    latex_parts.append("\n\n".join(processed_latex_parts))

    # Integrate Math OCR results.
    # If 'math_ocr' results were in `content` (e.g., content['math_ocr'] = {'img_path1': 'latex_str1', ...}),
    # this section would need to be smarter. It would iterate through document elements (text blocks, images).
    # If an image has a corresponding Math OCR LaTeX string, that string would be inserted instead of the image.
    # This might involve a more complex data structure from pdf_parser if text and images are to be interleaved correctly.
    # For now, we just append all images after all text.

    image_paths = content.get('image_paths', [])
    math_ocr_content = content.get('math_ocr', {}) # Expected: {'image_path': 'latex_string'}

    if image_paths:
        latex_parts.append("\n\n\\clearpage % Ensure images start after text, or on new page if needed")
        latex_parts.append("\\section*{Extracted Images/Formulas}") # More generic title
        for img_path in image_paths:
            img_path_latex = img_path.replace("\\", "/")
            img_filename_for_caption = os.path.basename(img_path_latex)
            # Escape underscores in caption filenames for LaTeX
            img_filename_for_caption = img_filename_for_caption.replace('_', '\\_')

            # If this image path has a corresponding Math OCR result (and it's not None/empty), insert that LaTeX.
            ocr_latex = math_ocr_content.get(img_path) # Use .get() for safe access
            if ocr_latex: # This checks if ocr_latex is not None and not an empty string
                latex_parts.append(f"\n% Image {img_filename_for_caption} was OCR'd as a formula:")
                latex_parts.append(ocr_latex) # Append the LaTeX string for the formula
            else:
                # Otherwise, include it as a regular image.
                # This block will be executed if img_path is not in math_ocr_content OR if its value is None/empty.
                latex_parts.append(f"\n\\begin{{figure}}[htbp]")
                latex_parts.append(f"  \\centering")
                # Try to use content width from PDF margins if available for image scaling
                img_width_cm_str = ""
                if margins and 'width' in margins:
                    try:
                        content_width_cm = float(margins['width'])
                        if content_width_cm > 0:
                            # Use a fraction of the content width, e.g. 80%
                            img_width_cm_str = f"width={content_width_cm * 0.8:.2f}cm, "
                    except (ValueError, TypeError):
                        pass # Use default includegraphics options if width is invalid

                latex_parts.append(f"  \\includegraphics[{img_width_cm_str}keepaspectratio]{{{img_path_latex}}}")
                latex_parts.append(f"  \\caption{{Image: {img_filename_for_caption}}}")
                latex_parts.append(f"\\end{{figure}}")

    latex_parts.append("\n\n\\end{document}")

    return "\n".join(latex_parts)

if __name__ == '__main__':
    sample_content_with_margins = {
        "text": "This is page 1 text.\n\nThis is an indented line using spaces.\n\tThis is a tabbed line.",
        "image_paths": ["sample_doc_images/img_p1_1.png"],
        "margins": {'left': 2.54, 'right': 2.54, 'top': 1.9, 'bottom': 1.9, 'width': 15.92, 'height': 25.0}
    }
    sample_pdf_filename = "sample_doc_with_margins"
    latex_output = generate_latex_document(sample_content_with_margins, sample_pdf_filename)
    print(f"--- LaTeX for {sample_pdf_filename}.tex (with margins) ---")
    print(latex_output)

    sample_content_no_margins = {
        "text": "Text for PDF without margin info.",
        "image_paths": [],
        "margins": None
    }
    sample_pdf_filename_no_margins = "sample_doc_no_margins"
    latex_output_no_margins = generate_latex_document(sample_content_no_margins, sample_pdf_filename_no_margins)
    print(f"\n--- LaTeX for {sample_pdf_filename_no_margins}.tex (no margins/default) ---")
    print(latex_output_no_margins)
