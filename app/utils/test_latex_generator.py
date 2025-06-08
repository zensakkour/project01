import unittest
import os # Needed for os.path.basename
from app.utils.latex_generator import generate_latex_document

class TestLatexGenerator(unittest.TestCase):

    def test_generate_latex_with_math_ocr_content(self):
        math_formula_latex = r"$$E=mc^2$$"
        image_path_for_formula = "images/formula1.png" # Relative path as used in content

        content = {
            "text": "This document contains a formula.",
            "image_paths": [image_path_for_formula, "images/another_image.png"],
            "margins": {'left': 2, 'right': 2, 'top': 2, 'bottom': 2, 'width': 17, 'height': 25.7},
            "math_ocr": {
                image_path_for_formula: math_formula_latex
            }
        }
        pdf_filename_no_ext = "test_doc_with_formula"

        generated_latex = generate_latex_document(content, pdf_filename_no_ext)

        # 1. Check that the math_formula_latex is included as is
        self.assertIn(math_formula_latex, generated_latex,
                      "Math OCR LaTeX string was not found or was altered in the generated document.")

        # 2. Check that the image replaced by the formula is NOT included as a regular \includegraphics
        #    but IS commented as being replaced.
        img_filename_for_caption = os.path.basename(image_path_for_formula)
        # Escape underscores for the caption check, as done in latex_generator
        img_filename_for_caption_escaped = img_filename_for_caption.replace('_', '\\_')

        expected_comment_for_ocr = f"% Image {img_filename_for_caption_escaped} was OCR'd as a formula:"
        self.assertIn(expected_comment_for_ocr, generated_latex,
                      "Comment indicating image was OCR'd is missing.")

        # Ensure the formula follows its specific comment. Note: LaTeX generator adds a newline after the comment.
        self.assertIn(f"{expected_comment_for_ocr}\n{math_formula_latex}", generated_latex,
                      f"Math OCR formula does not directly follow its introductory comment. Looking for:\n{expected_comment_for_ocr}\n{math_formula_latex}")

        # 3. Check that the specific \includegraphics command for the formula image is not present
        #    in the section of the document where this image is handled.
        #    The structure is: comment, then formula. There should be no \includegraphics for this image.

        # Find the start of the comment for the OCR'd image
        comment_start_index = generated_latex.find(expected_comment_for_ocr)
        self.assertTrue(comment_start_index != -1, "OCR comment not found.")

        # Find the start of the formula immediately after the comment
        formula_start_index = generated_latex.find(math_formula_latex, comment_start_index)
        self.assertTrue(formula_start_index != -1, "Formula not found after its comment.")

        # The segment between the end of the comment and the start of the formula should just be a newline
        segment_between = generated_latex[comment_start_index + len(expected_comment_for_ocr):formula_start_index]
        self.assertEqual(segment_between.strip(), "",
                         f"Expected only whitespace between OCR comment and formula, found: '{segment_between.strip()}'")

        # Also check that the other image ("images/another_image.png") IS included as a graphic
        other_image_path = "images/another_image.png"
        other_image_path_latex = other_image_path.replace("\\", "/")
        self.assertIn(f"\includegraphics[keepaspectratio]{{{other_image_path_latex}}}", generated_latex,
                      "The other standard image was not found in the document.")


    def test_generate_latex_with_math_ocr_and_other_images(self):
        math_formula_latex = r"$$\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}$$" # Corrected fracc
        formula_image_path = "images/integral.png"
        regular_image_filename = "photo.png"
        regular_image_path = f"images/{regular_image_filename}" # Path as in image_paths

        content = {
            "text": "Document with a formula and a regular image.",
            "image_paths": [formula_image_path, regular_image_path], # Order matters for sequential processing
            "margins": {'left': 1, 'right': 1, 'top': 1, 'bottom': 1, 'width': 19, 'height': 27.7},
            "math_ocr": {
                formula_image_path: math_formula_latex
            }
        }
        pdf_filename_no_ext = "test_doc_mixed_content"

        generated_latex = generate_latex_document(content, pdf_filename_no_ext)

        # 1. Check formula is present
        self.assertIn(math_formula_latex, generated_latex,
                      "Math OCR LaTeX string (integral) was not found or was altered.")

        # 2. Check comment for formula image
        formula_img_basename_escaped = os.path.basename(formula_image_path).replace('_', '\\_')
        expected_comment_for_formula = f"% Image {formula_img_basename_escaped} was OCR'd as a formula:"
        self.assertIn(expected_comment_for_formula, generated_latex)
        # Ensure the formula follows its specific comment. Note: LaTeX generator adds a newline.
        self.assertIn(f"{expected_comment_for_formula}\n{math_formula_latex}", generated_latex,
                      f"Math OCR formula (integral) does not directly follow its comment. Looking for:\n{expected_comment_for_formula}\n{math_formula_latex}")

        # 3. Check regular image IS included
        regular_img_path_latex = regular_image_path.replace("\\", "/")
        # This check assumes the image is included with keepaspectratio.
        # A more robust check might look for includegraphics and the path separately.
        # The path in \includegraphics uses forward slashes
        # Check for \includegraphics[...]{images/photo.png}
        # The exact options for includegraphics can vary (e.g. width might be present or not)
        # So, we check for the core part:
        self.assertIn(f"\includegraphics", generated_latex, "No \\includegraphics command found for the regular image.")
        self.assertIn(f"{{{regular_img_path_latex}}}", generated_latex, f"Regular image path {regular_img_path_latex} not found in any \\includegraphics.")
        # Check it's part of a figure environment
        figure_env_for_regular_image_pattern = (
            f"\\begin{{figure}}[htbp]\n"
            f"  \\centering\n"
            # The width part might or might not be there depending on margins.
            # So, we search for the image path within an includegraphics command that is within a figure environment.
            # This is becoming complex to assert robustly without parsing LaTeX.
            # For now, assertIn(f"{{{regular_img_path_latex}}}", generated_latex) is the most direct.
        )
        # Let's make sure the regular image is actually in a figure environment
        regular_image_figure_start = generated_latex.rfind(f"\\begin{{figure}}[htbp]", 0, generated_latex.find(f"{{{regular_img_path_latex}}}"))
        self.assertNotEqual(regular_image_figure_start, -1, "Regular image does not seem to be in a figure environment.")
        regular_image_figure_end = generated_latex.find(f"\\end{{figure}}", generated_latex.find(f"{{{regular_img_path_latex}}}"))
        self.assertNotEqual(regular_image_figure_end, -1, "Regular image does not seem to be in a figure environment that closes.")


        # 4. Check that the formula image is NOT included as a standard graphic after its comment
        comment_start_index = generated_latex.find(expected_comment_for_formula)
        formula_start_index = generated_latex.find(math_formula_latex, comment_start_index)
        segment_between = generated_latex[comment_start_index + len(expected_comment_for_formula) : formula_start_index]

        self.assertEqual(segment_between.strip(), "",
                         f"There should be no content (like an \\includegraphics command for the formula image) between the OCR comment and the formula itself. Found: '{segment_between.strip()}'")

if __name__ == '__main__':
    unittest.main()
