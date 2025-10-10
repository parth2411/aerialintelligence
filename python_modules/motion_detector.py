"""
Motion Detection Module
Skips frames with no motion to save API calls and speed up response
"""
import cv2
import numpy as np
from pathlib import Path

class MotionDetector:
    def __init__(self, threshold=25, min_change_percent=0.5):
        """
        Initialize motion detector
        
        Args:
            threshold: Pixel difference threshold (0-255)
            min_change_percent: Minimum % of frame that must change (0.5 = 0.5%)
        """
        self.prev_frame = None
        self.threshold = threshold
        self.min_change_percent = min_change_percent
        self.frame_count = 0
    
    def detect_motion(self, image_path):
        """
        Detect if there's significant motion in the frame
        
        Returns:
            tuple: (has_motion: bool, motion_percent: float)
        """
        self.frame_count += 1
        
        try:
            # Read and preprocess frame
            frame = cv2.imread(str(image_path))
            if frame is None:
                return True, 0  # Process if can't read
            
            # Convert to grayscale and blur to reduce noise
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)
            
            # First frame - always process
            if self.prev_frame is None:
                self.prev_frame = gray
                return True, 100.0
            
            # Compute absolute difference between current and previous frame
            frame_delta = cv2.absdiff(self.prev_frame, gray)
            
            # Apply threshold to get binary image
            thresh = cv2.threshold(frame_delta, self.threshold, 255, cv2.THRESH_BINARY)[1]
            
            # Dilate to fill gaps
            thresh = cv2.dilate(thresh, None, iterations=2)
            
            # Calculate percentage of frame that changed
            motion_pixels = np.sum(thresh > 0)
            total_pixels = thresh.size
            motion_percent = (motion_pixels / total_pixels) * 100
            
            # Update previous frame
            self.prev_frame = gray
            
            # Motion detected if change exceeds threshold
            has_motion = motion_percent >= self.min_change_percent
            
            return has_motion, motion_percent
            
        except Exception as e:
            print(f"⚠️  Motion detection error: {e}")
            return True, 0  # Process frame if error
    
    def reset(self):
        """Reset motion detector (call when stream restarts)"""
        self.prev_frame = None
        self.frame_count = 0