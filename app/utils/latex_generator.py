import os

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
    # Basic LaTeX escaping (can be improved with a dedicated library or more rules)
    replacements = {
        "\\": "\\textbackslash{}",
        "{": "\\{", "}": "\\}", "_": "\\_", "^": "\\textasciicircum{}",
        "~": "\\textasciitilde{}", "&": "\\&", "$": "\\$", "#": "\\#",
        "%": "\\%",
        # Consider common unicode characters if inputenc[utf8] doesn't cover them perfectly for LaTeX
        "“": "``", "”": "''", "‘": "`", "’": "'",
        "—": "---", "–": "--",
        "…": "\\dots{}",
    }
    for char, latex_char in replacements.items():
        extracted_text = extracted_text.replace(char, latex_char)

    # Paragraphs are often separated by double newlines in text extraction.
    # LaTeX uses a blank line (or \par) for a new paragraph.
    # Replace multiple newlines with LaTeX paragraph breaks.
    # This is a simple approach; more sophisticated paragraph detection might be needed for complex PDFs.
    processed_text_parts = []
    for para_text in extracted_text.split('\n\n'): # Split by double newlines
        if para_text.strip(): # Avoid empty paragraphs
            processed_text_parts.append(para_text.replace('\n', ' \\\\ ')) # Convert single newlines to LaTeX line breaks
    latex_parts.append("\n\n".join(processed_text_parts)) # Join paragraphs with double newlines for LaTeX

    # TODO: Integrate Math OCR results.
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

            # If this image path has a corresponding Math OCR result, insert that LaTeX instead.
            if img_path in math_ocr_content:
                latex_parts.append(f"\n% Image {img_filename_for_caption} was OCR'd as a formula:")
                latex_parts.append(math_ocr_content[img_path]) # Append the LaTeX string for the formula
            else:
                # Otherwise, include it as a regular image.
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
