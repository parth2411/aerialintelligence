"""
Image Optimization Module
Compress images for faster upload without quality loss
"""
import cv2
from pathlib import Path
from PIL import Image
import io

class ImageOptimizer:
    def __init__(self, max_size_kb=100, quality=85):
        """
        Initialize image optimizer
        
        Args:
            max_size_kb: Target maximum size in KB
            quality: JPEG quality (1-100)
        """
        self.max_size_kb = max_size_kb
        self.quality = quality
    
    def optimize(self, image_path):
        """
        Optimize image for faster upload
        Returns optimized image path or original if small enough
        """
        try:
            # Check current size
            file_size_kb = Path(image_path).stat().st_size / 1024
            
            if file_size_kb <= self.max_size_kb:
                return image_path  # Already small enough
            
            print(f"📦 Compressing image: {file_size_kb:.1f}KB → target {self.max_size_kb}KB")
            
            # Open image
            img = Image.open(image_path)
            
            # Convert to RGB if needed
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Resize if very large
            max_dimension = 1280
            if max(img.size) > max_dimension:
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            
            # Save with compression
            optimized_path = Path(image_path).parent / f"opt_{Path(image_path).name}"
            img.save(optimized_path, 'JPEG', quality=self.quality, optimize=True)
            
            new_size_kb = optimized_path.stat().st_size / 1024
            print(f"✅ Compressed: {new_size_kb:.1f}KB (saved {file_size_kb - new_size_kb:.1f}KB)")
            
            return str(optimized_path)
            
        except Exception as e:
            print(f"⚠️  Optimization failed: {e}")
            return image_path  # Return original if fails