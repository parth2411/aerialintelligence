const NodeMediaServer = require("node-media-server");
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

// ===== OPTIMIZED CONFIGURATION =====
const config = {
  rtmp: { port: 1935, chunk_size: 60000, gop_cache: true, ping: 30, ping_timeout: 60 },
  http: { port: 8000, allow_origin: "*" },
  
  // Performance settings
  captureIntervalMs: 3000,      // 3 seconds (was 10s) - 3x faster response
  initialDelayMs: 2000,         // 2 seconds (was 3s)
  ffmpegQuality: 7,             // Higher quality = bigger file but better accuracy
  maxConcurrentProcessing: 2,   // Process up to 2 frames simultaneously
};

const nms = new NodeMediaServer({ rtmp: config.rtmp, http: config.http });

// Setup directories
const captureDir = path.join(__dirname, "../data/captured_frames");
const classificationDir = path.join(__dirname, "../data/classification_results");

[captureDir, classificationDir].forEach((dir) => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
});

// State management
let activeStreams = new Map();
let frameCount = 0;
let processingQueue = [];
let currentlyProcessing = 0;

// Statistics
const stats = {
  captured: 0,
  processed: 0,
  skipped: 0,
  threats: 0,
  alerts: 0,
  startTime: Date.now()
};

/**
 * Process queue of frames (allows parallel processing)
 */
function processQueue() {
  while (processingQueue.length > 0 && currentlyProcessing < config.maxConcurrentProcessing) {
    const imagePath = processingQueue.shift();
    processWithPython(imagePath);
  }
}

/**
 * Capture frame and add to processing queue
 */
function captureAndProcess(streamPath) {
  frameCount++;
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const filename = `frame-${frameCount}-${timestamp}.jpg`;
  const outputPath = path.join(captureDir, filename);

  const captureStart = Date.now();

  const ffmpeg = spawn("ffmpeg", [
    "-i", `rtmp://localhost:1935${streamPath}`,
    "-vframes", "1",
    "-f", "image2",
    "-q:v", config.ffmpegQuality.toString(),
    "-y", outputPath,
  ]);

  ffmpeg.on("close", (code) => {
    if (code === 0 && fs.existsSync(outputPath) && fs.statSync(outputPath).size > 0) {
      const captureTime = Date.now() - captureStart;
      stats.captured++;
      
      console.log(`✅ [${new Date().toLocaleTimeString()}] Frame captured in ${captureTime}ms: ${filename}`);
      
      // Add to processing queue
      processingQueue.push(outputPath);
      processQueue();
    } else {
      console.log(`❌ Frame capture failed`);
    }
  });

  ffmpeg.stderr.on("data", () => {
    // Suppress FFmpeg output
  });
}

/**
 * Call Python script to process frame
 */
function processWithPython(imagePath) {
  currentlyProcessing++;
  
  const processStart = Date.now();
  const frameNum = stats.captured;
  
  console.log(`\n🐍 [${new Date().toLocaleTimeString()}] Processing frame ${frameNum}...`);
  
  const python = spawn("python3", ["process_frame.py", imagePath], {
    cwd: path.join(__dirname, "..")
  });
  
  let output = "";
  let pythonResult = null;

  python.stdout.on("data", (data) => {
    const text = data.toString();
    output += text;
    
    // Look for Python result JSON
    if (text.includes("PYTHON_RESULT:")) {
      try {
        const jsonStr = text.split("PYTHON_RESULT:")[1].trim();
        pythonResult = JSON.parse(jsonStr);
      } catch (e) {
        console.log("⚠️  Failed to parse Python result");
      }
    }
    
    // Print Python output (but not the raw result JSON)
    if (!text.includes("PYTHON_RESULT:") && !text.includes("====")) {
      process.stdout.write(text);
    }
  });

  python.stderr.on("data", (data) => {
    console.error(`Python error: ${data}`);
  });

  python.on("close", (code) => {
    currentlyProcessing--;
    const processTime = Date.now() - processStart;
    
    if (code === 0 && pythonResult) {
      if (pythonResult.skipped) {
        stats.skipped++;
        console.log(`⏭️  Frame skipped: ${pythonResult.skip_reason}`);
      } else {
        stats.processed++;
        console.log(`✅ Processing complete in ${processTime}ms`);
        
        if (pythonResult.threat_analysis?.threat_detected) {
          stats.threats++;
          console.log(`🚨 THREAT: ${pythonResult.threat_analysis.threat_level}`);
          
          if (pythonResult.alert_sent) {
            stats.alerts++;
            console.log(`📱 Alert sent to Telegram`);
          }
        }
      }
      
      // Show efficiency stats every 10 frames
      if ((stats.captured % 10) === 0) {
        printStats();
      }
    } else {
      console.log(`❌ Processing failed (code: ${code}, time: ${processTime}ms)`);
    }
    
    // Process next in queue
    processQueue();
  });

  python.on("error", (error) => {
    currentlyProcessing--;
    console.log(`❌ Failed to start Python: ${error.message}`);
    processQueue();
  });
}

/**
 * Print efficiency statistics
 */
function printStats() {
  const runtime = (Date.now() - stats.startTime) / 1000 / 60; // minutes
  const totalChecked = stats.captured;
  const apiCallsSaved = stats.skipped;
  const costSaved = apiCallsSaved * 0.005; // Approx $0.005 per API call
  
  console.log(`\n📊 ===== EFFICIENCY STATS =====`);
  console.log(`⏱️  Runtime: ${runtime.toFixed(1)} minutes`);
  console.log(`📸 Captured: ${stats.captured} frames`);
  console.log(`✅ Processed: ${stats.processed} frames`);
  console.log(`⏭️  Skipped: ${stats.skipped} frames (${((stats.skipped/Math.max(1,stats.captured))*100).toFixed(1)}%)`);
  console.log(`🚨 Threats: ${stats.threats}`);
  console.log(`📱 Alerts sent: ${stats.alerts}`);
  if (stats.threats > stats.alerts) {
    console.log(`⏭️  Alerts debounced: ${stats.threats - stats.alerts}`);
  }
  console.log(`💰 Cost saved: $${costSaved.toFixed(2)} (${apiCallsSaved} API calls avoided)`);
  console.log(`============================\n`);
}
/**
 * Start frame capture for a stream
 */
function startFrameCapture(streamPath) {
  if (activeStreams.has(streamPath)) return;

  console.log(`🎥 Starting optimized frame capture for ${streamPath}`);
  console.log(`⚡ Capture interval: ${config.captureIntervalMs}ms`);
  console.log(`🎯 Motion detection: ENABLED`);
  console.log(`🔄 Deduplication: ENABLED`);
  console.log(`📦 Image optimization: ENABLED\n`);

  // Reset stats for new stream
  stats.startTime = Date.now();
  stats.captured = 0;
  stats.processed = 0;
  stats.skipped = 0;
  stats.threats = 0;
  stats.alerts = 0;

  // Capture first frame after delay
  setTimeout(() => captureAndProcess(streamPath), config.initialDelayMs);

  // Then capture at intervals
  const interval = setInterval(() => captureAndProcess(streamPath), config.captureIntervalMs);

  activeStreams.set(streamPath, interval);
}

/**
 * Stop frame capture for a stream
 */
function stopFrameCapture(streamPath) {
  const interval = activeStreams.get(streamPath);
  if (interval) {
    clearInterval(interval);
    activeStreams.delete(streamPath);
    console.log(`⏹️  Stopped frame capture for ${streamPath}`);
    printStats();
  }
}

// Event listeners
nms.on("postPublish", (id, streamPath, args) => {
  console.log(`[postPublish] Stream started: ${streamPath}`);
  startFrameCapture(streamPath);
});

nms.on("donePublish", (id, streamPath, args) => {
  console.log(`[donePublish] Stream ended: ${streamPath}`);
  stopFrameCapture(streamPath);
});

// Start server
nms.run();

console.log("🚀 OPTIMIZED Hybrid RTMP Server Started!");
console.log(`📡 RTMP Port: 1935`);
console.log(`🌐 HTTP Port: 8000`);
console.log(`⚡ Capture interval: ${config.captureIntervalMs}ms (${1000/config.captureIntervalMs} fps)`);
console.log(`🐍 Python processing: ENABLED`);
console.log(`🎯 Smart filtering: ENABLED (motion + deduplication)`);
console.log(`📦 Image optimization: ENABLED`);
console.log(`🔄 Parallel processing: ${config.maxConcurrentProcessing} concurrent`);
console.log(`📁 Frames: ${captureDir}`);
console.log(`📁 Results: ${classificationDir}\n`);
console.log("Stream to: rtmp://localhost:1935/live/webcam");
console.log("Press Ctrl+C to stop\n");

// Graceful shutdown
process.on("SIGINT", () => {
  console.log("\n🛑 Shutting down...");
  for (const [streamPath] of activeStreams) {
    stopFrameCapture(streamPath);
  }
  console.log("👋 Goodbye!");
  process.exit(0);
});