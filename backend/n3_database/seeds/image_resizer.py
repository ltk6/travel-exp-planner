"""
Standalone utility to resize and crop seed images.
Reads from seeds/raw_imgs and writes optimized JPEG files into seeds/images.
"""
import os
import sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import setup_logging
from PIL import Image
logger = setup_logging("N3.ImageResizer")

def resize_and_crop(input_path: str, output_path: str, target_size: tuple = (1280, 720)) -> bool:
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

            # Scale down to target resolution (thumbnail avoids scaling up small images)
            img.thumbnail(target_size, Image.LANCZOS)
            
            # Save to new folder
            img.save(output_path, "JPEG", quality=85, optimize=True)
            return True
    except Exception as e:
        logger.error(f"Failed to process {input_path}: {e}")
        return False

def run_optimization(target_size: tuple = (1280, 720)):
    """Process all images from seeds/raw_imgs and save to seeds/images."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(base_dir, "raw_imgs")
    output_dir = os.path.join(base_dir, "images")
    
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
    run_optimization(target_size=(1280, 720))
