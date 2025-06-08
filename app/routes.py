import os
import shutil
import ntpath
import io # For in-memory file operations (zip)
import zipfile # For creating zip archives
from flask import render_template, request, redirect, url_for, flash, send_from_directory, send_file
from werkzeug.utils import secure_filename
from app import app
from app.utils.pdf_parser import extract_content_from_pdf, PDFProcessingError
from app.utils.latex_generator import generate_latex_document

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_pdf():
    if 'pdf_file' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))

    file = request.files['pdf_file']

    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        pdf_filename_no_ext_original, _ = os.path.splitext(original_filename)
        # Sanitize filename for directory/file creation
        safe_pdf_filename_no_ext = "".join(c if c.isalnum() else "_" for c in pdf_filename_no_ext_original)

        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)

        images_source_subfolder_name = f"{safe_pdf_filename_no_ext}_images"
        images_source_full_path = os.path.join(app.config['UPLOAD_FOLDER'], images_source_subfolder_name)

        # LaTeX output filenames and paths
        tex_filename_on_disk = f"{safe_pdf_filename_no_ext}.tex" # e.g. my_safe_doc.tex
        tex_file_path_on_disk = os.path.join(app.config['OUTPUT_FOLDER'], tex_filename_on_disk)

        images_target_subfolder_name = images_source_subfolder_name
        images_target_full_path = os.path.join(app.config['OUTPUT_FOLDER'], images_target_subfolder_name)

        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

        try:
            file.save(pdf_path)
        except Exception as e:
            flash(f"Error saving uploaded file: {e}")
            return redirect(url_for('index'))

        extracted_content = None
        error_message_for_template = None
        generated_latex_code = None

        try:
            extracted_content = extract_content_from_pdf(pdf_path, app.config['UPLOAD_FOLDER'])

            # TODO: Integrate Math OCR if enabled and relevant images are identified
            # Example placeholder for where Math OCR logic would go:
            # math_ocr_results = {} # Store image_path -> latex_string
            # if extracted_content.get("image_paths"):
            #     for img_rel_path in extracted_content["image_paths"]:
            #         # Determine if an image is likely a formula (e.g., by size, position, or a classification step)
            #         is_formula_image = False # Placeholder logic
            #         if is_formula_image:
            #             full_img_path_for_ocr = os.path.join(app.config['UPLOAD_FOLDER'], img_rel_path)
            #             try:
            #                 # from app.utils.math_ocr import convert_image_to_latex, MathOCRError
            #                 # latex_formula = convert_image_to_latex(full_img_path_for_ocr)
            #                 # math_ocr_results[img_rel_path] = latex_formula
            #                 pass # Replace with actual call
            #             except Exception as ocr_error: # MathOCRError or general
            #                 flash(f"Math OCR failed for {img_rel_path}: {ocr_error}")
            #
            # if math_ocr_results:
            #    extracted_content['math_ocr'] = math_ocr_results # Add to content for LaTeX generator

            if not extracted_content["text"].strip() and not extracted_content["image_paths"] and not extracted_content.get("margins"):
                 flash(f"No content (text, images, or margins) could be extracted from {original_filename}.")

            generated_latex_code = generate_latex_document(extracted_content, safe_pdf_filename_no_ext)

            with open(tex_file_path_on_disk, "w", encoding="utf-8") as f:
                f.write(generated_latex_code)

            if extracted_content.get("image_paths"):
                if os.path.exists(images_source_full_path):
                    os.makedirs(images_target_full_path, exist_ok=True)
                    shutil.copytree(images_source_full_path, images_target_full_path, dirs_exist_ok=True)
                else:
                    flash(f"Image source directory {images_source_full_path} not found, skipping image copy for LaTeX.")

        except PDFProcessingError as e:
            flash(str(e))
            error_message_for_template = str(e)
        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}")
            error_message_for_template = f"An unexpected error occurred during processing: {str(e)}"

        return render_template('result.html',
                               original_pdf_filename=original_filename, # For display
                               # Used by download links (safe version for file system)
                               tex_filename_for_download=tex_filename_on_disk,
                               filename_no_ext_for_zip=safe_pdf_filename_no_ext,
                               generated_latex_code=generated_latex_code, # For textarea display
                               # Raw content for review (optional)
                               raw_extracted_content=extracted_content,
                               error_message=error_message_for_template)

    else:
        flash('Invalid file type. Please upload a PDF.')
        return redirect(url_for('index'))

# Route to download the .tex file
@app.route('/download_tex/<path:filename>')
def download_tex_file(filename):
    try:
        return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        flash(f"Error: File {filename} not found in output directory.")
        return redirect(url_for('index')) # Or an error page

# Route to download a ZIP archive of .tex file and its images
@app.route('/download_zip/<path:filename_no_ext>')
def download_zip_archive(filename_no_ext):
    tex_filename = f"{filename_no_ext}.tex"
    image_subfolder_name = f"{filename_no_ext}_images" # This is the folder name inside OUTPUT_FOLDER

    tex_file_path = os.path.join(app.config['OUTPUT_FOLDER'], tex_filename)
    image_folder_path = os.path.join(app.config['OUTPUT_FOLDER'], image_subfolder_name)

    if not os.path.exists(tex_file_path):
        flash(f"Error: Main .tex file {tex_filename} not found for ZIP archive.")
        return redirect(url_for('index')) # Or an error page

    memory_file = io.BytesIO()
    try:
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add .tex file to the root of the zip
            zf.write(tex_file_path, arcname=tex_filename)

            # Add images if the image folder exists
            if os.path.isdir(image_folder_path):
                for root, _, files in os.walk(image_folder_path):
                    for file_in_folder in files:
                        full_file_path = os.path.join(root, file_in_folder)
                        # arcname should be relative to the OUTPUT_FOLDER/image_subfolder_name
                        # e.g., "my_doc_images/img1.png"
                        path_in_zip = os.path.join(image_subfolder_name,
                                                 os.path.relpath(full_file_path, image_folder_path))
                        zf.write(full_file_path, arcname=path_in_zip)
            else:
                # Optional: flash a message if images were expected but folder not found
                # flash(f"Note: Image folder {image_subfolder_name} not found. ZIP will contain .tex file only.")
                pass


    except Exception as e:
        flash(f"Error creating ZIP file: {e}")
        return redirect(url_for('index')) # Or an error page
    finally:
        memory_file.seek(0)

    return send_file(memory_file,
                     download_name=f'{filename_no_ext}.zip',
                     as_attachment=True,
                     mimetype='application/zip')
