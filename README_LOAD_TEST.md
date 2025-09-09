# Camera Stream Load Testing Tool

This tool tests the concurrent streaming capabilities of camera FR (Face Recognition) endpoints from the NTTA GID API.

## Features

✅ **Fetches Active Cameras**: Gets cameras with `status = 1` from API  
✅ **Concurrent Streaming**: Opens multiple `fr_url` streams simultaneously  
✅ **Multipart Stream Parsing**: Handles `multipart/x-mixed-replace; boundary=frame` format  
✅ **Automatic Reconnection**: Reconnects on disconnect with exponential backoff  
✅ **Performance Monitoring**: Tracks FPS, bandwidth, system resources  
✅ **Detailed Reports**: Generates comprehensive JSON reports  
✅ **5-Minute Default**: Runs for 5 minutes as requested  

## Quick Start

### 1. Find Maximum Capacity (Recommended)
```bash
python simple_max_test.py
```
**Simple single loop to find maximum stable concurrent streams:**
- Starts high, decreases until stable
- One test per level, no complex phases
- Quick and direct results
- Done when stable configuration found

### 2. Simple Fixed Test
```bash
python run_load_test.py
```
This will:
- Ask you for the number of concurrent streams to test
- Run for 5 minutes
- Show live progress
- Generate detailed report
- Display summary with key metrics

### 3. Advanced Usage
```bash
python camera_stream_load_test.py --max-streams 50 --duration 300
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

## Key Metrics (As Requested)

The tool provides exactly what you asked for:

1. **Count Open Cameras**: Shows how many FR streams opened successfully
2. **Reconnection Tracking**: Counts reconnection attempts per camera
3. **5-Minute Test**: Default 300-second duration
4. **Summary Report**: Detailed performance analysis

## Example Output

```
🎯 KEY METRICS (as requested):
   ✅ Successfully opened: 45 concurrent FR streams
   🔄 Total reconnections: 12
   ⏱️  Test duration: 300.2s (target: 300s)
   📊 Total frames received: 67,890
   🚀 Average FPS per stream: 4.52

🔄 CAMERAS WITH RECONNECTIONS:
   Camera 544: 2 reconnections
   Camera 548: 1 reconnection
   Camera 552: 3 reconnections
```

## Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--max-streams` | 50 | Maximum concurrent streams |
| `--duration` | 300 | Test duration in seconds |
| `--api-url` | https://cc.nttagid.com/api/v1/camera/ | Camera API endpoint |
| `--output` | auto | Output filename for report |

## Report Contents

The tool generates detailed JSON reports containing:

- **Stream Performance**: FPS, bandwidth, frame counts
- **System Resources**: CPU, memory usage during test
- **Individual Camera Stats**: Per-camera reconnections and errors
- **Analysis**: Performance assessment and recommendations

## Stream Format Support

The tool properly handles the `multipart/x-mixed-replace; boundary=frame` format used by the FR endpoints, parsing frame boundaries and counting frames accurately.

## Error Handling

- Automatic reconnection with exponential backoff
- Graceful handling of network issues
- Per-stream error tracking
- System resource monitoring
- Clean shutdown on Ctrl+C

## Files Created

- `camera_stream_load_test_report_YYYYMMDD_HHMMSS.json` - Detailed report
- `camera_load_test_YYYYMMDD_HHMMSS.log` - Execution log

## System Requirements

- Python 3.7+
- aiohttp for async HTTP requests
- psutil for system monitoring
- Sufficient network bandwidth for concurrent streams