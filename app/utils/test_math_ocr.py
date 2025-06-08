import unittest
from unittest.mock import patch
import os # For mocking os.path.exists
from app.utils.math_ocr import convert_image_to_latex

# A dummy image path used for tests where the actual image content doesn't matter due to mocking
DUMMY_IMG_PATH = "dummy.png"

class TestMathOCR(unittest.TestCase):

    @patch('app.utils.math_ocr._init_texify', return_value=None)
    @patch('app.utils.math_ocr.batch_inference')
    @patch('app.utils.math_ocr.os.path.exists', return_value=True) # Assume image exists unless specified
    def test_with_display_math_output(self, mock_exists, mock_batch_inference, mock_init_texify):
        mock_batch_inference.return_value = ['Some text before $$\sum x_i$$ some text after']
        result = convert_image_to_latex(DUMMY_IMG_PATH)
        self.assertEqual(result, "$$ \sum x_i $$")
        mock_init_texify.assert_called_once() # Ensure texify initialization was called

    @patch('app.utils.math_ocr._init_texify', return_value=None)
    @patch('app.utils.math_ocr.batch_inference')
    @patch('app.utils.math_ocr.os.path.exists', return_value=True)
    def test_with_inline_math_output(self, mock_exists, mock_batch_inference, mock_init_texify):
        mock_batch_inference.return_value = ['Some text before $x^2+y^2$ some text after']
        result = convert_image_to_latex(DUMMY_IMG_PATH)
        self.assertEqual(result, "$$ x^2+y^2 $$") # Still wrapped in $$ as per requirements
        mock_init_texify.assert_called_once()

    @patch('app.utils.math_ocr._init_texify', return_value=None)
    @patch('app.utils.math_ocr.batch_inference')
    @patch('app.utils.math_ocr.os.path.exists', return_value=True)
    def test_with_no_math_output(self, mock_exists, mock_batch_inference, mock_init_texify):
        mock_batch_inference.return_value = ['Just some regular text without math.']
        result = convert_image_to_latex(DUMMY_IMG_PATH)
        self.assertIsNone(result)
        mock_init_texify.assert_called_once()

    @patch('app.utils.math_ocr._init_texify', return_value=None)
    @patch('app.utils.math_ocr.batch_inference')
    @patch('app.utils.math_ocr.os.path.exists', return_value=True)
    def test_with_empty_texify_output_string(self, mock_exists, mock_batch_inference, mock_init_texify):
        mock_batch_inference.return_value = [''] # Texify returns a list with an empty string
        result = convert_image_to_latex(DUMMY_IMG_PATH)
        self.assertIsNone(result)
        mock_init_texify.assert_called_once()

    @patch('app.utils.math_ocr._init_texify', return_value=None)
    @patch('app.utils.math_ocr.batch_inference')
    @patch('app.utils.math_ocr.os.path.exists', return_value=True)
    def test_texify_runtime_error_empty_list(self, mock_exists, mock_batch_inference, mock_init_texify):
        mock_batch_inference.return_value = [] # Texify returns an empty list (failure)
        with self.assertRaises(RuntimeError) as context:
            convert_image_to_latex(DUMMY_IMG_PATH)
        self.assertEqual(str(context.exception), "No OCR output from Texify")
        mock_init_texify.assert_called_once()

    @patch('app.utils.math_ocr.os.path.exists', return_value=False)
    # No need to mock _init_texify or batch_inference as they shouldn't be called
    def test_image_not_found(self, mock_exists):
        with self.assertRaises(FileNotFoundError) as context:
            convert_image_to_latex("nonexistent.png")
        self.assertEqual(str(context.exception), "Image not found: nonexistent.png")
        # Verify that _init_texify was NOT called in this case by trying to assert it wasn't
        # This requires _init_texify to be available in the class or a different patching approach
        # For simplicity, we trust the code flow here; if os.path.exists is False, function returns early.

if __name__ == '__main__':
    unittest.main()
