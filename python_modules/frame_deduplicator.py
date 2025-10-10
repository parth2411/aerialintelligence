import cv2
import numpy as np
from pathlib import Path

class FrameDeduplicator:
    def __init__(self, similarity_threshold=0.95):
        """
        Initialize frame deduplicator
        
        Args:
            similarity_threshold: How similar frames must be to skip (0-1)
        """
        self.prev_hash = None
        self.similarity_threshold = similarity_threshold
    
    def is_duplicate(self, image_path):
        """
        Check if frame is duplicate of previous frame
        
        Returns:
            tuple: (is_duplicate: bool, similarity: float)
        """
        try:
            # Read and resize frame for faster comparison
            frame = cv2.imread(str(image_path))
            if frame is None:
                return False, 0
            
            # Resize to small size for fast comparison
            small = cv2.resize(frame, (64, 64))
            
            # Compute perceptual hash
            current_hash = self._compute_hash(small)
            
            # First frame
            if self.prev_hash is None:
                self.prev_hash = current_hash
                return False, 0
            
            # Compare with previous frame
            similarity = self._compare_hashes(self.prev_hash, current_hash)
            
            # Update hash
            self.prev_hash = current_hash
            
            # Is duplicate if very similar
            is_dup = similarity >= self.similarity_threshold
            
            return is_dup, similarity
            
        except Exception as e:
            print(f"⚠️  Deduplication error: {e}")
            return False, 0
    
    def _compute_hash(self, image):
        """Compute perceptual hash of image"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Average hash
        avg = gray.mean()
        return (gray > avg).flatten()
    
    def _compare_hashes(self, hash1, hash2):
        """Compare two hashes (returns similarity 0-1)"""
        if len(hash1) != len(hash2):
            return 0
        matches = np.sum(hash1 == hash2)
        return matches / len(hash1)
    
    def reset(self):
        """Reset deduplicator"""
        self.prev_hash = None