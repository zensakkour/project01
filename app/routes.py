import os, shutil, io, zipfile
from flask import (
    render_template, request, redirect,
    url_for, flash, send_from_directory, send_file
)
from werkzeug.utils import secure_filename

from app import app
from app.utils.pdf_parser import extract_content_from_pdf, PDFProcessingError
from app.utils.latex_generator import generate_latex_document
from app.utils.math_ocr import convert_image_to_latex

ALLOWED_EXTENSIONS = {'pdf'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_pdf():
    if 'pdf_file' not in request.files:
        flash('No file part'); return redirect(url_for('index'))
    file = request.files['pdf_file']
    if file.filename == '':
        flash('No selected file'); return redirect(url_for('index'))
    if not allowed_file(file.filename):
        flash('Invalid file type. Please upload a PDF.'); return redirect(url_for('index'))

    orig = secure_filename(file.filename)
    base, _ = os.path.splitext(orig)
    safe = "".join(c if c.isalnum() else "_" for c in base)
    UP, OP = app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER']
    os.makedirs(UP, exist_ok=True); os.makedirs(OP, exist_ok=True)

    pdf_path = os.path.join(UP, orig)
    imgs_sub = f"{safe}_images"
    img_src  = os.path.join(UP, imgs_sub)
    img_dst  = os.path.join(OP, imgs_sub)
    tex_file = f"{safe}.tex"
    tex_path = os.path.join(OP, tex_file)

    try:
        file.save(pdf_path)
        content = extract_content_from_pdf(pdf_path, UP)

        # --- Math OCR pass ---
        math_results = {}
        for img_rel in content.get("image_paths", []):
            img_full = os.path.join(UP, img_rel)
            try:
                math_results[img_rel] = convert_image_to_latex(img_full)
            except Exception as e:
                flash(f"⚠️ Math OCR failed for {img_rel}: {e}")
        if math_results:
            content['math_ocr'] = math_results

        if not (content.get("text","").strip()
                or content.get("image_paths")
                or content.get("margins")):
            flash(f"No content extracted from {orig}.")

        # Generate & save LaTeX
        latex = generate_latex_document(content, safe)
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex)

        # Copy images for ZIP
        if os.path.isdir(img_src):
            os.makedirs(img_dst, exist_ok=True)
            shutil.copytree(img_src, img_dst, dirs_exist_ok=True)

    except PDFProcessingError as e:
        flash(str(e)); latex = None
    except Exception as e:
        flash(f"Unexpected error: {e}"); latex = None

    return render_template(
        'result.html',
        original_pdf_filename=orig,
        tex_filename_for_download=tex_file,
        filename_no_ext_for_zip=safe,
        generated_latex_code=latex,
        raw_extracted_content=content,
        error_message=None
    )

@app.route('/download_tex/<path:filename>')
def download_tex_file(filename):
    try:
        return send_from_directory(OP, filename, as_attachment=True)
    except FileNotFoundError:
        flash(f"File {filename} not found."); return redirect(url_for('index'))

@app.route('/download_zip/<path:filename_no_ext>')
def download_zip_archive(filename_no_ext):
    tex = f"{filename_no_ext}.tex"
    imgs= f"{filename_no_ext}_images"
    texp = os.path.join(OP, tex)
    imgp = os.path.join(OP, imgs)
    if not os.path.exists(texp):
        flash(f"{tex} not found."); return redirect(url_for('index'))

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(texp, arcname=tex)
        if os.path.isdir(imgp):
            for root, _, files in os.walk(imgp):
                for fn in files:
                    full = os.path.join(root, fn)
                    arc  = os.path.join(imgs, os.path.relpath(full, imgp))
                    zf.write(full, arcname=arc)
    mem.seek(0)
    return send_file(mem,
                     download_name=f"{filename_no_ext}.zip",
                     as_attachment=True,
                     mimetype='application/zip')
