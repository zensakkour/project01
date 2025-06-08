import fitz  # PyMuPDF
import os
import ntpath # For path basename

class PDFProcessingError(Exception):
    """Custom exception for PDF processing errors."""
    pass

def extract_content_from_pdf(pdf_path: str, base_image_output_folder: str) -> dict:
    """
    Extracts text content, images, and page margins from a PDF file.
    Images are saved into a subdirectory within base_image_output_folder.
    Margin information is extracted from the first page.

    Args:
        pdf_path: The path to the PDF file.
        base_image_output_folder: The base directory where images should be stored.

    Returns:
        A dictionary containing:
        - 'text': The combined text content from all pages.
        - 'image_paths': A list of relative paths to the extracted images.
        - 'margins': A dictionary with 'left', 'right', 'top', 'bottom' margins,
                     and 'width', 'height' of the content area in centimeters.
                     Returns None if margins can't be determined (e.g., empty PDF).
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF {pdf_path}: {e}")
        raise PDFProcessingError(f"Could not open or read PDF file: {pdf_path}") from e

    text_content = []
    image_paths = []
    margins_cm = None
    points_to_cm = 2.54 / 72.0

    if len(doc) == 0:
        doc.close()
        # Return empty content but indicate no margins could be read
        return {
            "text": "",
            "image_paths": [],
            "margins": None # Or some default like {'left': 2, 'right': 2, 'top': 2, 'bottom': 2, 'width': 17, 'height': 25.7}
        }

    # Extract margins from the first page
    try:
        first_page = doc[0]
        media_box = first_page.mediabox # Typically the physical page size
        crop_box = first_page.rect      # Typically the visible/printable area (CropBox)

        # If CropBox is (0,0,0,0) it's likely not set, use MediaBox
        if crop_box.is_empty or crop_box.is_infinite:
            # This can happen if the CropBox isn't properly defined.
            # Fallback to using MediaBox as the content area, assuming no specific crop.
            # In this case, margins relative to MediaBox would be zero.
            # For simplicity, we'll use MediaBox as the page dimensions and assume zero effective margins
            # if CropBox is not providing useful data.
            # A more sophisticated approach might try to find a common CropBox or use heuristic.
            print(f"Warning: CropBox for {pdf_path} is invalid ({crop_box}). Using MediaBox dimensions with zero margins.")
            effective_rect = media_box
            left_margin_pts = 0.0
            top_margin_pts = 0.0
            right_margin_pts = 0.0
            bottom_margin_pts = 0.0
            content_width_pts = media_box.width
            content_height_pts = media_box.height
        else:
            # Standard calculation based on CropBox relative to MediaBox
            # Margins are the space outside the CropBox but within the MediaBox
            left_margin_pts = crop_box.x0 - media_box.x0
            top_margin_pts = crop_box.y0 - media_box.y0
            right_margin_pts = media_box.x1 - crop_box.x1
            bottom_margin_pts = media_box.y1 - crop_box.y1

            content_width_pts = crop_box.width
            content_height_pts = crop_box.height

            # Sanity check for negative margins (can happen if CropBox is outside MediaBox)
            if left_margin_pts < 0: left_margin_pts = 0
            if top_margin_pts < 0: top_margin_pts = 0
            if right_margin_pts < 0: right_margin_pts = 0
            if bottom_margin_pts < 0: bottom_margin_pts = 0


        margins_cm = {
            'left': left_margin_pts * points_to_cm,
            'right': right_margin_pts * points_to_cm,
            'top': top_margin_pts * points_to_cm,
            'bottom': bottom_margin_pts * points_to_cm,
            'width': content_width_pts * points_to_cm, # Content area width
            'height': content_height_pts * points_to_cm # Content area height
        }
    except Exception as e:
        print(f"Error extracting margins from {pdf_path}: {e}. Using default margins.")
        # Provide default A4-like margins if extraction fails
        margins_cm = {'left': 2, 'right': 2, 'top': 2, 'bottom': 2, 'width': 17, 'height': 25.7}


    # Create a unique directory for this PDF's images
    pdf_filename = ntpath.basename(pdf_path)
    pdf_filename_without_ext = os.path.splitext(pdf_filename)[0]
    safe_pdf_dirname = "".join(c if c.isalnum() else "_" for c in pdf_filename_without_ext)
    pdf_image_dir_name = f"{safe_pdf_dirname}_images"
    specific_image_output_dir = os.path.join(base_image_output_folder, pdf_image_dir_name)

    os.makedirs(specific_image_output_dir, exist_ok=True)

    try:
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text_content.append(page.get_text())
            image_list = page.get_images(full=True)
            for img_index, img_info in enumerate(image_list):
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                except Exception as e:
                    print(f"Error extracting image xref {xref} from page {page_num} of {pdf_path}: {e}")
                    continue
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                image_filename = f"img_p{page_num + 1}_{img_index + 1}.{image_ext}"
                relative_image_path = os.path.join(pdf_image_dir_name, image_filename)
                full_image_path = os.path.join(specific_image_output_dir, image_filename)
                try:
                    with open(full_image_path, "wb") as img_file:
                        img_file.write(image_bytes)
                    image_paths.append(relative_image_path)
                except Exception as e:
                    print(f"Error saving image {full_image_path}: {e}")
    except Exception as e:
        print(f"Error processing PDF pages for text/images in {pdf_path}: {e}")
        # We might have partial content, so don't raise immediately, let it return what it has
        # Or, re-raise if it's critical:
        # doc.close()
        # raise PDFProcessingError(f"Error extracting page content from PDF: {pdf_path}") from e

    doc.close()
    return {
        "text": "".join(text_content),
        "image_paths": image_paths,
        "margins": margins_cm
    }

if __name__ == '__main__':
    sample_pdf_path = "sample_for_margins.pdf"
    output_dir_for_images = "test_pdf_images_output_margins"

    if not os.path.exists(sample_pdf_path):
        try:
            dummy_doc = fitz.open()
            page = dummy_doc.new_page(width=595, height=842) # A4 size in points
            # Default MediaBox is (0,0,595,842)
            # Set a CropBox to simulate margins: x0, y0, x1, y1
            # e.g., 1 inch margins (72 points)
            page.set_cropbox(fitz.Rect(72, 72, 595-72, 842-72))
            page.insert_text((100, 100), "Hello, PDF with margins.")
            dummy_doc.save(sample_pdf_path)
            dummy_doc.close()
            print(f"Created dummy '{sample_pdf_path}' with defined CropBox for testing.")
        except Exception as e:
            print(f"Could not create dummy PDF for margin testing: {e}")

    if os.path.exists(sample_pdf_path):
        os.makedirs(output_dir_for_images, exist_ok=True)
        print(f"Attempting to process '{sample_pdf_path}' for margins and content...")
        try:
            content = extract_content_from_pdf(sample_pdf_path, output_dir_for_images)
            print("\nExtracted Text:")
            print(content['text'])
            print("\nExtracted Image Paths:")
            for p in content['image_paths']: print(p)
            if not content['image_paths']: print("No images.")
            print("\nExtracted Margins (cm):")
            if content['margins']:
                for k, v in content['margins'].items():
                    print(f"  {k}: {v:.2f} cm")
            else:
                print("No margin information extracted or PDF was empty.")
        except PDFProcessingError as e:
            print(f"PDF Processing Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
    else:
        print(f"'{sample_pdf_path}' not found. Please create it or provide a valid PDF path for testing.")
