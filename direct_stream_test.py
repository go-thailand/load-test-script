#!/usr/bin/env python3
"""
Direct Camera Stream Load Testing Tool
=====================================

Runs a fixed number of concurrent FR streams with comprehensive analytics.
- Shuffles camera selection for variety
- Runs for specified duration (default 120s)
- Provides same analytical summary as adaptive test
- Saves detailed reports and CSVs for data science analysis

Usage:
    python direct_stream_test.py 4                         # 4 streams, 120s duration
    python direct_stream_test.py 4 300                     # 4 streams, 300s duration
    python direct_stream_test.py 4 300 --prefix=sai1       # with optional API prefix
"""

import asyncio
import sys
import os
import time
import logging
import csv
import json
from typing import Optional, Dict

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from camera_stream_load_test import CameraStreamLoadTester, save_report

class DirectLoadTester:
    def __init__(self, stream_count: int, test_duration: int = 120, prefix: str = ""):
        """
        Args:
            stream_count: Number of concurrent streams to test
            test_duration: Duration for the test (seconds)
        """
        self.stream_count = stream_count
        self.test_duration = test_duration
        self.prefix = prefix or ""
        
        # Setup logging with unique logger name (saved under logs/)
        os.makedirs('logs', exist_ok=True)
        self.log_filename = os.path.join('logs', f'direct_stream_test_{stream_count}streams_{time.strftime("%Y%m%d_%H%M%S")}.log')
        
        # Create logger
        self.logger = logging.getLogger(f"DirectLoadTester_{id(self)}")
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

    async def run_direct_test(self) -> dict:
        """Run direct stream count test and return comprehensive report"""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"DIRECT LOAD TEST: Testing {self.stream_count} concurrent streams")
        self.logger.info(f"Duration: {self.test_duration}s with shuffled camera selection")
        self.logger.info(f"{'='*60}")
        
        # Set exception handler for asyncio to suppress SSL-related noise
        loop = asyncio.get_running_loop()
        def exception_handler(loop, context):
            exception = context.get('exception')
            if isinstance(exception, Exception) and 'SSL' in str(exception):
                return
            print(f"Asyncio exception: {context}")
        loop.set_exception_handler(exception_handler)
        
        tester = CameraStreamLoadTester(
            max_concurrent=self.stream_count,
            test_duration=self.test_duration,
            shuffle_cameras=True,  # Enable camera shuffling for variety
            prefix=self.prefix
        )
        
        try:
            report = await tester.run_load_test()
            
            if "error" in report:
                self.logger.error(f"Test failed: {report['error']}")
                return {"error": report["error"]}
            
            # Enhance report with direct test analysis
            enhanced_report = self.enhance_report_with_analysis(report)
            
            # Save artifacts
            self.save_test_artifacts(enhanced_report, tester)
            
            return enhanced_report
            
        except Exception as e:
            self.logger.error(f"Direct test failed: {e}")
            return {"error": str(e)}

    def enhance_report_with_analysis(self, report: dict) -> dict:
        """Add comprehensive analysis similar to adaptive test"""
        enhanced = report.copy()
        
        # Add direct test specific info
        enhanced["direct_test_info"] = {
            "target_streams": self.stream_count,
            "achieved_streams": report["test_info"]["max_concurrent_achieved"],
            "test_duration": self.test_duration,
            "camera_selection": "shuffled",
            "success_rate": report["test_info"]["max_concurrent_achieved"] / self.stream_count if self.stream_count > 0 else 0
        }
        
        # Generate analysis
        enhanced["analysis"] = self.analyze_results(report)
        
        return enhanced

    def analyze_results(self, report: dict) -> dict:
        """Generate comprehensive analysis for data scientists"""
        analysis = {
            "summary": "",
            "performance_characteristics": {},
            "recommendations": [],
            "stability_assessment": {},
            "top_unstable_cameras": [],
            "fps_distribution": {},
            "resource_utilization": {},
            "stream_quality_metrics": {}
        }
        
        test_info = report.get("test_info", {})
        stream_perf = report.get("stream_performance", {})
        individual_streams = report.get("individual_streams", [])
        system_resources = report.get("system_resources", {})
        
        achieved_streams = test_info.get("max_concurrent_achieved", 0)
        total_reconnections = stream_perf.get("total_reconnections", 0)
        
        # Performance characteristics
        reconnection_rate = total_reconnections / achieved_streams if achieved_streams > 0 else float('inf')
        
        analysis["performance_characteristics"] = {
            "target_streams": self.stream_count,
            "achieved_streams": achieved_streams,
            "achievement_rate": round(achieved_streams / self.stream_count * 100, 1) if self.stream_count > 0 else 0,
            "avg_fps_per_stream": round(stream_perf.get("average_fps", 0), 2),
            "total_frames_received": stream_perf.get("total_frames_received", 0),
            "total_data_gb": round(stream_perf.get("total_bytes_received", 0) / (1024**3), 3),
            "reconnection_rate": round(reconnection_rate, 3),
            "test_duration_actual": test_info.get("duration_seconds", 0)
        }
        
        # Stability assessment
        if achieved_streams >= self.stream_count * 0.95 and reconnection_rate <= 0.1:
            stability = "EXCELLENT"
        elif achieved_streams >= self.stream_count * 0.90 and reconnection_rate <= 0.2:
            stability = "GOOD"
        elif achieved_streams >= self.stream_count * 0.80 and reconnection_rate <= 0.5:
            stability = "MODERATE"
        else:
            stability = "POOR"
            
        analysis["stability_assessment"] = {
            "rating": stability,
            "achievement_threshold_met": achieved_streams >= self.stream_count * 0.9,
            "reconnection_threshold_met": reconnection_rate <= 0.1,
            "overall_stable": stability in ["EXCELLENT", "GOOD"]
        }
        
        # FPS distribution analysis
        if individual_streams:
            fps_values = [s.get("avg_fps", 0) for s in individual_streams]
            fps_values_sorted = sorted(fps_values)
            
            def percentile(vals, p):
                if not vals:
                    return 0
                k = (len(vals)-1) * p / 100
                f, c = int(k), min(int(k)+1, len(vals)-1)
                if f == c:
                    return vals[f]
                d = k - f
                return vals[f] + (vals[c] - vals[f]) * d
                
            analysis["fps_distribution"] = {
                "min": round(fps_values_sorted[0], 2) if fps_values_sorted else 0,
                "p25": round(percentile(fps_values_sorted, 25), 2),
                "p50": round(percentile(fps_values_sorted, 50), 2),
                "p75": round(percentile(fps_values_sorted, 75), 2),
                "p90": round(percentile(fps_values_sorted, 90), 2),
                "p95": round(percentile(fps_values_sorted, 95), 2),
                "max": round(fps_values_sorted[-1], 2) if fps_values_sorted else 0,
                "std_dev": round(sum((x - stream_perf.get("average_fps", 0))**2 for x in fps_values) / len(fps_values), 2) if fps_values else 0
            }
            
            # Top unstable cameras analysis
            unstable_cameras = sorted(individual_streams, key=lambda s: s.get("reconnections", 0), reverse=True)[:5]
            analysis["top_unstable_cameras"] = [
                {
                    "camera_id": s.get("camera_id"),
                    "reconnections": s.get("reconnections", 0),
                    "avg_fps": round(s.get("avg_fps", 0), 2),
                    "total_frames": s.get("total_frames", 0),
                    "errors_count": len(s.get("errors", [])),
                    "stability_score": round(1.0 - (s.get("reconnections", 0) * 0.1), 2)
                }
                for s in unstable_cameras if s.get("reconnections", 0) > 0
            ]
        
        # Resource utilization
        if system_resources:
            analysis["resource_utilization"] = {
                "peak_cpu_percent": system_resources.get("peak_cpu_percent"),
                "average_cpu_percent": system_resources.get("average_cpu_percent"),
                "peak_memory_percent": system_resources.get("peak_memory_percent"),
                "average_memory_percent": system_resources.get("average_memory_percent"),
                "cpu_efficiency": "high" if system_resources.get("average_cpu_percent", 0) < 70 else "moderate" if system_resources.get("average_cpu_percent", 0) < 85 else "low",
                "memory_efficiency": "high" if system_resources.get("average_memory_percent", 0) < 70 else "moderate" if system_resources.get("average_memory_percent", 0) < 85 else "low"
            }
        
        # Stream quality metrics
        if individual_streams:
            connected_streams = [s for s in individual_streams if s.get("status") == "connected"]
            failed_streams = [s for s in individual_streams if s.get("status") in ["error", "disconnected"]]
            
            analysis["stream_quality_metrics"] = {
                "connection_success_rate": round(len(connected_streams) / len(individual_streams) * 100, 1) if individual_streams else 0,
                "average_stream_uptime": round(sum(s.get("duration_seconds", 0) for s in connected_streams) / len(connected_streams), 1) if connected_streams else 0,
                "zero_fps_streams": len([s for s in individual_streams if s.get("avg_fps", 0) == 0]),
                "high_performance_streams": len([s for s in individual_streams if s.get("avg_fps", 0) > 25]),
                "error_rate": round(len(failed_streams) / len(individual_streams) * 100, 1) if individual_streams else 0
            }
        
        # Summary
        perf_char = analysis["performance_characteristics"]
        if stability == "EXCELLENT" and perf_char["achievement_rate"] >= 95:
            analysis["summary"] = f"✅ EXCELLENT: Successfully streamed {achieved_streams}/{self.stream_count} cameras with {perf_char['avg_fps_per_stream']:.1f} avg FPS and minimal reconnections"
        elif stability == "GOOD" and perf_char["achievement_rate"] >= 90:
            analysis["summary"] = f"✅ GOOD: Successfully streamed {achieved_streams}/{self.stream_count} cameras with acceptable performance"
        elif stability == "MODERATE":
            analysis["summary"] = f"⚠️ MODERATE: Streamed {achieved_streams}/{self.stream_count} cameras but with some stability issues"
        else:
            analysis["summary"] = f"❌ POOR: Only achieved {achieved_streams}/{self.stream_count} cameras with significant stability problems"
        
        # Recommendations for data scientists
        recommendations = []
        
        if perf_char["achievement_rate"] < 90:
            recommendations.append(f"Target achievement rate low ({perf_char['achievement_rate']:.1f}%) - investigate connection issues")
        
        if reconnection_rate > 0.2:
            recommendations.append(f"High reconnection rate ({reconnection_rate:.3f}) - check network stability and server load")
        
        if analysis.get("resource_utilization", {}).get("average_cpu_percent", 0) > 80:
            recommendations.append("High CPU utilization detected - consider scaling or optimization")
        
        if analysis.get("fps_distribution", {}).get("std_dev", 0) > 5:
            recommendations.append("High FPS variance detected - investigate camera performance consistency")
        
        if len(analysis.get("top_unstable_cameras", [])) > 0:
            recommendations.append("Some cameras showing instability - review individual camera performance")
        
        recommendations.extend([
            f"System can handle {achieved_streams} concurrent streams at this configuration",
            "Monitor resource utilization during production deployment",
            "Consider implementing gradual scaling for production workloads"
        ])
        
        analysis["recommendations"] = recommendations
        
        return analysis

    def save_test_artifacts(self, report: dict, tester):
        """Save all test artifacts for data science analysis"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        base_stem = f"direct_stream_test_{self.stream_count}streams_{timestamp}"
        
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
            # Per-camera CSV
            cam_csv = os.path.join(reports_dir, f"{base_stem}_cameras.csv")
            fields = [
                "camera_id", "status", "total_frames", "total_bytes",
                "reconnections", "avg_fps", "duration_seconds", "errors_count", "stability_score"
            ]
            with open(cam_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                for s in report.get("individual_streams", []):
                    stability_score = 1.0 - (s.get("reconnections", 0) * 0.1)
                    writer.writerow({
                        "camera_id": s.get("camera_id"),
                        "status": s.get("status"),
                        "total_frames": s.get("total_frames"),
                        "total_bytes": s.get("total_bytes"),
                        "reconnections": s.get("reconnections"),
                        "avg_fps": s.get("avg_fps"),
                        "duration_seconds": s.get("duration_seconds"),
                        "errors_count": len(s.get("errors", [])),
                        "stability_score": round(stability_score, 3)
                    })
            self.logger.info(f"   Saved per-camera CSV: {cam_csv}")
        except Exception as e:
            self.logger.warning(f"Could not save per-camera CSV: {e}")
        
        try:
            # System metrics CSV
            sys_csv = os.path.join(reports_dir, f"{base_stem}_system.csv")
            sys_fields = [
                "timestamp", "cpu_percent", "memory_percent", "memory_used_gb",
                "network_bytes_sent", "network_bytes_recv", "active_streams",
                "total_frames", "total_bytes"
            ]
            with open(sys_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=sys_fields)
                writer.writeheader()
                for row in getattr(tester, "system_stats", []) or []:
                    writer.writerow(row)
            self.logger.info(f"   Saved system metrics CSV: {sys_csv}")
        except Exception as e:
            self.logger.warning(f"Could not save system metrics CSV: {e}")


def print_direct_summary(report: dict):
    """Print comprehensive test results summary for data scientists"""
    print("\n" + "="*80)
    print("🎯 DIRECT CAMERA STREAM LOAD TEST RESULTS")
    print("="*80)
    
    direct_info = report.get("direct_test_info", {})
    analysis = report.get("analysis", {})
    
    print(f"\n📊 Test Configuration:")
    print(f"   Target streams: {direct_info.get('target_streams', 'N/A')}")
    print(f"   Achieved streams: {direct_info.get('achieved_streams', 'N/A')}")
    print(f"   Success rate: {direct_info.get('success_rate', 0)*100:.1f}%")
    print(f"   Test duration: {direct_info.get('test_duration', 'N/A')}s")
    print(f"   Camera selection: {direct_info.get('camera_selection', 'N/A')}")
    
    perf = analysis.get("performance_characteristics", {})
    if perf:
        print(f"\n📈 Performance Metrics:")
        print(f"   Average FPS per stream: {perf.get('avg_fps_per_stream', 'N/A')}")
        print(f"   Total frames received: {perf.get('total_frames_received', 'N/A'):,}")
        print(f"   Total data processed: {perf.get('total_data_gb', 'N/A')} GB")
        print(f"   Reconnection rate: {perf.get('reconnection_rate', 'N/A')}")
    
    stability = analysis.get("stability_assessment", {})
    if stability:
        print(f"\n🔒 Stability Assessment:")
        print(f"   Overall rating: {stability.get('rating', 'N/A')}")
        print(f"   Achievement threshold met: {'✅' if stability.get('achievement_threshold_met') else '❌'}")
        print(f"   Reconnection threshold met: {'✅' if stability.get('reconnection_threshold_met') else '❌'}")
    
    fps_dist = analysis.get("fps_distribution", {})
    if fps_dist:
        print(f"\n📊 FPS Distribution:")
        print(f"   min: {fps_dist.get('min', 'N/A')} | p25: {fps_dist.get('p25', 'N/A')} | p50: {fps_dist.get('p50', 'N/A')} | p75: {fps_dist.get('p75', 'N/A')} | p90: {fps_dist.get('p90', 'N/A')} | max: {fps_dist.get('max', 'N/A')}")
        print(f"   Standard deviation: {fps_dist.get('std_dev', 'N/A')}")
    
    resources = analysis.get("resource_utilization", {})
    if resources:
        print(f"\n🖥️  System Resources:")
        print(f"   CPU: avg {resources.get('average_cpu_percent', 'N/A')}% | peak {resources.get('peak_cpu_percent', 'N/A')}% | efficiency: {resources.get('cpu_efficiency', 'N/A')}")
        print(f"   Memory: avg {resources.get('average_memory_percent', 'N/A')}% | peak {resources.get('peak_memory_percent', 'N/A')}% | efficiency: {resources.get('memory_efficiency', 'N/A')}")
    
    quality = analysis.get("stream_quality_metrics", {})
    if quality:
        print(f"\n📺 Stream Quality:")
        print(f"   Connection success rate: {quality.get('connection_success_rate', 'N/A')}%")
        print(f"   High performance streams (>25 FPS): {quality.get('high_performance_streams', 'N/A')}")
        print(f"   Zero FPS streams: {quality.get('zero_fps_streams', 'N/A')}")
        print(f"   Error rate: {quality.get('error_rate', 'N/A')}%")
    
    print(f"\n📋 Analysis:")
    print(f"   {analysis.get('summary', 'N/A')}")
    
    if analysis.get('recommendations'):
        print(f"\n💡 Data Science Recommendations:")
        for rec in analysis.get('recommendations', []):
            print(f"   - {rec}")
    
    if analysis.get('top_unstable_cameras'):
        print(f"\n🔎 Top Unstable Cameras:")
        for c in analysis['top_unstable_cameras']:
            print(f"   - Camera {c.get('camera_id')}: {c.get('reconnections')} reconnections | {c.get('avg_fps')} FPS | stability: {c.get('stability_score')}")
    
    print("\n" + "="*80)


async def main():
    """Main entry point for direct load testing"""
    # Parse CLI args: <stream_count> [duration_seconds] [--prefix=VALUE]
    if len(sys.argv) < 2:
        print("Usage: python direct_stream_test.py <stream_count> [duration_seconds] [--prefix=VALUE]")
        print("Example: python direct_stream_test.py 4 300 --prefix=sai1")
        sys.exit(1)

    # Extract optional --prefix argument, keep numeric args clean
    prefix = ""
    numeric_args = []
    for arg in sys.argv[1:]:
        if arg.startswith("--prefix="):
            prefix = arg.split("=", 1)[1]
        else:
            numeric_args.append(arg)

    try:
        stream_count = int(numeric_args[0])
        duration = int(numeric_args[1]) if len(numeric_args) > 1 else 120
    except (ValueError, IndexError):
        print("Error: Please provide valid numbers for <stream_count> and optional [duration_seconds]")
        sys.exit(1)
    
    if stream_count <= 0:
        print("Error: Stream count must be > 0")
        sys.exit(1)
    
    print("="*80)
    print("🎯 DIRECT CAMERA STREAM LOAD TEST")
    print(f"Testing {stream_count} concurrent FR streams with shuffled camera selection")
    print("="*80)
    print()
    if prefix:
        print(f"   API prefix: {prefix}")
    
    print(f"🔧 Configuration:")
    print(f"   Target streams: {stream_count}")
    print(f"   Test duration: {duration}s")
    print(f"   Camera selection: shuffled for variety")
    print()
    
    input("Press Enter to start testing...")
    
    # Create and run direct tester
    tester = DirectLoadTester(
        stream_count=stream_count,
        test_duration=duration,
        prefix=prefix
    )
    
    try:
        start_time = time.time()
        report = await tester.run_direct_test()
        total_time = time.time() - start_time
        
        if "error" in report:
            print(f"❌ Test failed: {report['error']}")
            return 1
        
        # Display results
        print_direct_summary(report)
        print(f"\n⏱️ Total testing time: {total_time/60:.1f} minutes")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
        return 130
    except Exception as e:
        print(f"❌ Direct test failed: {e}")
        return 1


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)
