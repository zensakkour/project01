
import os
from PIL import Image
from .errors import MathOCRError

# Programmatically load the pix2tex OCR model once
try:
    from pix2tex.cli import LatexOCR
    _latex_ocr = LatexOCR()
except ImportError as e:
    raise ImportError(
        "pix2tex not installed or torch missing. "
        "Run `pip install pix2tex[gui] torch Pillow`"
    ) from e

def convert_image_to_latex(image_path):
    """
    Uses the pix2tex model to convert the image at `image_path`
    into a LaTeX string. Raises MathOCRError on failure.
    """
    if not os.path.exists(image_path):
        raise MathOCRError(f"Image not found: {image_path}")

    try:
        # Load and normalize image
        img = Image.open(image_path).convert("RGB")
        # Pix2tex returns the LaTeX code as a plain string
        latex = _latex_ocr(img)
        return latex.strip()
    except Exception as e:
        # Wrap any error in our MathOCRError
        raise MathOCRError(f"pix2tex failed: {e}")
