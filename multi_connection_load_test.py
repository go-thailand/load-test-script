#!/usr/bin/env python3
"""
Multi-Connection Camera Stream Load Testing Tool
===============================================

Tests multiple connections per camera to simulate realistic production loads.
- Supports N connections per unique camera for accurate capacity estimation
- Provides scaling recommendations for 100+ camera face recognition deployments
- Comprehensive analytics for production planning

Usage:
    python multi_connection_load_test.py 24 --connections-per-camera 2    # 24 cameras × 2 = 48 connections
    python multi_connection_load_test.py 30 --connections-per-camera 3    # 30 cameras × 3 = 90 connections
    python multi_connection_load_test.py 25 --connections-per-camera 4    # 25 cameras × 4 = 100 connections
"""

import asyncio
import sys
import os
import time
import logging
import csv
import json
import argparse
from typing import Optional, Dict, List
from dataclasses import dataclass

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from camera_stream_load_test import CameraStreamLoadTester, save_report, StreamStats

@dataclass
class ConnectionStats:
    """Individual connection statistics (separate from camera)"""
    connection_id: str
    camera_id: int
    camera_url: str
    connection_number: int
    start_time: float
    end_time: Optional[float] = None
    total_frames: int = 0
    total_bytes: int = 0
    reconnections: int = 0
    errors: List[str] = None
    last_frame_time: float = 0
    avg_fps: float = 0
    status: str = "starting"
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class MultiConnectionLoadTester:
    def __init__(self, camera_count: int, connections_per_camera: int = 1, test_duration: int = 120):
        """
        Args:
            camera_count: Number of unique cameras to test
            connections_per_camera: Number of connections per camera
            test_duration: Duration for the test (seconds)
        """
        self.camera_count = camera_count
        self.connections_per_camera = connections_per_camera
        self.total_connections = camera_count * connections_per_camera
        self.test_duration = test_duration
        
        # Enhanced statistics tracking
        self.connection_stats: Dict[str, ConnectionStats] = {}
        self.camera_groups: Dict[int, List[str]] = {}  # camera_id -> [connection_ids]
        
        # Setup logging
        os.makedirs('logs', exist_ok=True)
        self.log_filename = os.path.join('logs', f'multi_connection_test_{camera_count}x{connections_per_camera}_{time.strftime("%Y%m%d_%H%M%S")}.log')
        
        # Create logger
        self.logger = logging.getLogger(f"MultiConnectionTester_{id(self)}")
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

    async def run_multi_connection_test(self) -> dict:
        """Run multi-connection test and return comprehensive report"""
        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"MULTI-CONNECTION LOAD TEST")
        self.logger.info(f"Testing: {self.camera_count} cameras × {self.connections_per_camera} connections = {self.total_connections} total connections")
        self.logger.info(f"Duration: {self.test_duration}s with shuffled camera selection")
        self.logger.info(f"Target: Capacity estimation for 100+ camera FR deployment")
        self.logger.info(f"{'='*70}")
        
        # Set exception handler for asyncio to suppress SSL-related noise
        loop = asyncio.get_running_loop()
        def exception_handler(loop, context):
            exception = context.get('exception')
            if isinstance(exception, Exception) and 'SSL' in str(exception):
                return
            print(f"Asyncio exception: {context}")
        loop.set_exception_handler(exception_handler)
        
        # Create base tester to get cameras
        base_tester = CameraStreamLoadTester(
            max_concurrent=self.camera_count,
            test_duration=self.test_duration,
            shuffle_cameras=True
        )
        
        try:
            # Get camera list
            cameras = await base_tester.get_active_cameras()
            if len(cameras) < self.camera_count:
                self.logger.error(f"Only {len(cameras)} cameras available, need {self.camera_count}")
                return {"error": f"Insufficient cameras: {len(cameras)} < {self.camera_count}"}
            
            # Select test cameras
            test_cameras = cameras[:self.camera_count]
            self.logger.info(f"Selected {len(test_cameras)} cameras for multi-connection testing")
            
            # Create multiple connections per camera
            connection_tasks = []
            for camera in test_cameras:
                camera_id = camera['id']
                self.camera_groups[camera_id] = []
                
                for conn_num in range(1, self.connections_per_camera + 1):
                    connection_id = f"camera_{camera_id}_conn_{conn_num}"
                    self.camera_groups[camera_id].append(connection_id)
                    
                    # Create connection stats
                    conn_stats = ConnectionStats(
                        connection_id=connection_id,
                        camera_id=camera_id,
                        camera_url=camera['fr_url'],
                        connection_number=conn_num,
                        start_time=time.time()
                    )
                    self.connection_stats[connection_id] = conn_stats
                    
                    # Create connection task
                    task = asyncio.create_task(
                        self.stream_single_connection(camera, conn_stats)
                    )
                    connection_tasks.append(task)
                    
                self.logger.info(f"Camera {camera_id}: Created {self.connections_per_camera} connections")
            
            self.logger.info(f"Started {len(connection_tasks)} total connection tasks")
            
            # Run test
            start_time = time.time()
            
            # Wait for test duration
            await asyncio.sleep(self.test_duration)
            
            # Cancel all tasks
            self.logger.info("Test duration completed, stopping connections...")
            for task in connection_tasks:
                task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            end_time = time.time()
            actual_duration = end_time - start_time
            
            # Generate comprehensive report
            report = self.generate_multi_connection_report(actual_duration)
            
            # Save artifacts
            self.save_test_artifacts(report)
            
            return report
            
        except Exception as e:
            self.logger.error(f"Multi-connection test failed: {e}")
            return {"error": str(e)}

    async def stream_single_connection(self, camera: dict, conn_stats: ConnectionStats):
        """Stream from a single connection with tracking"""
        import aiohttp
        import ssl
        
        # Create SSL context and session for this connection
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(
            limit=10,
            enable_cleanup_closed=True,
            ssl=ssl_context,
            force_close=True
        )
        
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=None)
        )
        
        try:
            reconnect_delay = 1.0
            max_reconnect_delay = 30.0
            
            while True:
                try:
                    conn_stats.status = "connecting"
                    self.logger.debug(f"{conn_stats.connection_id}: Connecting to {conn_stats.camera_url}")
                    
                    async with session.get(
                        conn_stats.camera_url,
                        headers={'Accept': 'multipart/x-mixed-replace; boundary=frame'},
                        timeout=aiohttp.ClientTimeout(total=None, sock_read=60)
                    ) as response:
                        
                        if response.status != 200:
                            raise Exception(f"HTTP {response.status}: {response.reason}")
                        
                        conn_stats.status = "connected"
                        conn_stats.last_frame_time = time.time()
                        reconnect_delay = 1.0  # Reset delay on successful connection
                        
                        # Read multipart stream
                        buffer = b''
                        frame_start_marker = b'--frame'
                        
                        async for chunk in response.content.iter_chunked(8192):
                            buffer += chunk
                            conn_stats.total_bytes += len(chunk)
                            
                            # Look for frame boundaries
                            while frame_start_marker in buffer:
                                frame_pos = buffer.find(frame_start_marker)
                                if frame_pos > 0:
                                    # Found a complete frame
                                    conn_stats.total_frames += 1
                                    current_time = time.time()
                                    
                                    # Calculate FPS
                                    if conn_stats.total_frames > 1:
                                        elapsed = current_time - conn_stats.start_time
                                        conn_stats.avg_fps = conn_stats.total_frames / elapsed
                                    
                                    conn_stats.last_frame_time = current_time
                                
                                # Move past the frame marker
                                next_pos = frame_pos + len(frame_start_marker)
                                buffer = buffer[next_pos:]
                            
                            # Keep buffer manageable
                            if len(buffer) > 1024 * 1024:  # 1MB limit
                                buffer = buffer[-512*1024:]  # Keep last 512KB
                        
                        # If we reach here, stream ended normally
                        break
                        
                except asyncio.CancelledError:
                    self.logger.debug(f"{conn_stats.connection_id}: Connection cancelled")
                    break
                    
                except Exception as e:
                    conn_stats.reconnections += 1
                    conn_stats.errors.append(f"{time.time()}: {str(e)}")
                    conn_stats.status = "error"
                    
                    self.logger.warning(f"{conn_stats.connection_id}: Connection failed (attempt {conn_stats.reconnections}): {e}")
                    
                    # Wait before reconnecting
                    await asyncio.sleep(min(reconnect_delay, max_reconnect_delay))
                    reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                    
        finally:
            conn_stats.end_time = time.time()
            conn_stats.status = "disconnected" if conn_stats.status != "error" else "error"
            await session.close()

    def generate_multi_connection_report(self, actual_duration: float) -> dict:
        """Generate comprehensive multi-connection report"""
        report = {
            "multi_connection_test_info": {
                "target_cameras": self.camera_count,
                "connections_per_camera": self.connections_per_camera,
                "total_connections": self.total_connections,
                "test_duration": self.test_duration,
                "actual_duration": round(actual_duration, 2),
                "camera_selection": "shuffled"
            },
            "connection_statistics": self.analyze_connection_performance(),
            "camera_statistics": self.analyze_camera_performance(),
            "capacity_estimation": self.estimate_capacity(),
            "fr_deployment_recommendations": self.generate_fr_recommendations(),
            "analysis": self.analyze_results(),
            "individual_connections": self.get_individual_connection_data(),
            "camera_groups": self.get_camera_group_data()
        }
        
        return report

    def analyze_connection_performance(self) -> dict:
        """Analyze performance across all connections"""
        total_connections = len(self.connection_stats)
        connected_connections = [c for c in self.connection_stats.values() if c.status == "connected"]
        
        if not connected_connections:
            return {"error": "No successful connections"}
        
        total_frames = sum(c.total_frames for c in connected_connections)
        total_bytes = sum(c.total_bytes for c in connected_connections)
        total_reconnections = sum(c.reconnections for c in self.connection_stats.values())
        
        fps_values = [c.avg_fps for c in connected_connections if c.avg_fps > 0]
        avg_fps = sum(fps_values) / len(fps_values) if fps_values else 0
        
        return {
            "total_connections_attempted": total_connections,
            "successful_connections": len(connected_connections),
            "connection_success_rate": round(len(connected_connections) / total_connections * 100, 1),
            "total_frames_received": total_frames,
            "total_bytes_received": total_bytes,
            "total_data_gb": round(total_bytes / (1024**3), 3),
            "total_reconnections": total_reconnections,
            "average_fps_per_connection": round(avg_fps, 2),
            "global_fps": round(total_frames / self.test_duration, 2) if self.test_duration > 0 else 0,
            "reconnection_rate": round(total_reconnections / len(connected_connections), 3) if connected_connections else 0
        }

    def analyze_camera_performance(self) -> dict:
        """Analyze performance per unique camera"""
        camera_analysis = {}
        
        for camera_id, connection_ids in self.camera_groups.items():
            camera_connections = [self.connection_stats[cid] for cid in connection_ids]
            successful_conns = [c for c in camera_connections if c.status == "connected"]
            
            total_frames = sum(c.total_frames for c in successful_conns)
            total_bytes = sum(c.total_bytes for c in successful_conns)
            total_reconnections = sum(c.reconnections for c in camera_connections)
            
            fps_values = [c.avg_fps for c in successful_conns if c.avg_fps > 0]
            avg_fps = sum(fps_values) / len(fps_values) if fps_values else 0
            
            camera_analysis[camera_id] = {
                "connections_attempted": len(camera_connections),
                "successful_connections": len(successful_conns),
                "success_rate": round(len(successful_conns) / len(camera_connections) * 100, 1),
                "total_frames": total_frames,
                "total_bytes": total_bytes,
                "total_reconnections": total_reconnections,
                "avg_fps_per_connection": round(avg_fps, 2),
                "combined_fps": round(sum(c.avg_fps for c in successful_conns), 2)
            }
        
        return {
            "cameras_tested": len(camera_analysis),
            "per_camera_analysis": camera_analysis,
            "camera_summary": {
                "avg_success_rate": round(sum(c["success_rate"] for c in camera_analysis.values()) / len(camera_analysis), 1) if camera_analysis else 0,
                "avg_fps_per_camera": round(sum(c["combined_fps"] for c in camera_analysis.values()) / len(camera_analysis), 2) if camera_analysis else 0
            }
        }

    def estimate_capacity(self) -> dict:
        """Estimate server capacity for unique cameras"""
        conn_stats = self.analyze_connection_performance()
        
        if "error" in conn_stats:
            return {"error": "Cannot estimate capacity - no successful connections"}
        
        successful_connections = conn_stats["successful_connections"]
        connection_success_rate = conn_stats["connection_success_rate"] / 100
        
        # Estimate maximum connections server can handle
        if connection_success_rate >= 0.95:  # 95%+ success rate
            estimated_max_connections = int(successful_connections / 0.8)  # Use 80% of current capacity
            confidence = "high"
        elif connection_success_rate >= 0.90:  # 90%+ success rate
            estimated_max_connections = int(successful_connections / 0.9)  # Use 90% of current capacity
            confidence = "medium"
        else:
            estimated_max_connections = successful_connections  # Current level is likely near max
            confidence = "low"
        
        # Calculate unique camera capacity for different scenarios
        scenarios = {
            "single_viewer": {
                "connections_per_camera": 1,
                "estimated_unique_cameras": estimated_max_connections,
                "description": "Each camera has 1 viewer"
            },
            "dual_viewer": {
                "connections_per_camera": 2,
                "estimated_unique_cameras": estimated_max_connections // 2,
                "description": "Each camera has 2 viewers (security + recording)"
            },
            "multi_viewer": {
                "connections_per_camera": 4,
                "estimated_unique_cameras": estimated_max_connections // 4,
                "description": "Each camera has 4 viewers (multiple operators)"
            },
            "current_test": {
                "connections_per_camera": self.connections_per_camera,
                "estimated_unique_cameras": self.camera_count,
                "description": f"Current test scenario ({self.connections_per_camera} connections per camera)"
            }
        }
        
        return {
            "estimated_max_connections": estimated_max_connections,
            "confidence_level": confidence,
            "current_utilization": round(successful_connections / estimated_max_connections * 100, 1),
            "capacity_scenarios": scenarios,
            "production_recommendations": {
                "safe_deployment": int(estimated_max_connections * 0.7),  # 70% of estimated max
                "target_utilization": "70-80%",
                "monitoring_thresholds": {
                    "warning": int(estimated_max_connections * 0.8),
                    "critical": int(estimated_max_connections * 0.9)
                }
            }
        }

    def generate_fr_recommendations(self) -> dict:
        """Generate specific recommendations for FR deployment"""
        capacity = self.estimate_capacity()
        
        if "error" in capacity:
            return {"error": "Cannot generate recommendations - insufficient data"}
        
        scenarios = capacity["capacity_scenarios"]
        
        # Focus on realistic FR deployment scenarios
        fr_scenarios = {
            "conservative_deployment": {
                "unique_cameras": scenarios["single_viewer"]["estimated_unique_cameras"] // 2,
                "connections_per_camera": 1,
                "description": "Conservative deployment with 50% buffer for FR processing overhead",
                "fr_processing_load": "low",
                "recommended": True
            },
            "standard_deployment": {
                "unique_cameras": int(scenarios["single_viewer"]["estimated_unique_cameras"] * 0.7),
                "connections_per_camera": 1,
                "description": "Standard deployment with 30% buffer for FR processing",
                "fr_processing_load": "medium",
                "recommended": True
            },
            "aggressive_deployment": {
                "unique_cameras": int(scenarios["single_viewer"]["estimated_unique_cameras"] * 0.9),
                "connections_per_camera": 1,
                "description": "Aggressive deployment with 10% buffer - requires careful monitoring",
                "fr_processing_load": "high",
                "recommended": False
            }
        }
        
        # Determine best recommendation based on current performance
        conn_stats = self.analyze_connection_performance()
        reconnection_rate = conn_stats.get("reconnection_rate", 0)
        
        if reconnection_rate <= 0.1:  # Low reconnection rate
            recommended_scenario = "standard_deployment"
            deployment_confidence = "high"
        elif reconnection_rate <= 0.2:  # Moderate reconnection rate
            recommended_scenario = "conservative_deployment"
            deployment_confidence = "medium"
        else:  # High reconnection rate
            recommended_scenario = "conservative_deployment"
            deployment_confidence = "low"
        
        return {
            "target_deployment": "100+ unique cameras for face recognition",
            "recommended_scenario": recommended_scenario,
            "deployment_confidence": deployment_confidence,
            "fr_deployment_scenarios": fr_scenarios,
            "implementation_strategy": {
                "phase_1": f"Deploy {fr_scenarios[recommended_scenario]['unique_cameras'] // 2} cameras",
                "phase_2": f"Scale to {fr_scenarios[recommended_scenario]['unique_cameras']} cameras",
                "phase_3": "Monitor and optimize before further scaling",
                "monitoring_requirements": [
                    "CPU usage during FR processing",
                    "Memory consumption per camera stream",
                    "Network bandwidth utilization",
                    "FR processing latency per frame"
                ]
            },
            "risk_assessment": {
                "100_camera_feasibility": scenarios["single_viewer"]["estimated_unique_cameras"] >= 100,
                "required_optimization": scenarios["single_viewer"]["estimated_unique_cameras"] < 100,
                "scaling_bottlenecks": [
                    "Network bandwidth" if conn_stats.get("total_data_gb", 0) > 10 else None,
                    "Connection limits" if conn_stats.get("connection_success_rate", 0) < 95 else None,
                    "Processing overhead" if reconnection_rate > 0.15 else None
                ]
            }
        }

    def analyze_results(self) -> dict:
        """Generate comprehensive analysis similar to other test scripts"""
        conn_stats = self.analyze_connection_performance()
        camera_stats = self.analyze_camera_performance()
        capacity = self.estimate_capacity()
        
        if "error" in conn_stats:
            return {"summary": "❌ Test failed - no successful connections", "recommendations": []}
        
        success_rate = conn_stats["connection_success_rate"]
        reconnection_rate = conn_stats["reconnection_rate"]
        avg_fps = conn_stats["average_fps_per_connection"]
        
        # Determine overall performance grade
        if success_rate >= 95 and reconnection_rate <= 0.1 and avg_fps >= 20:
            grade = "EXCELLENT"
            summary = f"✅ EXCELLENT: {self.camera_count} cameras × {self.connections_per_camera} connections = {self.total_connections} total connections running stably"
        elif success_rate >= 90 and reconnection_rate <= 0.2 and avg_fps >= 15:
            grade = "GOOD"
            summary = f"✅ GOOD: {self.camera_count} cameras × {self.connections_per_camera} connections with acceptable performance"
        elif success_rate >= 80 and reconnection_rate <= 0.4:
            grade = "MODERATE"
            summary = f"⚠️ MODERATE: {self.camera_count} cameras × {self.connections_per_camera} connections with some stability issues"
        else:
            grade = "POOR"
            summary = f"❌ POOR: Significant issues with {self.camera_count} cameras × {self.connections_per_camera} connections"
        
        recommendations = [
            f"Server can handle {capacity.get('estimated_max_connections', 'unknown')} total connections",
            f"Estimated capacity: ~{capacity.get('capacity_scenarios', {}).get('single_viewer', {}).get('estimated_unique_cameras', 'unknown')} unique cameras",
            "Monitor connection success rates and reconnection patterns in production"
        ]
        
        if success_rate < 95:
            recommendations.append(f"Investigate connection failures ({100-success_rate:.1f}% failure rate)")
        
        if reconnection_rate > 0.2:
            recommendations.append("High reconnection rate indicates network or server stability issues")
        
        return {
            "summary": summary,
            "performance_grade": grade,
            "key_metrics": {
                "connection_success_rate": f"{success_rate:.1f}%",
                "avg_fps_per_connection": f"{avg_fps:.1f}",
                "reconnection_rate": f"{reconnection_rate:.3f}",
                "total_data_processed": f"{conn_stats.get('total_data_gb', 0):.1f} GB"
            },
            "recommendations": recommendations
        }

    def get_individual_connection_data(self) -> list:
        """Get individual connection data for detailed analysis"""
        connections = []
        for conn_stats in self.connection_stats.values():
            connections.append({
                "connection_id": conn_stats.connection_id,
                "camera_id": conn_stats.camera_id,
                "connection_number": conn_stats.connection_number,
                "status": conn_stats.status,
                "total_frames": conn_stats.total_frames,
                "total_bytes": conn_stats.total_bytes,
                "avg_fps": round(conn_stats.avg_fps, 2),
                "reconnections": conn_stats.reconnections,
                "duration_seconds": round((conn_stats.end_time or time.time()) - conn_stats.start_time, 1),
                "errors_count": len(conn_stats.errors)
            })
        return connections

    def get_camera_group_data(self) -> dict:
        """Get camera group data showing all connections per camera"""
        camera_groups = {}
        for camera_id, connection_ids in self.camera_groups.items():
            connections = []
            for conn_id in connection_ids:
                conn_stats = self.connection_stats[conn_id]
                connections.append({
                    "connection_id": conn_id,
                    "connection_number": conn_stats.connection_number,
                    "status": conn_stats.status,
                    "avg_fps": round(conn_stats.avg_fps, 2),
                    "total_frames": conn_stats.total_frames,
                    "reconnections": conn_stats.reconnections
                })
            
            camera_groups[camera_id] = {
                "connections": connections,
                "total_connections": len(connections),
                "successful_connections": len([c for c in connections if c["status"] == "connected"]),
                "combined_fps": sum(c["avg_fps"] for c in connections),
                "total_frames": sum(c["total_frames"] for c in connections)
            }
        
        return camera_groups

    def save_test_artifacts(self, report: dict):
        """Save all test artifacts for analysis"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        base_stem = f"multi_connection_test_{self.camera_count}x{self.connections_per_camera}_{timestamp}"
        
        # Create reports directory
        reports_dir = 'reports'
        try:
            os.makedirs(reports_dir, exist_ok=True)
        except Exception:
            pass
        
        try:
            # Main JSON report
            main_report_path = os.path.join(reports_dir, f"{base_stem}.json")
            save_report(report, main_report_path)
            self.logger.info(f"   Saved main report: {main_report_path}")
        except Exception as e:
            self.logger.warning(f"Could not save main report: {e}")
        
        try:
            # Per-connection CSV
            conn_csv = os.path.join(reports_dir, f"{base_stem}_connections.csv")
            fields = [
                "connection_id", "camera_id", "connection_number", "status", 
                "total_frames", "total_bytes", "avg_fps", "reconnections", 
                "duration_seconds", "errors_count"
            ]
            with open(conn_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                for conn_data in report.get("individual_connections", []):
                    writer.writerow(conn_data)
            self.logger.info(f"   Saved per-connection CSV: {conn_csv}")
        except Exception as e:
            self.logger.warning(f"Could not save per-connection CSV: {e}")
        
        try:
            # Per-camera summary CSV
            camera_csv = os.path.join(reports_dir, f"{base_stem}_cameras.csv")
            camera_fields = [
                "camera_id", "connections_attempted", "successful_connections", 
                "success_rate", "combined_fps", "total_frames", "total_reconnections"
            ]
            with open(camera_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=camera_fields)
                writer.writeheader()
                
                camera_analysis = report.get("camera_statistics", {}).get("per_camera_analysis", {})
                for camera_id, data in camera_analysis.items():
                    writer.writerow({
                        "camera_id": camera_id,
                        "connections_attempted": data["connections_attempted"],
                        "successful_connections": data["successful_connections"],
                        "success_rate": data["success_rate"],
                        "combined_fps": data["combined_fps"],
                        "total_frames": data["total_frames"],
                        "total_reconnections": data["total_reconnections"]
                    })
            self.logger.info(f"   Saved per-camera CSV: {camera_csv}")
        except Exception as e:
            self.logger.warning(f"Could not save per-camera CSV: {e}")


def print_multi_connection_summary(report: dict):
    """Print comprehensive multi-connection test results summary"""
    print("\n" + "="*80)
    print("🎯 MULTI-CONNECTION CAMERA STREAM LOAD TEST RESULTS")
    print("="*80)
    
    test_info = report.get("multi_connection_test_info", {})
    conn_stats = report.get("connection_statistics", {})
    camera_stats = report.get("camera_statistics", {})
    capacity = report.get("capacity_estimation", {})
    fr_recommendations = report.get("fr_deployment_recommendations", {})
    analysis = report.get("analysis", {})
    
    print(f"\n📊 Test Configuration:")
    print(f"   Target cameras: {test_info.get('target_cameras', 'N/A')}")
    print(f"   Connections per camera: {test_info.get('connections_per_camera', 'N/A')}")
    print(f"   Total connections: {test_info.get('total_connections', 'N/A')}")
    print(f"   Test duration: {test_info.get('actual_duration', 'N/A')}s")
    
    if "error" not in conn_stats:
        print(f"\n📈 Connection Performance:")
        print(f"   Successful connections: {conn_stats.get('successful_connections', 'N/A')}/{conn_stats.get('total_connections_attempted', 'N/A')}")
        print(f"   Success rate: {conn_stats.get('connection_success_rate', 'N/A')}%")
        print(f"   Average FPS per connection: {conn_stats.get('average_fps_per_connection', 'N/A')}")
        print(f"   Global FPS: {conn_stats.get('global_fps', 'N/A')}")
        print(f"   Total data processed: {conn_stats.get('total_data_gb', 'N/A')} GB")
        print(f"   Reconnection rate: {conn_stats.get('reconnection_rate', 'N/A')}")
    
    if "error" not in camera_stats:
        camera_summary = camera_stats.get("camera_summary", {})
        print(f"\n📺 Camera Performance:")
        print(f"   Cameras tested: {camera_stats.get('cameras_tested', 'N/A')}")
        print(f"   Average success rate per camera: {camera_summary.get('avg_success_rate', 'N/A')}%")
        print(f"   Average combined FPS per camera: {camera_summary.get('avg_fps_per_camera', 'N/A')}")
    
    if "error" not in capacity:
        print(f"\n🎯 Capacity Estimation:")
        print(f"   Estimated max connections: {capacity.get('estimated_max_connections', 'N/A')}")
        print(f"   Current utilization: {capacity.get('current_utilization', 'N/A')}%")
        print(f"   Confidence level: {capacity.get('confidence_level', 'N/A')}")
        
        scenarios = capacity.get("capacity_scenarios", {})
        print(f"\n📋 Unique Camera Capacity Scenarios:")
        for scenario_name, scenario_data in scenarios.items():
            if scenario_name != "current_test":
                print(f"   {scenario_data['description']}: ~{scenario_data['estimated_unique_cameras']} cameras")
    
    if "error" not in fr_recommendations:
        print(f"\n🤖 Face Recognition Deployment Recommendations:")
        print(f"   Recommended scenario: {fr_recommendations.get('recommended_scenario', 'N/A').replace('_', ' ').title()}")
        print(f"   Deployment confidence: {fr_recommendations.get('deployment_confidence', 'N/A')}")
        
        fr_scenarios = fr_recommendations.get("fr_deployment_scenarios", {})
        recommended = fr_recommendations.get("recommended_scenario", "")
        if recommended in fr_scenarios:
            rec_data = fr_scenarios[recommended]
            print(f"   Recommended unique cameras: {rec_data.get('unique_cameras', 'N/A')}")
            print(f"   Description: {rec_data.get('description', 'N/A')}")
        
        risk_assessment = fr_recommendations.get("risk_assessment", {})
        feasible = risk_assessment.get("100_camera_feasibility", False)
        print(f"   100+ camera deployment feasible: {'✅ Yes' if feasible else '❌ No - optimization required'}")
    
    print(f"\n📋 Analysis:")
    print(f"   {analysis.get('summary', 'N/A')}")
    print(f"   Performance grade: {analysis.get('performance_grade', 'N/A')}")
    
    if analysis.get('recommendations'):
        print(f"\n💡 Recommendations:")
        for rec in analysis.get('recommendations', []):
            print(f"   - {rec}")
    
    print("\n" + "="*80)


async def main():
    """Main entry point for multi-connection load testing"""
    parser = argparse.ArgumentParser(
        description="Multi-Connection Camera Stream Load Testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python multi_connection_load_test.py 24 --connections-per-camera 2 --duration 120
  python multi_connection_load_test.py 30 --connections-per-camera 3 --duration 300
  python multi_connection_load_test.py 25 --connections-per-camera 4 --duration 180
        """
    )
    
    parser.add_argument('camera_count', type=int, help='Number of unique cameras to test')
    parser.add_argument('--connections-per-camera', type=int, default=1, 
                       help='Number of connections per camera (default: 1)')
    parser.add_argument('--duration', type=int, default=120,
                       help='Test duration in seconds (default: 120)')
    
    args = parser.parse_args()
    
    if args.camera_count <= 0:
        print("Error: Camera count must be > 0")
        return 1
    
    if args.connections_per_camera <= 0:
        print("Error: Connections per camera must be > 0")
        return 1
    
    total_connections = args.camera_count * args.connections_per_camera
    
    print("="*80)
    print("🎯 MULTI-CONNECTION CAMERA STREAM LOAD TEST")
    print(f"Testing: {args.camera_count} cameras × {args.connections_per_camera} connections = {total_connections} total connections")
    print("For accurate capacity estimation of 100+ camera FR deployment")
    print("="*80)
    print()
    
    print(f"🔧 Configuration:")
    print(f"   Unique cameras: {args.camera_count}")
    print(f"   Connections per camera: {args.connections_per_camera}")
    print(f"   Total connections: {total_connections}")
    print(f"   Test duration: {args.duration}s")
    print(f"   Camera selection: shuffled for variety")
    print()
    
    input("Press Enter to start multi-connection testing...")
    
    # Create and run multi-connection tester
    tester = MultiConnectionLoadTester(
        camera_count=args.camera_count,
        connections_per_camera=args.connections_per_camera,
        test_duration=args.duration
    )
    
    try:
        start_time = time.time()
        report = await tester.run_multi_connection_test()
        total_time = time.time() - start_time
        
        if "error" in report:
            print(f"❌ Test failed: {report['error']}")
            return 1
        
        # Display results
        print_multi_connection_summary(report)
        print(f"\n⏱️ Total testing time: {total_time/60:.1f} minutes")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
        return 130
    except Exception as e:
        print(f"❌ Multi-connection test failed: {e}")
        return 1


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)