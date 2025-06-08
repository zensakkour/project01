import unittest
from unittest.mock import patch, MagicMock # Added MagicMock
import os
from app.utils.math_ocr import convert_image_to_latex

# A dummy image path used for tests where the actual image content doesn't matter due to mocking
DUMMY_IMG_PATH = "dummy.png"

class TestMathOCR(unittest.TestCase):

    @patch('app.utils.math_ocr._init_texify', return_value=None)
    @patch('app.utils.math_ocr.os.path.exists', return_value=True)
    @patch('app.utils.math_ocr.Image.open', return_value=MagicMock()) # Added Image.open mock
    @patch('app.utils.math_ocr.batch_inference')
    def test_with_display_math_output(self, mock_batch_inference, mock_image_open, mock_os_exists, mock_init_texify):
        mock_batch_inference.return_value = [r'Some text before $$\sum x_i$$ some text after']
        result = convert_image_to_latex(DUMMY_IMG_PATH)
        self.assertEqual(result, r"$$ \sum x_i $$")
        mock_init_texify.assert_called_once()
        mock_os_exists.assert_called_once_with(DUMMY_IMG_PATH)
        mock_image_open.assert_called_once_with(DUMMY_IMG_PATH)

    @patch('app.utils.math_ocr._init_texify', return_value=None)
    @patch('app.utils.math_ocr.os.path.exists', return_value=True)
    @patch('app.utils.math_ocr.Image.open', return_value=MagicMock()) # Added Image.open mock
    @patch('app.utils.math_ocr.batch_inference')
    def test_with_inline_math_output(self, mock_batch_inference, mock_image_open, mock_os_exists, mock_init_texify):
        mock_batch_inference.return_value = [r'Some text before $x^2+y^2$ some text after']
        result = convert_image_to_latex(DUMMY_IMG_PATH)
        self.assertEqual(result, r"$$ x^2+y^2 $$")
        mock_init_texify.assert_called_once()
        mock_os_exists.assert_called_once_with(DUMMY_IMG_PATH)
        mock_image_open.assert_called_once_with(DUMMY_IMG_PATH)

    @patch('app.utils.math_ocr._init_texify', return_value=None)
    @patch('app.utils.math_ocr.os.path.exists', return_value=True)
    @patch('app.utils.math_ocr.Image.open', return_value=MagicMock()) # Added Image.open mock
    @patch('app.utils.math_ocr.batch_inference')
    def test_with_no_math_output(self, mock_batch_inference, mock_image_open, mock_os_exists, mock_init_texify):
        mock_batch_inference.return_value = ['Just some regular text without math.']
        result = convert_image_to_latex(DUMMY_IMG_PATH)
        self.assertIsNone(result)
        mock_init_texify.assert_called_once()
        mock_os_exists.assert_called_once_with(DUMMY_IMG_PATH)
        mock_image_open.assert_called_once_with(DUMMY_IMG_PATH)

    @patch('app.utils.math_ocr._init_texify', return_value=None)
    @patch('app.utils.math_ocr.os.path.exists', return_value=True)
    @patch('app.utils.math_ocr.Image.open', return_value=MagicMock()) # Added Image.open mock
    @patch('app.utils.math_ocr.batch_inference')
    def test_with_empty_texify_output_string(self, mock_batch_inference, mock_image_open, mock_os_exists, mock_init_texify):
        mock_batch_inference.return_value = ['']
        result = convert_image_to_latex(DUMMY_IMG_PATH)
        self.assertIsNone(result)
        mock_init_texify.assert_called_once()
        mock_os_exists.assert_called_once_with(DUMMY_IMG_PATH)
        mock_image_open.assert_called_once_with(DUMMY_IMG_PATH)

    @patch('app.utils.math_ocr._init_texify', return_value=None)
    @patch('app.utils.math_ocr.os.path.exists', return_value=True)
    @patch('app.utils.math_ocr.Image.open', return_value=MagicMock()) # Added Image.open mock
    @patch('app.utils.math_ocr.batch_inference')
    def test_texify_runtime_error_empty_list(self, mock_batch_inference, mock_image_open, mock_os_exists, mock_init_texify):
        mock_batch_inference.return_value = []
        with self.assertRaisesRegex(RuntimeError, "No OCR output from Texify"):
            convert_image_to_latex(DUMMY_IMG_PATH)
        mock_init_texify.assert_called_once()
        mock_os_exists.assert_called_once_with(DUMMY_IMG_PATH)
        mock_image_open.assert_called_once_with(DUMMY_IMG_PATH)

    @patch('app.utils.math_ocr._init_texify', return_value=None)
    @patch('app.utils.math_ocr.os.path.exists', return_value=False)
    @patch('app.utils.math_ocr.Image.open') # Mock Image.open so it's available for assert_not_called
    def test_image_not_found(self, mock_image_open, mock_os_exists, mock_init_texify):
        # _init_texify IS called before os.path.exists
        # Image.open should NOT be called if os.path.exists is False

        # Use a unique path for this test to ensure mocks are clean for this specific path
        non_existent_dummy_path = "nonexistent_dummy.png"

        # Configure the mock for os.path.exists specifically for this path
        # This is safer if DUMMY_IMG_PATH was used elsewhere with different mock settings for os.path.exists
        mock_os_exists.side_effect = lambda path: False if path == non_existent_dummy_path else True

        with self.assertRaisesRegex(FileNotFoundError, f"Image not found: {non_existent_dummy_path}"):
            convert_image_to_latex(non_existent_dummy_path)

        mock_init_texify.assert_called_once()
        mock_os_exists.assert_any_call(non_existent_dummy_path) # Check that it was called with this path
        mock_image_open.assert_not_called() # Crucial: Image.open should not be called

if __name__ == '__main__':
    unittest.main()
