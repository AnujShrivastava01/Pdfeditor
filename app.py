from flask import Flask, request, render_template, send_file, jsonify
import os, uuid, time
import logging
from PIL import Image, ImageEnhance, ImageOps
import fitz  # PyMuPDF
import io

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_and_process():
    try:
        logger.info("Starting PDF processing...")
        pdf_file = request.files['pdf']
        processing_mode = request.form.get('mode', 'white_bg_only')  # default to white background only
        
        if not pdf_file.filename.endswith('.pdf'):
            return jsonify({'error': 'Invalid file type. Please upload a PDF file.'}), 400

        # Check file size (limit to 50MB)
        pdf_file.seek(0, 2)  # Seek to end
        file_size = pdf_file.tell()
        pdf_file.seek(0)  # Seek back to beginning
        
        max_size = 50 * 1024 * 1024  # 50MB
        if file_size > max_size:
            return jsonify({'error': 'File too large. Please upload a PDF smaller than 50MB.'}), 400
        
        logger.info(f"File size: {file_size / (1024*1024):.2f} MB, Mode: {processing_mode}")

        pdf_id = str(uuid.uuid4())
        input_path = os.path.join(UPLOAD_FOLDER, f"{pdf_id}.pdf")
        output_path = os.path.join(UPLOAD_FOLDER, f"{pdf_id}_clean.pdf")
        temp_folder = os.path.join(UPLOAD_FOLDER, pdf_id)

        os.makedirs(temp_folder, exist_ok=True)
        pdf_file.save(input_path)
        logger.info(f"PDF saved: {input_path}")

        # Process PDF using Python libraries
        success, page_count = process_pdf_with_python(input_path, output_path, temp_folder, processing_mode)
        
        if success:
            logger.info("PDF processing completed successfully")
            return jsonify({
                'success': True,
                'file_id': pdf_id,
                'original_name': pdf_file.filename,
                'page_count': page_count
            })
        else:
            logger.error("PDF processing failed")
            return jsonify({'error': 'Failed to process PDF. The file might be corrupted or contain unsupported content.'}), 500

    except Exception as e:
        logger.error(f"Error in upload_and_process: {str(e)}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

def process_pdf_with_python(input_path, output_path, temp_folder, mode='white_bg_only'):
    """Process PDF using Python libraries instead of command line tools"""
    try:
        logger.info("Opening PDF with PyMuPDF...")
        # Open PDF with PyMuPDF
        pdf_document = fitz.open(input_path)
        processed_images = []
        page_count = len(pdf_document)
        
        logger.info(f"Processing {page_count} pages with mode: {mode}")
        
        for page_num in range(page_count):
            logger.info(f"Processing page {page_num + 1} of {page_count}")
            
            # Get page
            page = pdf_document[page_num]
            
            # Render page to image (300 DPI for high quality)
            mat = fitz.Matrix(300/72, 300/72)  # 300 DPI
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Process the image based on mode
            if mode == 'black_white':
                cleaned_img = clean_image_to_black_white(img)
            else:  # white_bg_only
                cleaned_img = clean_image_background(img, mode)
            
            processed_images.append(cleaned_img)
        
        pdf_document.close()
        
        # Convert images back to PDF
        logger.info("Converting images back to PDF...")
        if processed_images:
            # Convert to RGB if needed
            rgb_images = []
            for img in processed_images:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                rgb_images.append(img)
            
            # Save as PDF
            rgb_images[0].save(
                output_path, 
                "PDF", 
                resolution=300.0,
                save_all=True, 
                append_images=rgb_images[1:] if len(rgb_images) > 1 else []
            )
            
            logger.info(f"PDF saved to: {output_path}")
            return True, page_count
        
        return False, 0
        
    except Exception as e:
        logger.error(f"Error in process_pdf_with_python: {str(e)}")
        return False, 0

def clean_image_background(img, mode='white_bg_only'):
    """Clean image background using PIL - optimized for speed with different modes"""
    try:
        # Convert to RGB if not already
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if too large to speed up processing
        original_size = img.size
        max_dimension = 2000
        if max(img.size) > max_dimension:
            ratio = max_dimension / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert to numpy array for faster processing
        import numpy as np
        img_array = np.array(img)
        
        if mode == 'black_white':
            # Black text, white background mode
            result_array = convert_to_black_white(img_array)
        else:
            # White background only mode (preserve colors)
            result_array = convert_background_only(img_array)
        
        # Convert back to PIL Image
        result = Image.fromarray(result_array.astype(np.uint8))
        
        # Resize back to original size if we resized earlier
        if result.size != original_size:
            result = result.resize(original_size, Image.Resampling.LANCZOS)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in clean_image_background: {str(e)}")
        return img  # Return original if processing fails

def convert_to_black_white(img_array):
    """Convert image to pure black text on white background using advanced thresholding"""
    import numpy as np
    
    # Convert to grayscale
    if len(img_array.shape) == 3:
        # Use luminance formula for better grayscale conversion
        gray = np.dot(img_array[...,:3], [0.299, 0.587, 0.114])
    else:
        gray = img_array
    
    # Apply Gaussian blur to reduce noise
    from scipy.ndimage import gaussian_filter
    blurred = gaussian_filter(gray, sigma=1)
    
    # Calculate average brightness to determine if it's a dark or light background
    avg_brightness = np.mean(blurred)
    logger.info(f"Average brightness: {avg_brightness:.1f}")
    
    # Use Otsu's method for automatic threshold selection
    # This finds the optimal threshold that separates foreground and background
    hist, bin_edges = np.histogram(blurred.astype(np.uint8), bins=256, range=(0, 256))
    
    # Otsu's algorithm
    total_pixels = blurred.size
    current_max = 0
    threshold = 0
    
    sum_total = np.sum(np.arange(256) * hist)
    sum_background = 0
    weight_background = 0
    
    for i in range(256):
        weight_background += hist[i]
        if weight_background == 0:
            continue
        
        weight_foreground = total_pixels - weight_background
        if weight_foreground == 0:
            break
        
        sum_background += i * hist[i]
        mean_background = sum_background / weight_background
        mean_foreground = (sum_total - sum_background) / weight_foreground
        
        # Calculate between-class variance
        variance_between = weight_background * weight_foreground * (mean_background - mean_foreground) ** 2
        
        if variance_between > current_max:
            current_max = variance_between
            threshold = i
    
    # For dark backgrounds, we might need to invert the logic
    if avg_brightness < 100:
        # Dark background - text is likely lighter
        # Adjust threshold to be more selective
        threshold = min(threshold, avg_brightness + 20)
        text_mask = blurred > threshold
    else:
        # Light background - text is likely darker
        # Adjust threshold to be more selective  
        threshold = max(threshold, avg_brightness - 20)
        text_mask = blurred < threshold
    
    logger.info(f"Using threshold: {threshold}")
    
    # Create result image
    result = np.full_like(img_array, 255)  # Start with white
    
    # Apply text mask - make text pixels black
    if len(img_array.shape) == 3:
        result[text_mask] = [0, 0, 0]  # Black text
    else:
        result[text_mask] = 0
    
    # Count text pixels for verification
    text_pixels = np.sum(text_mask)
    text_percentage = (text_pixels / text_mask.size) * 100
    logger.info(f"Text pixels: {text_pixels} ({text_percentage:.1f}%)")
    
    return result

def clean_image_to_black_white(img):
    """Enhanced black and white conversion with better text detection"""
    try:
        # Convert to RGB if not already
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if too large to speed up processing
        original_size = img.size
        max_dimension = 2000
        if max(img.size) > max_dimension:
            ratio = max_dimension / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert to numpy array
        import numpy as np
        img_array = np.array(img)
        
        # Use the enhanced black-white conversion
        result_array = convert_to_black_white(img_array)
        
        # Convert back to PIL Image
        result = Image.fromarray(result_array.astype(np.uint8))
        
        # Resize back to original size if we resized earlier
        if result.size != original_size:
            result = result.resize(original_size, Image.Resampling.LANCZOS)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in clean_image_to_black_white: {str(e)}")
        return img  # Return original if processing fails

def convert_background_only(img_array):
    """Convert only dark backgrounds to white, preserve other colors"""
    import numpy as np
    
    # Identify very dark pixels (likely dark background)
    threshold = 60
    dark_mask = np.all(img_array < threshold, axis=2)
    
    # Create result array
    result_array = img_array.copy()
    
    # Make dark background pixels white
    result_array[dark_mask] = [255, 255, 255]
    
    return result_array

@app.route('/download/<file_id>')
def download_file(file_id):
    try:
        output_path = os.path.join(UPLOAD_FOLDER, f"{file_id}_clean.pdf")
        
        if not os.path.exists(output_path):
            logger.error(f"File not found: {output_path}")
            return jsonify({'error': 'File not found or has expired'}), 404
        
        logger.info(f"Serving download for file: {file_id}")
        
        response = send_file(
            output_path,
            as_attachment=True,
            download_name='cleaned_document.pdf',
            mimetype='application/pdf'
        )
        
        # Get file size for Content-Length header
        file_size = os.path.getsize(output_path)
        response.headers['Content-Length'] = str(file_size)
        
        logger.info(f"Serving download for file: {file_id}, size: {file_size} bytes")
        return response
        
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
