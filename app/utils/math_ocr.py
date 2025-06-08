import os
import re
from PIL import Image
from texify.inference import batch_inference
from texify.model.model import load_model
from texify.model.processor import load_processor

# Lazy-load the Texify model and processor
_model = None
_processor = None
def _init_texify():
    global _model, _processor
    if _model is None or _processor is None:
        _model     = load_model()
        _processor = load_processor()

def convert_image_to_latex(img_path: str) -> str:
    """
    OCR a formula image using Texify and return
    the first $$…$$ chunk (or wrap the inline/math)
    """
    if not os.path.exists(img_path):
        raise FileNotFoundError(f"Image not found: {img_path}")

    _init_texify()
    img = Image.open(img_path).convert("RGB")
    results = batch_inference([img], _model, _processor)
    if not results:
        raise RuntimeError("No OCR output from Texify")

    md = results[0]
    # 1) try display math
    match = re.search(r"\$\$(.+?)\$\$", md, re.DOTALL)
    if match:
        return f"$$ {match.group(1).strip()} $$"
    # 2) try inline math
    inline = re.search(r"\$(.+?)\$", md)
    if inline:
        return f"$$ {inline.group(1).strip()} $$"
    # 3) fallback: wrap entire output
    return f"$$ {md.strip()} $$"
