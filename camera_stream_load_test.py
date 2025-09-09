#!/usr/bin/env python3
"""
Camera Stream Load Testing Tool
================================

Tests concurrent streaming capabilities from camera API endpoints.
- Fetches cameras with status = 1 from API
- Opens concurrent fr_url streams (multipart/x-mixed-replace; boundary=frame)
- Monitors performance and connection health
- Implements automatic reconnection on failures
- Generates detailed load testing report

Usage:
    python camera_stream_load_test.py --max-streams 50 --duration 300
"""

import asyncio
import aiohttp
import time
import json
import logging
import argparse
import signal
import sys
import ssl
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import threading
from dataclasses import dataclass, asdict
from collections import defaultdict
import psutil
import statistics
import random
import os

@dataclass
class StreamStats:
    camera_id: int
    fr_url: str
    start_time: float
    end_time: Optional[float] = None
    total_frames: int = 0
    total_bytes: int = 0
    reconnections: int = 0
    errors: List[str] = None
    last_frame_time: float = 0
    avg_fps: float = 0
    status: str = "starting"  # starting, connected, error, disconnected
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class CameraStreamLoadTester:
    def __init__(self, api_url: str = "https://cc.nttagid.com/api/v1/camera/", 
                 max_concurrent: int = 50, test_duration: int = 300,
                 shuffle_cameras: bool = True):
        self.api_url = api_url
        self.max_concurrent = max_concurrent
        self.test_duration = test_duration
        self.shuffle_cameras = shuffle_cameras
        
        # Test state
        self.active_streams: Dict[int, StreamStats] = {}
        self.stream_tasks: Dict[int, asyncio.Task] = {}
        self.start_time = 0
        self.should_stop = False
        
        # Statistics
        self.system_stats = []
        self.global_stats = {
            'total_streams_attempted': 0,
            'max_concurrent_achieved': 0,
            'total_reconnections': 0,
            'total_frames_received': 0,
            'total_bytes_received': 0,
            'total_errors': 0
        }
        
        # Setup logging with unique logger name (saved under logs/)
        os.makedirs('logs', exist_ok=True)
        self.log_filename = os.path.join('logs', f'camera_load_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        
        # Create logger
        self.logger = logging.getLogger(f"CameraLoadTester_{id(self)}")
        self.logger.setLevel(logging.INFO)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # File handler
        try:
            file_handler = logging.FileHandler(self.log_filename)
            file_handler.setLevel(logging.INFO)
            file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)
            self.logger.info(f"Logging to file: {self.log_filename}")
        except Exception as e:
            print(f"Warning: Could not create log file {self.log_filename}: {e}")
        
        # Prevent propagation to root logger
        self.logger.propagate = False
        
        # Handle graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle graceful shutdown on SIGINT/SIGTERM"""
        self.logger.info("Received shutdown signal, stopping test...")
        self.should_stop = True
    
    async def get_active_cameras(self) -> List[Dict]:
        """Fetch cameras with status = 1 from the API"""
        self.logger.info(f"Fetching cameras from {self.api_url}")
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        ) as session:
            try:
                async with session.get(self.api_url) as response:
                    if response.status != 200:
                        raise Exception(f"API returned status {response.status}")
                    
                    cameras = await response.json()
                    active_cameras = [cam for cam in cameras if cam.get('status') == 1 and cam.get('fr_url')]
                    
                    self.logger.info(f"Found {len(active_cameras)} active cameras out of {len(cameras)} total")
                    return active_cameras
                    
            except Exception as e:
                self.logger.error(f"Failed to fetch cameras: {e}")
                raise
    
    async def stream_camera(self, camera: Dict, session: aiohttp.ClientSession) -> None:
        """Stream from a single camera with reconnection logic"""
        camera_id = camera['id']
        fr_url = camera['fr_url']
        
        stats = StreamStats(camera_id=camera_id, fr_url=fr_url, start_time=time.time())
        self.active_streams[camera_id] = stats
        
        reconnect_delay = 1.0
        max_reconnect_delay = 30.0
        
        while not self.should_stop:
            try:
                stats.status = "connecting"
                self.logger.info(f"Camera {camera_id}: Connecting to {fr_url}")
                
                async with session.get(
                    fr_url,
                    headers={'Accept': 'multipart/x-mixed-replace; boundary=frame'},
                    timeout=aiohttp.ClientTimeout(total=None, sock_read=10)
                ) as response:
                    
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}: {response.reason}")
                    
                    content_type = response.headers.get('content-type', '')
                    if 'multipart/x-mixed-replace' not in content_type:
                        self.logger.warning(f"Camera {camera_id}: Unexpected content-type: {content_type}")
                    
                    stats.status = "connected"
                    stats.last_frame_time = time.time()
                    reconnect_delay = 1.0  # Reset delay on successful connection
                    
                    # Read multipart stream
                    buffer = b''
                    frame_start_marker = b'--frame'
                    
                    async for chunk in response.content.iter_chunked(8192):
                        if self.should_stop:
                            break
                            
                        buffer += chunk
                        stats.total_bytes += len(chunk)
                        
                        # Look for frame boundaries
                        while frame_start_marker in buffer:
                            frame_pos = buffer.find(frame_start_marker)
                            if frame_pos > 0:
                                # Found a complete frame
                                stats.total_frames += 1
                                current_time = time.time()
                                
                                # Calculate FPS
                                if stats.total_frames > 1:
                                    elapsed = current_time - stats.start_time
                                    stats.avg_fps = stats.total_frames / elapsed
                                
                                stats.last_frame_time = current_time
                            
                            # Move past the frame marker
                            next_pos = frame_pos + len(frame_start_marker)
                            buffer = buffer[next_pos:]
                        
                        # Keep buffer manageable
                        if len(buffer) > 1024 * 1024:  # 1MB limit
                            buffer = buffer[-512*1024:]  # Keep last 512KB
                    
                    # If we reach here, stream ended normally
                    break
                    
            except asyncio.CancelledError:
                self.logger.info(f"Camera {camera_id}: Stream cancelled")
                break
                
            except (aiohttp.ClientConnectionError, aiohttp.ClientSSLError, 
                    aiohttp.ServerDisconnectedError) as e:
                # Handle connection-specific errors more gracefully
                error_msg = f"Connection error: {str(e)}"
                stats.errors.append(error_msg)
                stats.status = "error"
                self.global_stats['total_errors'] += 1
                
                self.logger.warning(f"Camera {camera_id}: {error_msg}")
                
                if not self.should_stop:
                    # Implement exponential backoff for reconnection
                    stats.reconnections += 1
                    self.global_stats['total_reconnections'] += 1
                    
                    self.logger.info(f"Camera {camera_id}: Reconnecting in {reconnect_delay}s (attempt #{stats.reconnections})")
                    
                    # Wait for reconnection delay but check for cancellation
                    try:
                        await asyncio.sleep(reconnect_delay)
                    except asyncio.CancelledError:
                        self.logger.info(f"Camera {camera_id}: Reconnection cancelled")
                        break
                    
                    reconnect_delay = min(reconnect_delay * 1.5, max_reconnect_delay)
                else:
                    break
                    
            except Exception as e:
                error_msg = f"Stream error: {str(e)}"
                stats.errors.append(error_msg)
                stats.status = "error"
                self.global_stats['total_errors'] += 1
                
                self.logger.warning(f"Camera {camera_id}: {error_msg}")
                
                if not self.should_stop:
                    # Implement exponential backoff for reconnection
                    stats.reconnections += 1
                    self.global_stats['total_reconnections'] += 1
                    
                    self.logger.info(f"Camera {camera_id}: Reconnecting in {reconnect_delay}s (attempt #{stats.reconnections})")
                    
                    # Wait for reconnection delay but check for cancellation
                    try:
                        await asyncio.sleep(reconnect_delay)
                    except asyncio.CancelledError:
                        self.logger.info(f"Camera {camera_id}: Reconnection cancelled")
                        break
                    
                    reconnect_delay = min(reconnect_delay * 1.5, max_reconnect_delay)
                else:
                    break
        
        # Clean up
        stats.status = "disconnected"
        stats.end_time = time.time()
        self.logger.info(f"Camera {camera_id}: Stream ended. Frames: {stats.total_frames}, Reconnections: {stats.reconnections}")
    
    async def monitor_system_resources(self):
        """Monitor system resources during the test"""
        while not self.should_stop:
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                network = psutil.net_io_counters()
                
                # Count active connections
                active_count = len([s for s in self.active_streams.values() if s.status == "connected"])
                
                system_stat = {
                    'timestamp': time.time(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_used_gb': memory.used / (1024**3),
                    'network_bytes_sent': network.bytes_sent,
                    'network_bytes_recv': network.bytes_recv,
                    'active_streams': active_count,
                    'total_frames': sum(s.total_frames for s in self.active_streams.values()),
                    'total_bytes': sum(s.total_bytes for s in self.active_streams.values())
                }
                
                self.system_stats.append(system_stat)
                self.global_stats['max_concurrent_achieved'] = max(
                    self.global_stats['max_concurrent_achieved'], 
                    active_count
                )
                
                # Log progress every 30 seconds
                if len(self.system_stats) % 30 == 0:
                    elapsed = time.time() - self.start_time
                    total_frames = sum(s.total_frames for s in self.active_streams.values())
                    avg_fps = total_frames / elapsed if elapsed > 0 else 0
                    
                    self.logger.info(
                        f"Progress: {elapsed:.0f}s | Active: {active_count}/{self.max_concurrent} | "
                        f"CPU: {cpu_percent:.1f}% | RAM: {memory.percent:.1f}% | "
                        f"Total Frames: {total_frames} | Avg FPS: {avg_fps:.1f}"
                    )
                
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error monitoring system: {e}")
                await asyncio.sleep(5)
    
    def _exception_handler(self, loop, context):
        """Handle unhandled asyncio exceptions to prevent spam logs"""
        exception = context.get('exception')
        if isinstance(exception, (aiohttp.ClientConnectionError, aiohttp.ClientSSLError)):
            # Silently ignore SSL/connection errors that are already handled
            return
        # Log other exceptions normally
        self.logger.warning(f"Unhandled asyncio exception: {context}")

    async def run_load_test(self) -> Dict:
        """Run the main load test"""
        # Set exception handler for current event loop
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(self._exception_handler)
        
        self.logger.info("=== Camera Stream Load Test Started ===")
        self.logger.info(f"Max concurrent streams: {self.max_concurrent}")
        self.logger.info(f"Test duration: {self.test_duration} seconds")
        
        # Get active cameras
        try:
            cameras = await self.get_active_cameras()
        except Exception as e:
            self.logger.error(f"Failed to get cameras: {e}")
            return {"error": str(e)}
        
        if not cameras:
            self.logger.error("No active cameras found")
            return {"error": "No active cameras found"}
        
        # Optionally shuffle before selecting test set
        if self.shuffle_cameras:
            try:
                random.shuffle(cameras)
                self.logger.info("Camera list shuffled before selection")
            except Exception as e:
                self.logger.warning(f"Could not shuffle cameras: {e}")

        # Limit cameras to max concurrent (after shuffle if enabled)
        test_cameras = cameras[:self.max_concurrent]
        self.logger.info(f"Testing with {len(test_cameras)} cameras")
        
        self.start_time = time.time()
        self.global_stats['total_streams_attempted'] = len(test_cameras)
        
        # Create SSL context that handles connection errors gracefully
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create session for all requests
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent + 10,
            limit_per_host=50,
            enable_cleanup_closed=True,
            ssl=ssl_context,
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
            force_close=True  # Force close connections to prevent SSL issues
        )
        
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=None)
        )
        
        try:
            # Start system monitoring
            monitor_task = asyncio.create_task(self.monitor_system_resources())
            
            # Start streaming tasks
            for camera in test_cameras:
                camera_id = camera['id']
                task = asyncio.create_task(self.stream_camera(camera, session))
                self.stream_tasks[camera_id] = task
            
            self.logger.info(f"Started {len(self.stream_tasks)} streaming tasks")
            
            # Wait for test duration or interruption
            end_time = self.start_time + self.test_duration
            while time.time() < end_time and not self.should_stop:
                await asyncio.sleep(1)
            
            self.logger.info("Test duration completed or interrupted, stopping streams...")
            self.should_stop = True
            
            # Cancel all tasks gracefully
            self.logger.info("Cancelling tasks...")
            monitor_task.cancel()
            for task in self.stream_tasks.values():
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete with proper exception handling
            all_tasks = list(self.stream_tasks.values()) + [monitor_task]
            if all_tasks:
                results = await asyncio.gather(*all_tasks, return_exceptions=True)
                # Log any unexpected exceptions (not CancelledError)
                for i, result in enumerate(results):
                    if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                        self.logger.warning(f"Task {i} finished with exception: {result}")
            
        except Exception as e:
            self.logger.error(f"Error during load test: {e}")
        finally:
            # Close session with proper SSL cleanup
            try:
                if not session.closed:
                    await session.close()
                    # Give some time for SSL cleanup
                    await asyncio.sleep(0.1)
            except Exception as e:
                self.logger.warning(f"Warning during session cleanup: {e}")
        
        # Generate final report
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        """Generate comprehensive test report"""
        end_time = time.time()
        total_duration = end_time - self.start_time
        
        # Aggregate statistics
        total_frames = sum(s.total_frames for s in self.active_streams.values())
        total_bytes = sum(s.total_bytes for s in self.active_streams.values())
        total_reconnections = sum(s.reconnections for s in self.active_streams.values())
        
        # Calculate FPS statistics
        fps_values = [s.avg_fps for s in self.active_streams.values() if s.avg_fps > 0]
        avg_fps = statistics.mean(fps_values) if fps_values else 0
        median_fps = statistics.median(fps_values) if fps_values else 0
        
        # Stream status breakdown
        status_counts = defaultdict(int)
        for stream in self.active_streams.values():
            status_counts[stream.status] += 1
        
        # System resource analysis
        if self.system_stats:
            avg_cpu = statistics.mean([s['cpu_percent'] for s in self.system_stats])
            max_cpu = max([s['cpu_percent'] for s in self.system_stats])
            avg_memory = statistics.mean([s['memory_percent'] for s in self.system_stats])
            max_memory = max([s['memory_percent'] for s in self.system_stats])
            max_concurrent = max([s['active_streams'] for s in self.system_stats])
        else:
            avg_cpu = max_cpu = avg_memory = max_memory = max_concurrent = 0
        
        report = {
            "test_info": {
                "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                "end_time": datetime.fromtimestamp(end_time).isoformat(),
                "duration_seconds": round(total_duration, 2),
                "max_concurrent_target": self.max_concurrent,
                "max_concurrent_achieved": max_concurrent
            },
            "stream_performance": {
                "total_streams_attempted": len(self.active_streams),
                "total_frames_received": total_frames,
                "total_bytes_received": total_bytes,
                "total_reconnections": total_reconnections,
                "average_fps": round(avg_fps, 2),
                "median_fps": round(median_fps, 2),
                "bytes_per_second": round(total_bytes / total_duration, 2) if total_duration > 0 else 0,
                "frames_per_second_global": round(total_frames / total_duration, 2) if total_duration > 0 else 0
            },
            "stream_status": dict(status_counts),
            "system_resources": {
                "average_cpu_percent": round(avg_cpu, 2),
                "peak_cpu_percent": round(max_cpu, 2),
                "average_memory_percent": round(avg_memory, 2),
                "peak_memory_percent": round(max_memory, 2)
            },
            "individual_streams": [
                {
                    "camera_id": stream.camera_id,
                    "fr_url": stream.fr_url,
                    "status": stream.status,
                    "total_frames": stream.total_frames,
                    "total_bytes": stream.total_bytes,
                    "reconnections": stream.reconnections,
                    "avg_fps": round(stream.avg_fps, 2),
                    "duration_seconds": round((stream.end_time or end_time) - stream.start_time, 2),
                    "errors": stream.errors
                }
                for stream in self.active_streams.values()
            ],
            "analysis": self.analyze_results(total_duration, max_concurrent, avg_fps)
        }
        
        return report
    
    def analyze_results(self, duration: float, max_concurrent: int, avg_fps: float) -> Dict:
        """Analyze test results and provide recommendations"""
        analysis = {
            "summary": "",
            "recommendations": [],
            "capacity_assessment": "",
            "issues_found": []
        }
        
        # Performance summary
        success_rate = max_concurrent / self.max_concurrent if self.max_concurrent > 0 else 0
        
        if success_rate >= 0.9:
            analysis["summary"] = f"EXCELLENT: Successfully handled {max_concurrent}/{self.max_concurrent} concurrent streams"
        elif success_rate >= 0.7:
            analysis["summary"] = f"GOOD: Handled {max_concurrent}/{self.max_concurrent} concurrent streams with some limitations"
        elif success_rate >= 0.5:
            analysis["summary"] = f"MODERATE: Only {max_concurrent}/{self.max_concurrent} streams successful"
        else:
            analysis["summary"] = f"POOR: Only {max_concurrent}/{self.max_concurrent} streams successful"
        
        # Capacity assessment
        if avg_fps >= 20:
            analysis["capacity_assessment"] = "High performance - suitable for real-time monitoring"
        elif avg_fps >= 10:
            analysis["capacity_assessment"] = "Moderate performance - acceptable for most use cases"
        elif avg_fps >= 5:
            analysis["capacity_assessment"] = "Low performance - may impact monitoring quality"
        else:
            analysis["capacity_assessment"] = "Very low performance - not suitable for production"
        
        # Issues and recommendations
        total_errors = sum(len(s.errors) for s in self.active_streams.values())
        total_reconnections = sum(s.reconnections for s in self.active_streams.values())
        
        if total_errors > max_concurrent * 0.1:
            analysis["issues_found"].append(f"High error rate: {total_errors} errors across streams")
            analysis["recommendations"].append("Investigate network stability and server capacity")
        
        if total_reconnections > max_concurrent:
            analysis["issues_found"].append(f"Frequent reconnections: {total_reconnections} total")
            analysis["recommendations"].append("Check stream server stability and network conditions")
        
        if max_concurrent < self.max_concurrent * 0.8:
            analysis["issues_found"].append("Could not achieve target concurrent stream count")
            analysis["recommendations"].append("Consider increasing server resources or reducing stream quality")
        
        if not analysis["recommendations"]:
            analysis["recommendations"].append("System performed well within tested parameters")
        
        return analysis

def save_report(report: Dict, filename: str = None) -> str:
    """Save report to JSON file"""
    # Ensure reports directory exists
    os.makedirs('reports', exist_ok=True)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"camera_stream_load_test_report_{timestamp}.json"
    
    # If no directory specified in filename, save under reports/
    if not os.path.dirname(filename):
        filename = os.path.join('reports', filename)
    else:
        # Ensure the directory for the given filename exists
        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
        except Exception:
            pass
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        return filename
    except Exception as e:
        print(f"Failed to save report: {e}")
        return None

def print_summary(report: Dict):
    """Print test summary to console"""
    print("\n" + "="*80)
    print("CAMERA STREAM LOAD TEST RESULTS")
    print("="*80)
    
    test_info = report["test_info"]
    perf = report["stream_performance"]
    resources = report["system_resources"]
    analysis = report["analysis"]
    
    print(f"\n📊 Test Overview:")
    print(f"   Duration: {test_info['duration_seconds']}s")
    print(f"   Target concurrent streams: {test_info['max_concurrent_target']}")
    print(f"   Achieved concurrent streams: {test_info['max_concurrent_achieved']}")
    
    print(f"\n📈 Performance Metrics:")
    print(f"   Total frames received: {perf['total_frames_received']:,}")
    print(f"   Total data received: {perf['total_bytes_received'] / (1024**2):.1f} MB")
    print(f"   Average FPS per stream: {perf['average_fps']}")
    print(f"   Global FPS: {perf['frames_per_second_global']}")
    print(f"   Total reconnections: {perf['total_reconnections']}")
    
    print(f"\n🖥️  System Resources:")
    print(f"   Peak CPU usage: {resources['peak_cpu_percent']}%")
    print(f"   Peak memory usage: {resources['peak_memory_percent']}%")
    
    print(f"\n📋 Analysis:")
    print(f"   {analysis['summary']}")
    print(f"   {analysis['capacity_assessment']}")
    
    if analysis['issues_found']:
        print(f"\n⚠️  Issues Found:")
        for issue in analysis['issues_found']:
            print(f"   - {issue}")
    
    if analysis['recommendations']:
        print(f"\n💡 Recommendations:")
        for rec in analysis['recommendations']:
            print(f"   - {rec}")
    
    print("\n" + "="*80)

async def main():
    parser = argparse.ArgumentParser(description='Camera Stream Load Testing Tool')
    parser.add_argument('--api-url', default='https://cc.nttagid.com/api/v1/camera/', 
                       help='Camera API endpoint URL')
    parser.add_argument('--max-streams', type=int, default=50, 
                       help='Maximum concurrent streams to test')
    parser.add_argument('--duration', type=int, default=300, 
                       help='Test duration in seconds')
    parser.add_argument('--output', '-o', 
                       help='Output filename for report (auto-generated if not specified)')
    parser.add_argument('--no-shuffle', dest='shuffle', action='store_false',
                       help='Disable shuffling cameras before selection')
    parser.set_defaults(shuffle=True)
    
    args = parser.parse_args()
    
    # Create and run load tester
    tester = CameraStreamLoadTester(
        api_url=args.api_url,
        max_concurrent=args.max_streams,
        test_duration=args.duration,
        shuffle_cameras=args.shuffle
    )
    
    try:
        report = await tester.run_load_test()
        
        if "error" in report:
            print(f"Test failed: {report['error']}")
            sys.exit(1)
        
        # Save and display report
        filename = save_report(report, args.output)
        if filename:
            print(f"\n📄 Report saved to: {filename}")
        
        print_summary(report)
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
