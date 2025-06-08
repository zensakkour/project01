import os
import re

# Helper function to identify math blocks
def is_math_block(text_block: str) -> bool:
    # Normalize: remove leading/trailing whitespace
    text_block = text_block.strip()
    if not text_block:
        return False

    # Explicit LaTeX math environments (high confidence)
    # Added \begin{align*} and \end{align*}
    if (text_block.startswith("$$") and text_block.endswith("$$")) or \
       (text_block.startswith("\\[") and text_block.endswith("\\]")) or \
       (text_block.startswith("\\begin{equation}") and text_block.endswith("\\end{equation}")) or \
       (text_block.startswith("\\begin{equation*}") and text_block.endswith("\\end{equation*}")) or \
       (text_block.startswith("\\begin{align}") and text_block.endswith("\\end{align}")) or \
       (text_block.startswith("\\begin{align*}") and text_block.endswith("\\end{align*}")) or \
       (text_block.startswith("\\begin{gather}") and text_block.endswith("\\end{gather}")) or \
       (text_block.startswith("\\begin{gather*}") and text_block.endswith("\\end{gather*}")) or \
       (text_block.startswith("\\begin{multline}") and text_block.endswith("\\end{multline}")) or \
       (text_block.startswith("\\begin{multline*}") and text_block.endswith("\\end{multline*}")):
        return True

    lines = text_block.split('\n')
    num_lines = len(lines)

    # If it's very long and not explicitly delimited, probably not a single math block
    if num_lines > 15:  # Tunable parameter
        prose_indicators = 0
        # Check first few lines for prose-like characteristics (long words and a period)
        # More robust check for sentence structure might involve checking for capital letter at start.
        for i in range(min(3, num_lines)): # Check first few lines
             # Check for a capital letter at the beginning of the line, a long word, and a period.
            if re.search(r'^[A-Z]', lines[i].lstrip()) and re.search(r'[a-zA-Z]{5,}', lines[i]) and '.' in lines[i]:
                prose_indicators += 1
        if prose_indicators > 1:  # If multiple initial lines look like prose
            return False

    math_line_count = 0
    # Regex for common math keywords (ensure they are standalone, e.g., \sum not part of a word)
    # Made keywords more specific, requiring backslash. Includes common operators.
    # Note: Original prompt had unescaped ( in (\sum|...). Corrected to \\( for literal parenthesis if needed,
    # but for grouping it's fine. The current regex uses \ for LaTeX commands.
    # Added more keywords like \mathbb, \mathcal, \mathbf, \mathrm, etc.
    # Added single letter Greek letters like \pi, \phi etc. that were in the original spec.
    math_keywords_re = re.compile(
        r"\\(?:sum|int|frac|sqrt|lim|prod|partial|nabla|infty|forall|exists|in|notin|"
        r"subset|supset|approx|equiv|neq|leq|geq|times|div|pm|mp|cdot|circ|wedge|vee|cap|cup|"
        r"oplus|otimes|perp|angle|hbar|ell|wp|Re|Im|mathbb|mathcal|mathbf|mathrm|mathsf|mathtt|"
        r"alpha|beta|gamma|Gamma|delta|Delta|epsilon|varepsilon|zeta|eta|theta|Theta|iota|kappa|"
        r"lambda|Lambda|mu|nu|xi|Xi|pi|Pi|rho|sigma|Sigma|tau|upsilon|Upsilon|phi|Phi|chi|psi|Psi|omega|Omega)|"
        r"[=<>+\-*/^_{}()\[\]|%]"  # Common operators and delimiters
    )
    # Regex for typical equation structures (e.g., var = expr, lines with many operators)
    # This pattern looks for an assignment or common binary operations.
    equation_pattern_re = re.compile(r"^\s*([a-zA-Z0-9\s_^{}]+\s*=\s*.+)|(\S+\s*[*\/+\-<>]\s*\S+)")

    # Avoid classifying list items or very short text as math unless very obvious
    if text_block.strip().startswith("\\item"): # Handles LaTeX \item
        return False
    if text_block.strip().startswith("* ") or text_block.strip().startswith("- "): # Handles markdown-like list items
        # Check if it's a list item that is NOT math.
        # If it's short and doesn't have strong math signals, assume it's a list item.
        if num_lines == 1 and len(text_block) < 30 and not math_keywords_re.search(text_block):
            return False


    # Heuristic: check for prose indicators (long words, sentence structure)
    # This is a strong negative indicator.
    words = text_block.split()
    # Consider it prose if it has many words and sentence-ending punctuation,
    # and relatively few math keywords.
    if len(words) > 25 and any(word.endswith(('.', '?', '!', ':')) for word in words): # Reduced word count threshold
        math_keyword_matches = math_keywords_re.findall(text_block)
        # If math keywords are sparse compared to number of lines or a fixed low count.
        if len(math_keyword_matches) < max(2, num_lines / 3) : # Tunable: e.g. less than 2 keywords or < 1/3rd of lines
             return False

    for line_idx, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Skip comment lines in LaTeX
        if line_stripped.startswith("%"):
            continue

        # Strong indicators of a math line
        # Check if keywords or equation patterns are present.
        # Also, check if the line is almost entirely composed of math-related characters.
        # (e.g. digits, operators, braces, common variable names like x, y, z, t, n, k, i, j)
        non_space_chars = len(line_stripped.replace(" ", ""))
        if non_space_chars > 0: # Avoid division by zero for empty lines after stripping
            math_char_count = len(re.findall(r"[a-zA-Z0-9_^{}\[\]()+\-*/=<>.,:;\s\\]", line_stripped))
            # A line is likely math if over 70% of its chars are math-related,
            # or it contains specific math keywords/patterns.
            # This ratio is a heuristic.
            is_dense_math_line = (math_char_count / non_space_chars) > 0.7

            if math_keywords_re.search(line_stripped) or equation_pattern_re.search(line_stripped) or is_dense_math_line:
                math_line_count += 1
            # Check for lines that are clearly text (e.g., start with \section, \subsection, or known text commands)
            elif re.match(r"^\s*\\(section|subsection|subsubsection|caption|text|item)\b", line_stripped):
                # This line is explicitly text, so it shouldn't count towards math_line_count
                # And if we find too many such lines, the block is likely not math.
                pass # Effectively counts as a non-math line.


    if num_lines == 0: return False

    # Decision logic:
    # 1. Short blocks (1-3 lines): need at least one clearly math line.
    # 2. Medium blocks (4-10 lines): need a higher proportion (e.g., >50%) of math lines.
    # 3. Longer blocks (>10 lines): need a very high proportion (e.g., >60-70%) or other strong signals,
    #    already partly handled by the num_lines > 15 check.

    if num_lines <= 3:
        # For very short blocks, also check character density if only one line is "mathy"
        if math_line_count >= 1:
            if num_lines == 1: # Single line block
                # For a single line, require high density of math characters or explicit math keywords/equation patterns
                # unless it's explicitly delimited (handled at the start)
                non_space_chars = len(text_block.replace(" ", ""))
                if non_space_chars > 0:
                    math_chars_in_block = len(math_keywords_re.findall(text_block)) # Count actual math keywords/symbols
                    # A single line must be very math heavy or have multiple keywords.
                    # Or be an equation.
                    if equation_pattern_re.search(text_block) or math_chars_in_block >= 2 or \
                       (len(re.findall(r"[a-zA-Z0-9_^{}\[\]()+\-*/=<>.,\s\\]", text_block)) / non_space_chars > 0.8 and non_space_chars > 5):
                        return True
                    else: # Single line that's not dense enough
                        return False
                else: # Empty single line
                    return False
            return True # 2-3 lines with at least one math line
    elif num_lines <= 10: # Medium blocks
        if math_line_count / num_lines >= 0.5: # At least 50% math lines
            return True
    else: # Longer blocks (already filtered by num_lines > 15 initial check)
        if math_line_count / num_lines >= 0.6: # Stricter for longer blocks, >60%
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
