# Multi-Connection Camera Stream Load Testing

## Overview

Enhanced load testing framework that supports multiple connections per camera to provide realistic capacity estimations for large-scale camera deployments, specifically designed for 100+ camera face recognition systems.

## Key Features

### 🎯 **Multi-Connection Testing**
- Test N connections per unique camera for realistic production simulation
- Separate tracking of connections vs unique cameras
- Accurate resource usage measurement for capacity planning

### 📊 **Enhanced Analytics**
- Connection-level performance metrics (FPS, frames, bytes, reconnections)
- Camera group analysis showing all connections per camera
- Success rates and stability assessments

### 🚀 **Capacity Estimation Engine**
- Estimates maximum server connections based on current performance
- Calculates unique camera capacity for different viewer scenarios
- Provides confidence levels and utilization metrics

### 🤖 **FR Deployment Recommendations**
- Conservative/Standard/Aggressive deployment scenarios
- Specific recommendations for 100+ camera target
- Risk assessment and feasibility analysis
- Phased implementation strategy with monitoring requirements

## Usage

### Basic Usage
```bash
# Test 24 cameras × 2 connections = 48 total connections
python multi_connection_load_test.py 24 --connections-per-camera 2

# Test 30 cameras × 3 connections = 90 total connections  
python multi_connection_load_test.py 30 --connections-per-camera 3

# Test 25 cameras × 4 connections = 100 total connections
python multi_connection_load_test.py 25 --connections-per-camera 4

# Custom duration
python multi_connection_load_test.py 24 --connections-per-camera 2 --duration 180
```

### Real-World Scenarios

| Scenario | Command | Purpose |
|----------|---------|---------|
| **Production Simulation** | `python multi_connection_load_test.py 50 --connections-per-camera 2` | Simulate 50 cameras with 2 viewers each |
| **Heavy Load Testing** | `python multi_connection_load_test.py 25 --connections-per-camera 4` | Test 25 cameras with 4 concurrent viewers |
| **Capacity Discovery** | `python multi_connection_load_test.py 20 --connections-per-camera 5` | Find maximum load with high viewer count |

## Capacity Estimation Logic

### Connection vs Camera Relationship
- **Current Test**: 24 cameras × 2 connections = 48 total server load
- **Capacity Estimation**: If 48 connections are stable, estimate ~240 unique cameras (single viewer scenario)

### Deployment Scenarios
1. **Single Viewer**: Each camera has 1 connection → Full estimated capacity
2. **Dual Viewer**: Each camera has 2 connections → 50% of estimated capacity  
3. **Multi Viewer**: Each camera has 4 connections → 25% of estimated capacity

## Output Example

```
🎯 MULTI-CONNECTION CAMERA STREAM LOAD TEST RESULTS
================================================================================

📊 Test Configuration:
   Target cameras: 24
   Connections per camera: 2
   Total connections: 48
   Test duration: 120.2s

📈 Connection Performance:
   Successful connections: 47/48
   Success rate: 97.9%
   Average FPS per connection: 24.3
   Global FPS: 1142.4
   Total data processed: 2.1 GB
   Reconnection rate: 0.043

📺 Camera Performance:
   Cameras tested: 24
   Average success rate per camera: 97.9%
   Average combined FPS per camera: 48.6

🎯 Capacity Estimation:
   Estimated max connections: 240
   Current utilization: 19.6%
   Confidence level: high

📋 Unique Camera Capacity Scenarios:
   Each camera has 1 viewer: ~240 cameras
   Each camera has 2 viewers (security + recording): ~120 cameras
   Each camera has 4 viewers (multiple operators): ~60 cameras

🤖 Face Recognition Deployment Recommendations:
   Recommended scenario: Standard Deployment
   Deployment confidence: high
   Recommended unique cameras: 168
   Description: Standard deployment with 30% buffer for FR processing
   100+ camera deployment feasible: ✅ Yes

📋 Analysis:
   ✅ EXCELLENT: 24 cameras × 2 connections = 48 total connections running stably
   Performance grade: EXCELLENT

💡 Recommendations:
   - Server can handle 240 total connections
   - Estimated capacity: ~240 unique cameras
   - Monitor connection success rates and reconnection patterns in production
```

## Files Generated

### Reports Directory (`reports/`)
- **Main JSON Report**: `multi_connection_test_24x2_YYYYMMDD_HHMMSS.json`
- **Per-Connection CSV**: `multi_connection_test_24x2_YYYYMMDD_HHMMSS_connections.csv`
- **Per-Camera CSV**: `multi_connection_test_24x2_YYYYMMDD_HHMMSS_cameras.csv`

### Logs Directory (`logs/`)
- **Test Log**: `multi_connection_test_24x2_YYYYMMDD_HHMMSS.log`

## FR Deployment Strategy

### For 100+ Camera Target

1. **Phase 1**: Deploy 50 cameras (conservative start)
2. **Phase 2**: Scale to 80-100 cameras based on performance
3. **Phase 3**: Monitor and optimize before further scaling

### Monitoring Requirements
- CPU usage during FR processing
- Memory consumption per camera stream  
- Network bandwidth utilization
- FR processing latency per frame

### Risk Assessment
- **100+ Camera Feasibility**: Automatically assessed based on test results
- **Scaling Bottlenecks**: Identified and flagged in recommendations
- **Resource Optimization**: Specific suggestions for infrastructure improvements

## Technical Implementation

### Connection Tracking
```python
# Each connection gets unique tracking
connection_id = f"camera_{camera_id}_conn_{connection_number}"
```

### Statistics Separation
- **Connection Level**: Individual performance per stream
- **Camera Level**: Aggregated performance per unique camera
- **System Level**: Overall capacity and resource utilization

### Capacity Calculation
```python
# Conservative estimation with safety buffer
estimated_max_connections = successful_connections / utilization_rate
unique_camera_capacity = estimated_max_connections / connections_per_camera
```

## Benefits

### 1. **Realistic Load Simulation**
- Multiple connections per camera simulate real production scenarios
- Accounts for multiple viewers, recording systems, and monitoring displays

### 2. **Accurate Capacity Planning** 
- Know exactly how many unique FR cameras can be deployed
- Understand relationship between connections and camera count
- Plan infrastructure sizing with confidence

### 3. **Production Confidence**
- Test with realistic multi-viewer patterns before deployment
- Risk assessment for different deployment scenarios
- Phased rollout recommendations with monitoring guidelines

### 4. **Data-Driven Decisions**
- Comprehensive analytics for technical and business stakeholders
- Executive summaries with deployment feasibility assessments
- Detailed technical metrics for optimization

## Integration with Existing Tools

### Compatible with Current Framework
- Uses same `camera_stream_load_test.py` base functionality
- Maintains compatibility with existing reporting systems
- Extends analytics without breaking existing workflows

### Enhanced Features
- All logging and monitoring improvements from previous agents
- Structured JSON logging with correlation IDs
- Real-time performance tracking and alerting
- Integration capabilities with monitoring systems

This tool provides the most accurate capacity estimation for large-scale camera deployments, specifically optimized for face recognition processing workloads.