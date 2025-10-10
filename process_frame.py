#!/usr/bin/env python3
"""
Optimized Frame Processing with Alert Debouncing
"""
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add python_modules to path
sys.path.insert(0, str(Path(__file__).parent))

from python_modules.config import Config
from python_modules.classifier import ImageClassifier
from python_modules.threat_detector import ThreatDetector
from python_modules.telegram_notifier import TelegramNotifier
from python_modules.motion_detector import MotionDetector
from python_modules.frame_deduplicator import FrameDeduplicator
from python_modules.image_optimizer import ImageOptimizer

# ===== PERSISTENT STATE (keeps across function calls) =====
class ProcessingState:
    """Singleton to maintain state across function calls"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Initialize once
            cls._instance.motion_detector = MotionDetector(threshold=25, min_change_percent=0.5)
            cls._instance.frame_deduplicator = FrameDeduplicator(similarity_threshold=0.95)
            cls._instance.image_optimizer = ImageOptimizer(max_size_kb=150, quality=85)
            cls._instance.stats = {
                'total_frames': 0,
                'skipped_no_motion': 0,
                'skipped_duplicate': 0,
                'processed': 0,
                'threats_detected': 0,
                'alerts_sent': 0,
                'alerts_debounced': 0
            }
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset all state (call when stream restarts)"""
        if cls._instance:
            cls._instance.motion_detector.reset()
            cls._instance.frame_deduplicator.reset()
            cls._instance.stats = {
                'total_frames': 0,
                'skipped_no_motion': 0,
                'skipped_duplicate': 0,
                'processed': 0,
                'threats_detected': 0,
                'alerts_sent': 0,
                'alerts_debounced': 0
            }

# Get singleton instance
state = ProcessingState()

def process_frame(image_path):
    """
    Process a single frame with smart filtering and alert debouncing
    
    Args:
        image_path: Path to the captured frame
        
    Returns:
        dict: Processing results
    """
    state.stats['total_frames'] += 1
    
    start_time = time.time()
    frame_name = Path(image_path).name
    
    print(f"\n{'='*60}")
    print(f"🎬 Frame {state.stats['total_frames']}: {frame_name}")
    print(f"⏱️  Start: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
    print(f"{'='*60}")
    
    result = {
        'success': False,
        'image_file': frame_name,
        'skipped': False,
        'skip_reason': None,
        'classification': None,
        'threat_analysis': None,
        'alert_sent': False,
        'alert_debounced': False,
        'processing_time': 0,
        'error': None
    }
    
    try:
        # ===== STEP 1: Motion Detection =====
        has_motion, motion_percent = state.motion_detector.detect_motion(image_path)
        
        if not has_motion:
            state.stats['skipped_no_motion'] += 1
            print(f"⏭️  SKIPPED: No motion detected ({motion_percent:.2f}% change)")
            print(f"📊 Stats: {state.stats['processed']} processed, {state.stats['skipped_no_motion']} skipped (no motion)")
            result['success'] = True
            result['skipped'] = True
            result['skip_reason'] = 'no_motion'
            result['motion_percent'] = motion_percent
            return result
        
        print(f"🎯 Motion detected: {motion_percent:.2f}% change")
        
        # ===== STEP 2: Deduplication =====
        is_duplicate, similarity = state.frame_deduplicator.is_duplicate(image_path)
        
        if is_duplicate:
            state.stats['skipped_duplicate'] += 1
            print(f"⏭️  SKIPPED: Duplicate frame ({similarity*100:.1f}% similar)")
            print(f"📊 Stats: {state.stats['processed']} processed, {state.stats['skipped_duplicate']} skipped (duplicate)")
            result['success'] = True
            result['skipped'] = True
            result['skip_reason'] = 'duplicate'
            result['similarity'] = similarity
            return result
        
        print(f"✓ Frame is unique ({similarity*100:.1f}% similar to previous)")
        
        # ===== STEP 3: Image Optimization =====
        optimized_path = state.image_optimizer.optimize(image_path)
        
        # ===== STEP 4: AI Classification =====
        print("\n🤖 Starting AI classification...")
        classify_start = time.time()
        
        classifier = ImageClassifier()
        classification = classifier.classify_image(optimized_path)
        
        classify_time = time.time() - classify_start
        print(f"⏱️  Classification took: {classify_time:.2f}s")
        
        result['classification'] = classification
        
        # Save classification result
        result_file = classifier.save_result(
            image_path,
            classification,
            Config.CLASSIFICATION_RESULTS_DIR
        )
        result['result_file'] = result_file
        
        # ===== STEP 5: Threat Analysis =====
        print("\n🔍 Analyzing threats...")
        threat_start = time.time()
        
        detector = ThreatDetector()
        threat_analysis = detector.analyze_threat(classification, frame_name)
        
        threat_time = time.time() - threat_start
        print(f"⏱️  Threat analysis took: {threat_time:.2f}s")
        
        result['threat_analysis'] = threat_analysis
        state.stats['processed'] += 1
        
        # ===== STEP 6: Send Alert (with debouncing) =====
        if threat_analysis['threat_detected']:
            state.stats['threats_detected'] += 1
            print(f"\n🚨 THREAT DETECTED: {threat_analysis['threat_level']}")
            
            if Config.TELEGRAM_ENABLED:
                print("📱 Checking alert cooldown...")
                alert_start = time.time()
                
                notifier = TelegramNotifier()
                alert_sent = notifier.send_alert(threat_analysis, image_path)
                
                if alert_sent:
                    alert_time = time.time() - alert_start
                    print(f"⏱️  Alert took: {alert_time:.2f}s")
                    state.stats['alerts_sent'] += 1
                    result['alert_sent'] = True
                else:
                    # Check if it was debounced
                    if notifier._should_debounce(threat_analysis['threat_level']):
                        state.stats['alerts_debounced'] += 1
                        result['alert_debounced'] = True
            else:
                print("📱 Telegram notifications disabled")
        else:
            print(f"\n✅ No threats: {threat_analysis['threat_level']}")
        
        result['success'] = True
        
        # Clean up optimized image if different
        if optimized_path != image_path:
            try:
                Path(optimized_path).unlink()
            except:
                pass
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ Processing failed: {error_msg}")
        result['error'] = error_msg
    
    # ===== SUMMARY =====
    total_time = time.time() - start_time
    result['processing_time'] = total_time
    
    print(f"\n{'='*60}")
    print(f"⏱️  Total time: {total_time:.2f}s")
    print(f"📊 Session stats:")
    print(f"   Total frames: {state.stats['total_frames']}")
    print(f"   Processed: {state.stats['processed']}")
    print(f"   Skipped (no motion): {state.stats['skipped_no_motion']}")
    print(f"   Skipped (duplicate): {state.stats['skipped_duplicate']}")
    print(f"   Threats detected: {state.stats['threats_detected']}")
    print(f"   Alerts sent: {state.stats['alerts_sent']}")
    print(f"   Alerts debounced: {state.stats['alerts_debounced']}")
    
    # Calculate cost savings
    total_skipped = state.stats['skipped_no_motion'] + state.stats['skipped_duplicate']
    if state.stats['total_frames'] > 0:
        savings_percent = (total_skipped / state.stats['total_frames']) * 100
        api_calls_saved = total_skipped + state.stats['alerts_debounced']
        print(f"   💰 Cost savings: {savings_percent:.1f}% ({api_calls_saved} API calls avoided)")
    
    print(f"{'='*60}\n")
    
    return result

def main():
    """Main function for command-line usage"""
    if len(sys.argv) < 2:
        print("Usage: python process_frame.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    if not Path(image_path).exists():
        print(f"❌ Image not found: {image_path}")
        sys.exit(1)
    
    # Process the frame
    result = process_frame(image_path)
    
    # Output result as JSON for Node.js to parse
    print("\nPYTHON_RESULT:" + json.dumps(result))
    
    sys.exit(0 if result['success'] else 1)

if __name__ == '__main__':
    main()