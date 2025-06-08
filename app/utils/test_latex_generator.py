import unittest
# Assuming is_math_block is in latex_generator and can be imported.
# If not, tests for it would be indirect via generate_latex_document.
from app.utils.latex_generator import is_math_block, generate_latex_document

class TestIsMathBlock(unittest.TestCase):
    # Test cases for is_math_block directly

    def test_plain_text_paragraphs(self):
        prose1 = """Introduction.
This is the first paragraph. It contains several sentences.
Accented characters like é à ô are common in some languages."""
        prose2 = """This is a second paragraph.
It also contains normal text without any mathematical formulas.
Words like 'for', 'let', 'sum' might appear but not in a math context."""
        self.assertFalse(is_math_block(prose1), "Prose 1 misidentified as math")
        self.assertFalse(is_math_block(prose2), "Prose 2 misidentified as math")

    def test_explicit_display_math(self):
        text_before = "Some introductory text."
        math_block_dollar = r"$$\nE = mc^2\n$$"
        math_block_bracket = r"\\[\n\\sum_{i=0}^n x_i = Y\n\\]"
        text_after = "More text following the equation."

        self.assertFalse(is_math_block(text_before), "Text before explicit math misidentified")
        self.assertTrue(is_math_block(math_block_dollar), "Explicit $$ math block not detected")
        self.assertTrue(is_math_block(math_block_bracket), "Explicit \\[ \\] math block not detected")
        self.assertFalse(is_math_block(text_after), "Text after explicit math misidentified")

        env_equation = r"\\begin{equation}\na^2 + b^2 = c^2\n\\end{equation}"
        env_align = r"\\begin{align}\nx &= y + z \\\\\na &= b * c\n\\end{align}"
        env_gather = r"\\begin{gather*}\nx_1, x_2, x_3 \\\\\ y_1, y_2\n\\end{gather*}" # Added from is_math_block logic

        self.assertTrue(is_math_block(env_equation), "Equation environment not detected")
        self.assertTrue(is_math_block(env_align), "Align environment not detected")
        self.assertTrue(is_math_block(env_gather), "Gather* environment not detected")


    def test_heuristic_display_math(self):
        intro_text = "The first equation is:"
        # This block should be detected due to multiple lines with equation structure
        math_block1 = "a = b + c\nf(x) = x^2 - 2x + 1"
        # This block has LaTeX commands and equation structure
        math_block2 = r"\\frac{d}{dx} \\sin(x) = \\cos(x)\n\\int y dy = \\frac{y^2}{2}"

        self.assertFalse(is_math_block(intro_text), "Intro text for heuristic math misidentified")
        self.assertTrue(is_math_block(math_block1), "Heuristic math block 1 (plain equations) not detected")
        self.assertTrue(is_math_block(math_block2), "Heuristic math block 2 (LaTeX equations) not detected")

    def test_mixed_content_inline_math_is_not_block(self):
        para1 = "This paragraph has inline math like $x > 0$."
        para2 = r"The variable is $\\alpha$ and the sum is $\\sum y_i$."
        para3 = "These should not make the whole paragraph a math block."
        self.assertFalse(is_math_block(para1), "Paragraph with inline math $x>0$ misidentified as block math")
        self.assertFalse(is_math_block(para2), "Paragraph with inline math $\\alpha$ misidentified as block math")
        self.assertFalse(is_math_block(para3), "Plain text paragraph misidentified")

    def test_prose_similar_to_user_feedback(self):
        prose_feedback1 = """Introduction
L'accroissement des capacit´es de simulation num´erique a fait ´emerger de nouvelles probl´ema-
tiques dans le spectre de l'ing´enieur. Apr`es 30 ans de d´eveloppement en mod´elisation
num´erique, les probabilit´es fournissent un cadre adapt´e `a la prise en compte des incertitudes
inh´erentes aux erreurs de mod´elisation et `a la variabilit´e de l'environnement."""
        prose_feedback2 = """Pour maitriser ces concepts modernes, il est n´ecessaire de bien comprendre le cas o`u les
processus sont index´es par des ´el´ements d'ensembles discrets avant d'aborder les outils
complexes issus du calcul stochastique intervenant en conception robuste, mod´elisation
physique et ﬁnanci`ere ou traitement du signal et d'images."""
        self.assertFalse(is_math_block(prose_feedback1), "User feedback prose 1 misidentified as math")
        self.assertFalse(is_math_block(prose_feedback2), "User feedback prose 2 misidentified as math")

    def test_list_items(self):
        text_intro = "Here are some points:"
        latex_item1 = r"\\item First point."
        latex_item2 = r"\\item Second point with some math-like words: sum, let, for."
        markdown_item1 = "- Markdown style list"
        markdown_item2 = "* Another item"

        self.assertFalse(is_math_block(text_intro), "Intro to list misidentified")
        self.assertFalse(is_math_block(latex_item1), "LaTeX item 1 misidentified")
        self.assertFalse(is_math_block(latex_item2), "LaTeX item 2 (with text) misidentified")
        self.assertFalse(is_math_block(markdown_item1), "Markdown item 1 misidentified")
        self.assertFalse(is_math_block(markdown_item2), "Markdown item 2 misidentified")

        # List items that ARE math
        latex_math_item = r"\\item $x^2 + y^2 = z^2$" # This is inline, so block should be False
        self.assertFalse(is_math_block(latex_math_item), "LaTeX item with inline math misidentified as block")

        # A list item that is a full display math block itself (less common but possible)
        # is_math_block should detect the inner $$...$$ and return True.
        # However, the current is_math_block checks startswith("$$"), so this specific case might be False.
        # This depends on how strictly `\item` is a negative indicator vs `$$` being positive.
        # The current `is_math_block` has `text_block.strip().startswith("\\item")` as an early exit `False`.
        latex_item_display_math = r"\\item \n$$\na = b+c\n$$"
        self.assertFalse(is_math_block(latex_item_display_math),
                        "LaTeX item that IS display math was misidentified due to \\item rule")


    def test_short_potentially_ambiguous_lines(self):
        math_line1 = "x = 1"
        text_note = "Note:"
        math_line2 = "y > 2"
        text_conclusion = "Conclusion."

        self.assertTrue(is_math_block(math_line1), "Short math line 'x = 1' not detected")
        self.assertFalse(is_math_block(text_note), "Short text 'Note:' misidentified")
        self.assertTrue(is_math_block(math_line2), "Short math line 'y > 2' not detected")
        self.assertFalse(is_math_block(text_conclusion), "Short text 'Conclusion.' misidentified")

    def test_empty_and_whitespace_strings(self):
        self.assertFalse(is_math_block(""), "Empty string misidentified")
        self.assertFalse(is_math_block("   "), "Whitespace string misidentified")
        self.assertFalse(is_math_block("\n\n"), "Newline string misidentified")

    def test_single_words_vs_math(self):
        self.assertFalse(is_math_block("word"), "Plain word 'word' misidentified")
        self.assertFalse(is_math_block("Hamiltonian"), "Word 'Hamiltonian' misidentified")
        # Single char variables are tricky. Current logic might make them true.
        self.assertTrue(is_math_block("x"), "Single variable 'x' not detected as math")
        self.assertTrue(is_math_block("E"), "Single variable 'E' not detected as math")
        self.assertTrue(is_math_block(r"\\alpha"), "Single LaTeX command '\\alpha' not detected")
        self.assertFalse(is_math_block("Alpha"), "Word 'Alpha' misidentified as math command")

    def test_latex_text_commands(self):
        self.assertFalse(is_math_block(r"\\section{Introduction}"),"\\section misidentified")
        self.assertFalse(is_math_block(r"\\subsection{Details}"), "\\subsection misidentified")
        self.assertFalse(is_math_block(r"\\textit{italic text}"), "\\textit misidentified")
        self.assertFalse(is_math_block(r"\\textbf{bold text}"), "\\textbf misidentified")
        self.assertFalse(is_math_block(r"\\caption{This is a caption. With period.}"),"\\caption misidentified")
        self.assertFalse(is_math_block(r"\\label{fig:myfig}"), "\\label misidentified")
        self.assertFalse(is_math_block(r"\\ref{eq:1}"), "\\ref misidentified")

    def test_more_complex_heuristic_math(self):
        math_block_complex = r"""P(A|B) = \\frac{P(B|A)P(A)}{P(B)}
\\nabla \\cdot E = \\frac{\\rho}{\\epsilon_0}
\\oint_S E \\cdot dA = \\frac{Q_{enc}}{\\epsilon_0}"""
        self.assertTrue(is_math_block(math_block_complex), "Complex heuristic math block not detected")

        text_with_some_symbols = "This line has a > symbol and a = sign but is text."
        self.assertFalse(is_math_block(text_with_some_symbols), "Text with few symbols misidentified as math")

        dense_single_line = r"x_1, x_2, \\ldots, x_n \\in \\mathbb{R}^d"
        self.assertTrue(is_math_block(dense_single_line), "Dense single math line not detected")

        single_equation = r"f(x, y, z) = (x^2 + y^2 + z^2)^{1/2}"
        self.assertTrue(is_math_block(single_equation), "Single line equation not detected")

        # Test case from is_math_block implementation detail: single line, not dense enough
        not_dense_enough = r"a single math word like \\sum here"
        self.assertFalse(is_math_block(not_dense_enough), "Single line with one math word, not dense, misidentified.")

        # Test case for prose with one math keyword
        prose_with_one_keyword = r"This text contains the word \\sum perhaps."
        self.assertFalse(is_math_block(prose_with_one_keyword), "Prose with one math keyword misidentified.")


class TestGenerateLatexMathDetection(unittest.TestCase):
    # Test cases for generate_latex_document, focusing on math detection's impact

    def _get_processed_text_body(self, full_latex_doc: str) -> str:
        start_marker = "\\maketitle\n"
        # Try to find the end of text content before potential image sections or end of document
        end_marker_images = "\n\n\\clearpage" # A common way to start images section
        end_marker_doc = "\n\n\\end{document}"

        start_idx = full_latex_doc.find(start_marker)
        if start_idx == -1: # Fallback if \maketitle is not there (e.g. if title parts are removed)
            start_idx = full_latex_doc.find("\\begin{document}\n") + len("\\begin{document}\n")
            if start_idx < len("\\begin{document}\n"): # if \begin{document} not found either
                 return full_latex_doc # Or raise error, but for testing this might be too strict

        start_idx += len(start_marker) if start_idx >= len(start_marker) else 0

        body_part = full_latex_doc[start_idx:]

        end_idx = len(body_part) # Default to end of what we have

        idx_images = body_part.find(end_marker_images)
        if idx_images != -1:
            end_idx = min(end_idx, idx_images)

        idx_doc_end = body_part.find(end_marker_doc)
        if idx_doc_end != -1:
            end_idx = min(end_idx, idx_doc_end)

        return body_part[:end_idx].strip()


    def test_plain_text_processing_generate_doc(self):
        text = """Introduction.
This is the first paragraph. It contains several sentences.
Accented characters like é à ô are common in some languages.

This is a second paragraph.
It also contains normal text without any mathematical formulas.
Words like 'for', 'let', 'sum' might appear but not in a math context."""
        content = {"text": text} # No margins or images for simplicity
        latex_output = generate_latex_document(content, "test_doc_plain")
        processed_body = self._get_processed_text_body(latex_output)

        self.assertNotIn("$$", processed_body, "Plain text should not be wrapped in $$")
        self.assertIn("Introduction. \\\\ This is the first paragraph.", processed_body)
        self.assertIn("languages.\n\nThis is a second paragraph.", processed_body) # Paragraph break
        self.assertIn("formulas. \\\\ Words like 'for'", processed_body)

        content_with_special_char = {"text": r"Value is 5% and _underscore_ and char \ backslash."}
        latex_output_special = generate_latex_document(content_with_special_char, "test_doc_special")
        processed_body_special = self._get_processed_text_body(latex_output_special)
        self.assertIn(r"Value is 5\% and \_underscore\_ and char \textbackslash{} backslash.", processed_body_special)


    def test_explicit_math_block_generate_doc(self):
        text = """Some intro text.
This line has a $ sign, which should be escaped.

$$
E = mc^2
\\sum x_i = Y
$$

More text. This has an _underscore_.
"""
        content = {"text": text}
        latex_output = generate_latex_document(content, "test_doc_explicit_math")
        processed_body = self._get_processed_text_body(latex_output)

        self.assertIn("Some intro text. \\\\ This line has a \\$ sign", processed_body)
        # Math block should be exactly as input, as it's already $$ wrapped
        self.assertIn(r"$$\nE = mc^2\n\\sum x_i = Y\n$$", processed_body)
        self.assertIn("More text. This has an \\_underscore\\_.", processed_body)
        self.assertNotIn("$$\nSome intro text.", processed_body)

    def test_heuristic_math_block_generate_doc(self):
        text = """This is text.

f(x) = a^2 + b^2 - c^2
E_0 = m_0 c^2

This is more text.

g(y) = y \\times 2
z = \\alpha + \\beta
"""
        content = {"text": text}
        latex_output = generate_latex_document(content, "test_doc_heuristic_math")
        processed_body = self._get_processed_text_body(latex_output)

        self.assertIn("This is text.\n\n", processed_body) # Check it's separate paragraph
        self.assertNotIn("$$\nThis is text.\n$$", processed_body)

        expected_math_block1 = "$$\nf(x) = a^2 + b^2 - c^2\nE_0 = m_0 c^2\n$$"
        self.assertIn(expected_math_block1, processed_body)

        self.assertIn("\n\nThis is more text.\n\n", processed_body)
        expected_math_block2 = r"$$\ng(y) = y \\times 2\nz = \\alpha + \\beta\n$$"
        self.assertIn(expected_math_block2, processed_body)

    def test_user_feedback_prose_generate_doc(self):
        prose_feedback = """Introduction
L'accroissement des capacit´es de simulation num´erique a fait ´emerger de nouvelles probl´ema-
tiques dans le spectre de l'ing´enieur.

Pour maitriser ces concepts modernes, il est n´ecessaire de bien comprendre le cas o`u les
processus sont index´es par des ´el´ements d'ensembles discrets."""
        content = {"text": prose_feedback}
        latex_output = generate_latex_document(content, "test_doc_prose_feedback")
        processed_body = self._get_processed_text_body(latex_output)

        self.assertNotIn("$$", processed_body, "User feedback prose should not be wrapped in $$")
        self.assertIn("Introduction \\\\ L'accroissement des capacit´es", processed_body)
        self.assertIn("l'ing´enieur.\n\nPour maitriser ces concepts", processed_body)


if __name__ == '__main__':
    unittest.main()
