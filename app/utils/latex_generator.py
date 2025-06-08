import os
import re

# Helper function to identify math blocks
def is_math_block(text_block: str) -> bool:
    text_block = text_block.strip()
    if not text_block:
        return False

    # 1. Check for explicit LaTeX math environments (highest confidence)
    # Using a more robust check for paired delimiters
    explicit_env_pairs = {
        "$$": "$$", # Needs careful handling due to regex special chars if used in re.
        "\\[": "\\]",
        "\\begin{equation}": "\\end{equation}",
        "\\begin{equation*}": "\\end{equation*}",
        "\\begin{align}": "\\end{align}",
        "\\begin{align*}": "\\end{align*}",
        "\\begin{gather}": "\\end{gather}",
        "\\begin{gather*}": "\\end{gather*}",
        "\\begin{multline}": "\\end{multline}",
        "\\begin{multline*}": "\\end{multline*}",
        "\\begin{displaymath}": "\\end{displaymath}",
        # "\\begin{math}": "\\end{math}", # Usually inline, but can be used for blocks. Too ambiguous?
    }

    for start_delim, end_delim in explicit_env_pairs.items():
        # Need to escape for regex if using re.match, but startswith/endswith are fine for fixed strings.
        # Handle $ and \ for startswith/endswith
        esc_start = start_delim.replace("$", "\\$").replace("[", "\\[")
        esc_end = end_delim.replace("$", "\\$").replace("]", "\\]")

        if text_block.startswith(start_delim) and text_block.endswith(end_delim):
            return True
        # A common pattern for $$ is to have them on their own lines.
        if start_delim == "$$" and text_block.startswith("$$\n") and text_block.endswith("\n$$"):
            return True


    lines = text_block.split('\n')
    num_lines = len(lines)

    # 2. Strong Negative Indicators (Prose & Structure)
    # LaTeX sectioning, list items, text formatting commands are strong non-math indicators
    # Using raw strings for regex patterns
    latex_text_commands_re = re.compile(
        r"^\s*\\(section|subsection|subsubsection|paragraph|caption|label|ref|textit|textbf|texttt|item|footnote|chapter|part|textnormal|emph)\b",
        re.IGNORECASE
    )
    if any(latex_text_commands_re.match(line) for line in lines):
        return False # If any line starts with these commands, assume it's not a math block.

    # Markdown list items (conservative: if a line looks like a list item, and the block is short and not dense with math)
    markdown_list_re = re.compile(r"^\s*([-*+]|\d+\.)\s+")
    if any(markdown_list_re.match(line) for line in lines):
        # Count non-list lines; if all are list items or very few non-list items, it's likely a list.
        non_list_lines = sum(1 for line in lines if not markdown_list_re.match(line))
        # If the block is short, and mostly list items, and not overwhelmingly math.
        if num_lines <= 5 and non_list_lines <=1:
             # Check overall math density for this potential list
            math_symbols_in_block = len(re.findall(r"[=+\-*/^_{}\[\]<>\\$]|\\(frac|sum|int|sqrt|mathbb|mathcal|mathbf)", text_block))
            if math_symbols_in_block < num_lines : # If fewer math symbols than lines, probably a text list
                return False


    # Simple prose check: more than N words, ends with sentence punctuation.
    words = text_block.split()
    # Adjusted word count and added check for multiple sentences for longer blocks.
    if len(words) > 8 and any(text_block.endswith(punc) for punc in ['.', '?', '!']):
        # Count basic math-like characters (operators, brackets, some keywords)
        math_indicators_count = len(re.findall(r"[=+\-*/^_{}\[\]<>\\$]|\\(frac|sum|int|sqrt|alpha|beta|gamma|mathbb|mathcal|mathbf)", text_block))

        # If it has sentence structure and few math indicators, it's likely prose.
        # Example: "This is a sentence with x = 1." might have one indicator.
        # Threshold: if math indicators are less than, say, 1 for every 10 words, or less than num_lines / 2.
        if math_indicators_count < max(1, len(words) / 10, num_lines / 2):
            # Further check: number of lines ending with punctuation
            sentence_end_count = sum(1 for line in lines if any(line.strip().endswith(punc) for punc in ['.', '?', '!']))
            if sentence_end_count > num_lines / 2 or (num_lines ==1 and sentence_end_count ==1): # Majority of lines end like sentences
                 return False

    # If it's a very long block and not explicitly delimited, it's likely prose or mixed.
    # Stricter: >5 lines is already quite long for an undelimited math block.
    if num_lines > 5 and not (text_block.startswith("$$") or text_block.startswith("\\[") or text_block.startswith("\\begin")):
        # Exception: if it's ALL math lines (e.g. a long derivation)
        # This needs the math line checker below.
        pass # Will be checked by line-by-line analysis later.

    # Specific test cases from failures: "Conclusion.", "Hamiltonian", "Note:", "Introduction"
    # These should be caught by the prose checks or lack of math indicators.
    # Adding a small list of common non-math short headers/phrases:
    common_short_prose = ["conclusion", "introduction", "summary", "abstract", "results", "discussion", "methods", "note", "figure", "table", "appendix"]
    if num_lines == 1 and len(words) <= 2 and text_block.lower().strip('.').strip(':') in common_short_prose:
        return False


    # 3. Stricter Heuristics for Undelimited Math
    # Count "equation-like" lines.
    # Using a more specific regex for LaTeX commands (must start with \\)
    # and common math symbols.
    math_keywords_re = re.compile(
        r"\\(?:sum|int|frac|sqrt|lim|alpha|beta|gamma|delta|omega|sin|cos|log|prod|partial|nabla|infty|forall|exists|in|notin|"
        r"subset|supset|approx|equiv|neq|leq|geq|times|div|pm|mp|cdot|circ|wedge|vee|cap|cup|oplus|otimes|perp|angle|hbar|"
        r"mathbb|mathcal|mathbf|mathrm|mathsf|mathtt|textrm|textit|textbf)|" # LaTeX commands
        r"[=<>+\-*/^_{}()\[\]|%]"  # Individual symbols
    )

    equation_line_count = 0
    strong_math_line_count = 0 # Lines that are almost certainly math

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith("%"): # Skip empty or comment lines
            continue

        # Check 1: Presence of equals sign with substantial content, or common equation structures
        # e.g. something = something, or f(x) = ..., or \frac{...}{...} = ...
        if re.search(r"\S+\s*=\s*\S+", line_stripped) or \
           re.search(r"^[a-zA-Z0-9_]+\(.+\)\s*=", line_stripped) or \
           re.search(r"\\frac.+=", line_stripped):
            equation_line_count += 1
            strong_math_line_count +=1
            continue

        # Check 2: Presence of multiple distinct math keywords or structures
        # (e.g., \frac, \sum, \int, \sqrt, \lim, common operators if many)
        # Or a mix of keywords and operators.
        found_keywords = math_keywords_re.findall(line_stripped)
        num_math_keywords = len(found_keywords)

        # Consider a line strongly math if it has a LaTeX command AND an operator/bracket,
        # or multiple LaTeX commands, or multiple operators.
        has_latex_cmd = any(kw.startswith("\\") for kw in found_keywords)
        has_operator_or_bracket = any(kw in "=<>+-*/^_{}()[]|%" for kw in found_keywords)

        if (has_latex_cmd and has_operator_or_bracket) or \
           (has_latex_cmd and num_math_keywords > 1) or \
           (num_math_keywords > 2 and not has_latex_cmd): # e.g. ( x + y ) ^ 2
            equation_line_count += 1
            strong_math_line_count +=1
            continue
        elif has_latex_cmd and num_lines ==1: # Single line, single command (e.g. "\alpha")
            equation_line_count +=1 # Tentatively count it
            # No strong_math_line_count increment here unless it's complex.
            continue
        elif num_math_keywords >= 1 and num_lines == 1 and len(words) < 3 and len(line_stripped) < 15 : # e.g. x_1 or E_0
             # Short, few words, one math keyword/symbol found by regex
             if re.fullmatch(r"[a-zA-Z0-9_^{}]+", line_stripped.replace("\\", "")): # Check if it's just a variable name with sub/super
                 equation_line_count +=1
                 continue


    if num_lines == 0: return False

    # Decision logic:
    # Case 1: Single line block
    if num_lines == 1:
        # Must be a strong math line or have multiple indicators if not an explicit environment
        if strong_math_line_count >= 1:
            return True
        if equation_line_count >=1: # Counted by the weaker single-line checks
             # Check if it's a very simple variable/constant or a single LaTeX command
            if len(words) <= 2 and len(text_block) < 15 :
                 # e.g. "x", "E_0", "\alpha"
                 # Avoid classifying "alpha" (word) as math unless it's "\alpha"
                 if text_block.startswith("\\") or re.fullmatch(r"[a-zA-Z0-9_^{}\[\]()+\-*/=<>|%]+", text_block) :
                    if not (text_block.lower() in common_short_prose or (len(text_block)>3 and text_block.isalpha() and not text_block.startswith("\\"))):
                         return True
        return False # Otherwise, single undelimited lines are not math by default

    # Case 2: Multi-line blocks (require a higher proportion of mathy lines)
    # And not too many words overall, unless keywords are very dense.
    # At least 60% of lines must look like equations (strong or regular).
    # Or, at least 40% must be *strong* math lines.
    if (equation_line_count / num_lines >= 0.6) or \
       (strong_math_line_count / num_lines >= 0.4 and num_lines <=5) : # more lenient for shorter multi-line
        # Additional check for very wordy blocks that might still pass above thresholds
        if len(words) > num_lines * 7 and num_lines > 2: # Avg more than 7 words per line for >2 lines
            # If very wordy, require even higher proportion of math lines
            if equation_line_count / num_lines < 0.8:
                return False # Likely prose with some equations interspersed
        return True

    # Check for long blocks that weren't caught by the earlier num_lines > 5 check
    # if they didn't meet the equation_line_count criteria
    if num_lines > 5 and equation_line_count / num_lines < 0.5:
        return False # Too long, not enough math lines

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
