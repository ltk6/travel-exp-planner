"""
backend/n3_database/utils/image_resizer.py

Standalone utility to resize and crop images.
Outputs optimized images to a new 'images_optimized' directory.
"""
import os
import logging
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ImageResizer")

def resize_and_crop(input_path: str, output_path: str, target_size: tuple = (1024, 768)) -> bool:
    """
    Resizes and center-crops an image to the target resolution.
    Saves the result to output_path as an optimized JPEG.
    """
    try:
        with Image.open(input_path) as img:
            # Convert to RGB if necessary
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Calculate aspect ratios
            target_ratio = target_size[0] / target_size[1]
            img_ratio = img.width / img.height

            if img_ratio > target_ratio:
                # Image is wider than target ratio: crop sides
                new_width = int(target_ratio * img.height)
                offset = (img.width - new_width) // 2
                img = img.crop((offset, 0, offset + new_width, img.height))
            elif img_ratio < target_ratio:
                # Image is taller than target ratio: crop top/bottom
                new_height = int(img.width / target_ratio)
                offset = (img.height - new_height) // 2
                img = img.crop((0, offset, img.width, offset + new_height))

            # Resize to target resolution
            img = img.resize(target_size, Image.LANCZOS)
            
            # Save to new folder
            img.save(output_path, "JPEG", quality=85, optimize=True)
            return True
    except Exception as e:
        logger.error(f"Failed to process {input_path}: {e}")
        return False

def run_optimization(target_size: tuple = (1024, 768)):
    """Process all images from 'images' and save to 'images_optimized'."""
    # Base directory is backend/n3_database/
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_dir = os.path.join(base_dir, "images")
    output_dir = os.path.join(base_dir, "images_optimized")
    
    if not os.path.exists(input_dir):
        logger.error(f"Input directory not found: {input_dir}")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created output directory: {output_dir}")

    files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    logger.info(f"Starting batch optimization of {len(files)} images...")
    
    success_count = 0
    for filename in files:
        in_path = os.path.join(input_dir, filename)
        # Force .jpg extension for output consistency
        out_name = os.path.splitext(filename)[0] + ".jpg"
        out_path = os.path.join(output_dir, out_name)
        
        if resize_and_crop(in_path, out_path, target_size):
            success_count += 1
            if success_count % 10 == 0:
                logger.info(f"Progress: {success_count}/{len(files)}")

    logger.info(f"Complete. Successfully optimized {success_count}/{len(files)} images.")
    logger.info(f"Results saved in: {output_dir}")

if __name__ == "__main__":
    run_optimization(target_size=(1024, 768))
