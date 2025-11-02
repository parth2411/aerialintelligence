# Python Modules - AI Threat Detection Pipeline

This directory contains the Python modules that power the AI-driven threat detection system. These modules work together to process video frames, detect threats, and send alerts.

## Overview

The Python modules are called from the Node.js server via the [process_frame.py](../process_frame.py) script, which orchestrates the entire frame processing pipeline with smart filtering and optimization.

## Module Architecture

```
python_modules/
├── config.py                 # Configuration and environment management
├── motion_detector.py        # Motion detection and frame filtering
├── frame_deduplicator.py     # Duplicate frame detection
├── image_optimizer.py        # Image compression and optimization
├── classifier.py             # AI-powered image classification
├── threat_detector.py        # Threat analysis and severity assessment
├── telegram_notifier.py      # Alert notifications via Telegram
└── requirements.txt          # Python dependencies
```

## Module Details

### 1. config.py

**Purpose**: Centralized configuration management using environment variables

**Key Features**:
- Loads configuration from `.env` file
- Validates required API keys and settings
- Provides configuration constants for all modules

**Configuration Options**:
```python
NVIDIA_API_KEY              # Required: NVIDIA API key for Florence-2 model
NVIDIA_API_URL              # Florence-2 API endpoint
TELEGRAM_ENABLED            # Enable/disable Telegram notifications
TELEGRAM_BOT_TOKEN          # Telegram bot token
TELEGRAM_CHAT_ID            # Telegram chat ID for alerts
THREAT_THRESHOLD            # Minimum threat level for alerts (1-5)
CLASSIFICATION_TASK         # AI classification task type
ALERT_COOLDOWN_SECONDS      # Cooldown between alerts (debouncing)
CAPTURED_FRAMES_DIR         # Directory for captured frames
CLASSIFICATION_RESULTS_DIR  # Directory for classification results
```

**Usage**:
```python
from python_modules.config import Config

# Access configuration
api_key = Config.NVIDIA_API_KEY
telegram_enabled = Config.TELEGRAM_ENABLED

# Validate configuration
Config.validate()
```

---

### 2. motion_detector.py

**Purpose**: Detect motion in frames to skip processing static scenes

**How It Works**:
- Compares consecutive frames using OpenCV
- Calculates pixel-level differences
- Determines if significant motion occurred
- Reduces API calls by ~40-60% in typical scenarios

**Key Features**:
- Frame-to-frame comparison using computer vision
- Configurable threshold for motion sensitivity
- Percentage-based change detection
- State management for frame history

**Usage**:
```python
from python_modules.motion_detector import MotionDetector

detector = MotionDetector(threshold=25, min_change_percent=0.5)
has_motion, motion_percent = detector.detect_motion(image_path)

if has_motion:
    print(f"Motion detected: {motion_percent:.2f}% change")
```

**Parameters**:
- `threshold`: Pixel difference threshold (default: 25)
- `min_change_percent`: Minimum percentage of changed pixels (default: 0.5%)

---

### 3. frame_deduplicator.py

**Purpose**: Identify and skip duplicate or nearly identical frames

**How It Works**:
- Uses perceptual hashing (pHash) for image similarity
- Compares current frame with previous unique frame
- Skips frames that are too similar to previous ones
- Further reduces API calls by ~20-30%

**Key Features**:
- Perceptual hash-based similarity detection
- Configurable similarity threshold
- Efficient duplicate detection
- Works with compressed images

**Usage**:
```python
from python_modules.frame_deduplicator import FrameDeduplicator

deduplicator = FrameDeduplicator(similarity_threshold=0.95)
is_duplicate, similarity = deduplicator.is_duplicate(image_path)

if not is_duplicate:
    print(f"Unique frame ({similarity*100:.1f}% similar)")
```

**Parameters**:
- `similarity_threshold`: Similarity threshold for duplicates (default: 0.95)

---

### 4. image_optimizer.py

**Purpose**: Compress and optimize images before sending to AI API

**How It Works**:
- Resizes images to reduce file size
- Applies JPEG compression
- Maintains aspect ratio
- Reduces bandwidth and API costs

**Key Features**:
- Smart resizing with aspect ratio preservation
- Quality-based JPEG compression
- File size targeting
- Temporary optimized file creation

**Usage**:
```python
from python_modules.image_optimizer import ImageOptimizer

optimizer = ImageOptimizer(max_size_kb=150, quality=85)
optimized_path = optimizer.optimize(image_path)

print(f"Original: {original_size}KB → Optimized: {optimized_size}KB")
```

**Parameters**:
- `max_size_kb`: Target maximum file size in KB (default: 150)
- `quality`: JPEG quality 1-100 (default: 85)

---

### 5. classifier.py

**Purpose**: AI-powered image classification using NVIDIA Florence-2 model

**How It Works**:
- Sends images to NVIDIA's Florence-2 API
- Receives detailed image descriptions
- Saves classification results to JSON
- Provides structured data for threat analysis

**Key Features**:
- Vision-language model integration
- Detailed caption generation
- Error handling and retry logic
- Result persistence to disk

**Usage**:
```python
from python_modules.classifier import ImageClassifier

classifier = ImageClassifier()
classification = classifier.classify_image(image_path)

print(f"Description: {classification['description']}")
print(f"Confidence: {classification.get('confidence', 'N/A')}")

# Save result
result_file = classifier.save_result(
    image_path,
    classification,
    results_dir
)
```

**API Integration**:
- Uses NVIDIA Florence-2 vision-language model
- Supports custom classification tasks
- Returns detailed scene descriptions
- Handles API errors gracefully

---

### 6. threat_detector.py

**Purpose**: Analyze image classifications for security threats

**How It Works**:
- Analyzes AI-generated descriptions using pattern matching
- Assigns threat severity levels (CRITICAL, HIGH, MEDIUM, LOW, NONE)
- Identifies specific threat keywords
- Provides confidence scores and recommended actions

**Threat Severity Levels**:

| Level | Priority | Examples |
|-------|----------|----------|
| **CRITICAL (5)** | Immediate danger | Weapons, violence, break-ins, fires, explosions |
| **HIGH (4)** | Urgent concern | Unauthorized persons, masked individuals, fence climbing |
| **MEDIUM (3)** | Potential threat | Unusual objects, loitering, after-hours activity |
| **LOW (2)** | Minor anomaly | Unexpected movement, unclear situations |
| **NONE (1)** | No threat | Normal activity |

**Usage**:
```python
from python_modules.threat_detector import ThreatDetector

detector = ThreatDetector()
analysis = detector.analyze_threat(classification, frame_name)

if analysis['threat_detected']:
    print(f"🚨 Threat: {analysis['threat_level']}")
    print(f"Confidence: {analysis['confidence']}%")
    print(f"Keywords: {', '.join(analysis['threat_keywords'])}")
    print(f"Action: {analysis['recommended_action']}")
```

**Analysis Output**:
```python
{
    'threat_detected': bool,
    'threat_level': str,           # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'NONE'
    'threat_score': int,           # 1-5
    'confidence': int,             # 0-100
    'threat_keywords': list,       # Detected threat keywords
    'description': str,            # Full description
    'recommended_action': str,     # Suggested action
    'frame': str                   # Frame filename
}
```

---

### 7. telegram_notifier.py

**Purpose**: Send security alerts via Telegram with debouncing

**How It Works**:
- Sends formatted threat alerts to Telegram
- Includes threat images as attachments
- Implements cooldown periods to prevent alert spam
- Different cooldown times based on threat severity

**Key Features**:
- Rich alert formatting with emojis and structure
- Image attachment support
- Alert debouncing with configurable cooldown
- Severity-based cooldown periods
- Retry logic for failed sends

**Alert Cooldown Periods**:
- CRITICAL: 30 seconds
- HIGH: 60 seconds
- MEDIUM: 120 seconds
- LOW: 180 seconds
- NONE: No alerts sent

**Usage**:
```python
from python_modules.telegram_notifier import TelegramNotifier

notifier = TelegramNotifier()
alert_sent = notifier.send_alert(threat_analysis, image_path)

if alert_sent:
    print("✅ Alert sent successfully")
else:
    print("⏸️  Alert debounced (cooldown active)")
```

**Alert Format**:
```
🚨 SAFETY ALERT - CRITICAL PRIORITY 🚨

⏰ Time: 10/10/2025, 3:45:12 PM

🔍 DETECTED SITUATION:
[AI-generated description]

⚠️ THREAT INDICATORS:
• keyword1
• keyword2

🎯 CONFIDENCE: 95%

📋 RECOMMENDED ACTION:
[Action based on threat level]

📱 This is an automated safety monitoring alert.
```

---

## Processing Pipeline

The modules work together in a specific sequence orchestrated by [process_frame.py](../process_frame.py):

```
1. Motion Detection (motion_detector.py)
   ↓ (Skip if no motion)

2. Deduplication Check (frame_deduplicator.py)
   ↓ (Skip if duplicate)

3. Image Optimization (image_optimizer.py)
   ↓

4. AI Classification (classifier.py)
   ↓

5. Threat Analysis (threat_detector.py)
   ↓

6. Alert Notification (telegram_notifier.py)
   ↓ (Only if threat detected and cooldown expired)

Result: Processed frame with threat assessment
```

## Installation

### 1. Install Python Dependencies

```bash
# From the project root
pip install -r python_modules/requirements.txt
```

Or manually:
```bash
pip install requests pillow opencv-python python-telegram-bot python-dotenv
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# NVIDIA API Configuration
NVIDIA_API_KEY=your_nvidia_api_key_here

# Telegram Configuration
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Threat Detection Settings
THREAT_THRESHOLD=3              # MEDIUM and above (1-5)
ALERT_COOLDOWN_SECONDS=60       # Cooldown between alerts

# Classification Settings
CLASSIFICATION_TASK=<DETAILED_CAPTION>

# Directory Paths
CAPTURED_FRAMES_DIR=./data/captured_frames
CLASSIFICATION_RESULTS_DIR=./data/classification_results
```

### 3. Test the Setup

```bash
# Test frame processing
python process_frame.py path/to/test/image.jpg
```

## Running the System

The Python modules are integrated with the Node.js RTMP server. You need to run both the server and stream video to it.

### Quick Start

**Terminal 1** - Start the RTMP server:
```bash
node src/server_minimal.js
```

**Terminal 2** - Stream video from your source (see options below)

### Video Source Options

#### 1. Webcam Stream (macOS)

Stream from your built-in webcam:

```bash
ffmpeg -f avfoundation -framerate 30 -video_size 1280x720 -i "0" \
  -f flv -vcodec libx264 -preset ultrafast -tune zerolatency \
  rtmp://localhost:1935/live/webcam
```

**Parameters**:
- `-i "0"`: First camera device (use `-list_devices true -f avfoundation -i ""` to list all devices)
- `-framerate 30`: Capture at 30 FPS
- `-video_size 1280x720`: 720p resolution
- Stream key: `webcam`

#### 2. Webcam Stream (Linux)

```bash
ffmpeg -f v4l2 -framerate 30 -video_size 1280x720 -i /dev/video0 \
  -f flv -vcodec libx264 -preset ultrafast -tune zerolatency \
  rtmp://localhost:1935/live/webcam
```

#### 3. Webcam Stream (Windows)

```bash
ffmpeg -f dshow -framerate 30 -video_size 1280x720 -i video="Integrated Camera" \
  -f flv -vcodec libx264 -preset ultrafast -tune zerolatency \
  rtmp://localhost:1935/live/webcam
```

#### 4. Drone Stream (DJI/Generic RTSP)

Stream from a drone that supports RTSP output:

```bash
ffmpeg -i rtsp://drone_ip:rtsp_port/stream \
  -f flv -vcodec libx264 -preset ultrafast -tune zerolatency \
  rtmp://localhost:1935/live/drone
```

**Common drone RTSP URLs**:
- DJI Drones: `rtsp://192.168.1.1:8554/live`
- Generic IP cameras: `rtsp://admin:password@camera_ip:554/stream1`

Stream key: `drone`

#### 5. IP Security Camera

Stream from an IP camera with RTSP support:

```bash
ffmpeg -i rtsp://username:password@camera_ip:554/stream \
  -f flv -vcodec libx264 -preset ultrafast -tune zerolatency \
  rtmp://localhost:1935/live/camera1
```

Stream key: `camera1`

#### 6. Video File (Testing)

Stream a pre-recorded video file for testing:

```bash
ffmpeg -re -i /path/to/video.mp4 \
  -f flv -vcodec libx264 -preset ultrafast \
  rtmp://localhost:1935/live/test
```

**Parameters**:
- `-re`: Read input at native frame rate (simulates real-time)
- Stream key: `test`

#### 7. OBS Studio

Use OBS Studio for advanced streaming:

1. Open OBS Studio
2. Configure your scene (webcam, screen capture, etc.)
3. Settings → Stream:
   - Service: Custom
   - Server: `rtmp://localhost:1935/live`
   - Stream Key: `obs` (or any key you choose)
4. Click "Start Streaming"

#### 8. Multiple Camera Setup

Run multiple camera streams simultaneously:

**Terminal 2** - Camera 1:
```bash
ffmpeg -f avfoundation -i "0" \
  -f flv -vcodec libx264 -preset ultrafast -tune zerolatency \
  rtmp://localhost:1935/live/camera1
```

**Terminal 3** - Camera 2:
```bash
ffmpeg -f avfoundation -i "1" \
  -f flv -vcodec libx264 -preset ultrafast -tune zerolatency \
  rtmp://localhost:1935/live/camera2
```

### Stream Keys

The stream key (last part of RTMP URL) identifies different video sources:
- `webcam` - Built-in webcam
- `drone` - Aerial drone footage
- `camera1`, `camera2` - Multiple security cameras
- `test` - Testing/demo footage
- `obs` - OBS Studio stream

### Viewing the Stream

While streaming, you can view the feed:

1. **VLC Media Player**:
   - Open Network Stream: `rtmp://localhost:1935/live/webcam`

2. **ffplay** (comes with ffmpeg):
   ```bash
   ffplay rtmp://localhost:1935/live/webcam
   ```

3. **Web Browser** (if HTML viewer is configured):
   - Open `http://localhost:8000` in your browser

### Frame Capture Settings

Configure frame capture rate in your Node.js server configuration:

```javascript
// Capture a frame every N seconds
const FRAME_CAPTURE_INTERVAL = 5; // seconds

// Or capture every N frames
const FRAME_CAPTURE_RATE = 150; // frames (5 seconds at 30fps)
```

### Production Deployment

For production use with continuous monitoring:

```bash
# Start server in background with PM2
npm install -g pm2
pm2 start src/server_minimal.js --name "security-monitor"

# Stream from IP camera (runs continuously)
ffmpeg -i rtsp://camera_ip:554/stream \
  -f flv -vcodec libx264 -preset ultrafast -tune zerolatency \
  -reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 \
  rtmp://localhost:1935/live/security_cam
```

**Reconnection flags** ensure ffmpeg reconnects if the stream drops.

### Troubleshooting Streams

**Issue**: `Connection refused`
- **Solution**: Ensure the RTMP server is running first

**Issue**: `Device not found` (webcam)
- **Solution**: List available devices:
  ```bash
  # macOS
  ffmpeg -f avfoundation -list_devices true -i ""

  # Linux
  ls /dev/video*

  # Windows
  ffmpeg -list_devices true -f dshow -i dummy
  ```

**Issue**: High latency/lag
- **Solution**: Use `-tune zerolatency` and `-preset ultrafast` flags

**Issue**: Stream keeps dropping
- **Solution**: Add reconnection flags (see Production Deployment above)

**Issue**: Poor video quality
- **Solution**: Increase bitrate:
  ```bash
  ffmpeg -i input -b:v 2M -maxrate 2M -bufsize 4M -f flv rtmp://...
  ```

## Integration with Node.js

The Python modules are called from Node.js via child process:

```javascript
const { spawn } = require('child_process');

const python = spawn('python', ['process_frame.py', imagePath]);

python.stdout.on('data', (data) => {
  const output = data.toString();
  if (output.includes('PYTHON_RESULT:')) {
    const result = JSON.parse(output.split('PYTHON_RESULT:')[1]);
    console.log('Processing result:', result);
  }
});
```

## Performance Optimizations

The modules implement several optimizations to reduce costs and improve performance:

1. **Motion Detection**: Skips ~40-60% of frames with no motion
2. **Deduplication**: Eliminates ~20-30% of duplicate frames
3. **Image Optimization**: Reduces API bandwidth by ~70-80%
4. **Alert Debouncing**: Prevents notification spam
5. **Persistent State**: Maintains context across frames

**Total API Cost Reduction**: ~70-85% compared to processing every frame

## Error Handling

All modules implement robust error handling:

- **Configuration Errors**: Validated on startup with clear error messages
- **API Errors**: Retry logic with exponential backoff
- **File Errors**: Graceful handling of missing or corrupt files
- **Network Errors**: Timeout handling and retry mechanisms

## Development

### Adding New Modules

1. Create a new Python file in `python_modules/`
2. Import required dependencies
3. Use `Config` class for configuration
4. Implement error handling
5. Add module to the processing pipeline in `process_frame.py`
6. Update this README with module documentation

### Testing Individual Modules

```python
# Test motion detector
from python_modules.motion_detector import MotionDetector
detector = MotionDetector()
has_motion, percent = detector.detect_motion('test.jpg')
print(f"Motion: {has_motion}, Change: {percent}%")

# Test classifier
from python_modules.classifier import ImageClassifier
classifier = ImageClassifier()
result = classifier.classify_image('test.jpg')
print(f"Classification: {result}")

# Test threat detector
from python_modules.threat_detector import ThreatDetector
detector = ThreatDetector()
analysis = detector.analyze_threat(classification, 'frame.jpg')
print(f"Threat: {analysis}")
```

## Dependencies

See [requirements.txt](requirements.txt) for the complete list:

- **requests**: HTTP client for API calls
- **pillow**: Image processing and optimization
- **opencv-python**: Computer vision for motion detection
- **python-telegram-bot**: Telegram Bot API integration
- **python-dotenv**: Environment variable management

## Troubleshooting

### Common Issues

**Issue**: `NVIDIA_API_KEY is required`
- **Solution**: Set `NVIDIA_API_KEY` in `.env` file

**Issue**: Motion detection too sensitive/insensitive
- **Solution**: Adjust `threshold` and `min_change_percent` in `MotionDetector` initialization

**Issue**: Too many duplicate frames detected
- **Solution**: Lower `similarity_threshold` in `FrameDeduplicator` (e.g., from 0.95 to 0.90)

**Issue**: Images too large for API
- **Solution**: Reduce `max_size_kb` or `quality` in `ImageOptimizer`

**Issue**: No Telegram alerts received
- **Solution**: Check `TELEGRAM_ENABLED`, `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_CHAT_ID` in `.env`

**Issue**: Too many alerts
- **Solution**: Increase `ALERT_COOLDOWN_SECONDS` or raise `THREAT_THRESHOLD`

## Security Considerations

- API keys are loaded from environment variables (never hardcoded)
- Sensitive data is not logged to console
- Image files are cleaned up after processing
- Telegram bot token should be kept secret
- Use HTTPS for all API communications

## Contributing

When contributing new modules:

1. Follow the existing code structure
2. Add comprehensive docstrings
3. Implement error handling
4. Add configuration options to `config.py`
5. Update this README with documentation
6. Test thoroughly with various scenarios
7. Ensure compatibility with the existing pipeline

## License

See the main project README for license information.
