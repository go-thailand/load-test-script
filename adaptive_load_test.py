#!/usr/bin/env python3
"""
Adaptive Camera Stream Load Testing Tool
=========================================

Finds the maximum number of concurrent FR streams that can be maintained stably
without excessive disconnections, and produces an analytical summary like a
data scientist/engineer would.

Implemented search strategy:
- Binary search within [1, initial_max] using stability criteria
- Tracks per-iteration outcomes and best stable result
- Produces analytical summary with recommendations and per-stream insights
"""

import asyncio
import sys
import os
from typing import Optional, Tuple
import time
import logging
import csv
import json

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from camera_stream_load_test import CameraStreamLoadTester, save_report, print_summary

class AdaptiveLoadTester:
    def __init__(self, initial_max: int = 100, test_duration: int = 120, 
                 stability_threshold: float = 0.1):
        """
        Args:
            initial_max: Starting number of streams to test
            test_duration: Duration for each test iteration (seconds)
            stability_threshold: Max acceptable reconnection rate (reconnections/streams)
        """
        self.initial_max = initial_max
        self.test_duration = test_duration
        self.stability_threshold = stability_threshold
        
        # Search state
        self.min_streams = 1
        self.max_streams = initial_max
        self.best_stable_count = 0
        self.test_iteration = 0
        
        # Results tracking
        self.test_results = []
        
        # Setup logging with unique logger name (saved under logs/)
        os.makedirs('logs', exist_ok=True)
        self.log_filename = os.path.join('logs', f'adaptive_load_test_{time.strftime("%Y%m%d_%H%M%S")}.log')
        
        # Create logger
        self.logger = logging.getLogger(f"AdaptiveLoadTester_{id(self)}")
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
    
    async def test_stream_count(self, stream_count: int) -> Tuple[bool, dict]:
        """Test a specific number of streams for stability"""
        self.test_iteration += 1
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"ITERATION {self.test_iteration}: Testing {stream_count} concurrent streams")
        self.logger.info(f"Duration: {self.test_duration}s, Stability threshold: {self.stability_threshold}")
        self.logger.info(f"{'='*60}")
        
        tester = CameraStreamLoadTester(
            max_concurrent=stream_count,
            test_duration=self.test_duration
        )
        
        try:
            report = await tester.run_load_test()
            
            if "error" in report:
                self.logger.error(f"Test failed: {report['error']}")
                return False, {"error": report["error"]}
            
            # Analyze stability
            achieved_streams = report["test_info"]["max_concurrent_achieved"]
            total_reconnections = report["stream_performance"]["total_reconnections"]
            
            # Calculate reconnection rate
            reconnection_rate = total_reconnections / achieved_streams if achieved_streams > 0 else float('inf')
            
            # Determine if stable
            is_stable = (
                achieved_streams >= stream_count * 0.9 and  # At least 90% of target streams achieved
                reconnection_rate <= self.stability_threshold  # Low reconnection rate
            )
            
            result_summary = {
                "stream_count": stream_count,
                "achieved_streams": achieved_streams,
                "total_reconnections": total_reconnections,
                "reconnection_rate": reconnection_rate,
                "is_stable": is_stable,
                "test_duration": report["test_info"]["duration_seconds"],
                "avg_fps": report["stream_performance"]["average_fps"],
                "full_report": report
            }
            
            self.test_results.append(result_summary)

            # Persist per-iteration artifacts (JSON + CSVs) under reports/
            ts = time.strftime("%Y%m%d_%H%M%S")
            base_stem = f"adaptive_iter{self.test_iteration}_streams{stream_count}_{ts}"
            reports_dir = os.path.join('reports')
            try:
                os.makedirs(reports_dir, exist_ok=True)
            except Exception:
                pass

            try:
                # Raw JSON report
                save_report(report, os.path.join(reports_dir, f"{base_stem}.json"))
            except Exception as e:
                self.logger.warning(f"Could not save iteration JSON: {e}")

            try:
                # Per-camera CSV
                cam_csv = os.path.join(reports_dir, f"{base_stem}_cameras.csv")
                fields = [
                    "camera_id", "status", "total_frames", "total_bytes",
                    "reconnections", "avg_fps", "duration_seconds", "errors_count"
                ]
                with open(cam_csv, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fields)
                    writer.writeheader()
                    for s in report.get("individual_streams", []):
                        writer.writerow({
                            "camera_id": s.get("camera_id"),
                            "status": s.get("status"),
                            "total_frames": s.get("total_frames"),
                            "total_bytes": s.get("total_bytes"),
                            "reconnections": s.get("reconnections"),
                            "avg_fps": s.get("avg_fps"),
                            "duration_seconds": s.get("duration_seconds"),
                            "errors_count": len(s.get("errors", [])),
                        })
                self.logger.info(f"   Saved per-camera CSV: {cam_csv}")
            except Exception as e:
                self.logger.warning(f"Could not save per-camera CSV: {e}")

            try:
                # System metrics CSV (from tester.system_stats)
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
            
            # Log results
            status = "✅ STABLE" if is_stable else "❌ UNSTABLE"
            self.logger.info(f"\nResult: {status}")
            self.logger.info(f"   Target streams: {stream_count}")
            self.logger.info(f"   Achieved streams: {achieved_streams}")
            self.logger.info(f"   Reconnections: {total_reconnections} (rate: {reconnection_rate:.3f})")
            self.logger.info(f"   Average FPS: {result_summary['avg_fps']:.2f}")
            
            if is_stable:
                self.best_stable_count = max(self.best_stable_count, achieved_streams)
                self.logger.info(f"   🎯 New stable maximum: {self.best_stable_count}")
            
            return is_stable, result_summary
            
        except Exception as e:
            self.logger.error(f"Test iteration failed: {e}")
            return False, {"error": str(e)}
    
    async def find_maximum_streams(self) -> dict:
        """Run adaptive search and return the adaptive summary report.

        Uses binary search within [1, initial_max] to identify the maximum
        stable concurrent stream count according to the stability threshold.
        """
        print(f"Starting adaptive search up to {self.initial_max} streams...")

        # Set exception handler for asyncio to suppress SSL-related noise
        loop = asyncio.get_running_loop()
        def exception_handler(loop, context):
            exception = context.get('exception')
            if isinstance(exception, Exception) and 'SSL' in str(exception):
                return
            print(f"Asyncio exception: {context}")
        loop.set_exception_handler(exception_handler)

        low, high = 1, max(1, self.initial_max)
        best = 0
        max_iterations = 12
        iterations = 0

        while low <= high and iterations < max_iterations:
            mid = (low + high) // 2
            is_stable, result = await self.test_stream_count(mid)

            # If the underlying test failed catastrophically, try smaller range
            if "error" in result and not is_stable:
                self.logger.info("   Encountered error at this level; decreasing search range")
                high = mid - 1
                iterations += 1
                continue

            if is_stable:
                achieved = result.get("achieved_streams", 0)
                best = max(best, achieved)
                low = mid + 1
                self.logger.info(f"   Decision: STABLE at {mid} → searching higher [{low}, {high}]")
            else:
                high = mid - 1
                self.logger.info(f"   Decision: UNSTABLE at {mid} → searching lower [{low}, {high}]")

            iterations += 1

        self.best_stable_count = max(self.best_stable_count, best)

        # Produce final adaptive report aggregating all iterations
        adaptive_report = self.generate_final_report()
        return adaptive_report
    
    def generate_final_report(self) -> dict:
        """Generate comprehensive report of the adaptive testing process"""
        # Find the best stable result
        stable_results = [r for r in self.test_results if r["is_stable"]]
        best_result = max(stable_results, key=lambda x: x["achieved_streams"]) if stable_results else None
        
        report = {
            "adaptive_test_info": {
                "total_iterations": self.test_iteration,
                "initial_max_target": self.initial_max,
                "test_duration_per_iteration": self.test_duration,
                "stability_threshold": self.stability_threshold,
                "maximum_stable_streams": self.best_stable_count
            },
            "optimization_results": {
                "recommended_max_streams": self.best_stable_count,
                "confidence_level": "high" if len(stable_results) >= 3 else "medium",
                "stability_verified": best_result is not None
            },
            "all_test_iterations": self.test_results,
            "best_stable_configuration": best_result,
            "analysis": self.analyze_adaptive_results()
        }
        
        return report
    
    def analyze_adaptive_results(self) -> dict:
        """Analyze the adaptive testing results with richer insights"""
        analysis = {
            "summary": "",
            "performance_characteristics": {},
            "recommendations": [],
            "top_unstable_cameras": [],
            "fps_distribution": {},
            "resource_peaks": {}
        }
        
        if self.best_stable_count == 0:
            analysis["summary"] = "❌ Unable to find stable configuration - system may be overloaded"
            analysis["recommendations"].extend([
                "Check network connectivity and server capacity",
                "Try reducing initial test parameters",
                "Consider testing during off-peak hours"
            ])
            return analysis
        
        stable_results = [r for r in self.test_results if r.get("is_stable")]
        unstable_results = [r for r in self.test_results if not r.get("is_stable")]
        
        # Performance characteristics
        if stable_results:
            avg_fps_stable = sum(r["avg_fps"] for r in stable_results) / len(stable_results)
            avg_reconnect_rate = sum(r["reconnection_rate"] for r in stable_results) / len(stable_results)
            
            analysis["performance_characteristics"] = {
                "max_stable_streams": self.best_stable_count,
                "avg_fps_at_stable": round(avg_fps_stable, 2),
                "avg_reconnection_rate": round(avg_reconnect_rate, 3),
                "stability_range": f"1-{self.best_stable_count} streams"
            }

            # Drill into best stable configuration for deeper analytics
            best_result = max(stable_results, key=lambda x: x.get("achieved_streams", 0))
            best_full = best_result.get("full_report", {}) if best_result else {}
            indiv = best_full.get("individual_streams", [])
            resources = best_full.get("system_resources", {})

            if indiv:
                fps_values = [s.get("avg_fps", 0) for s in indiv]
                fps_values_sorted = sorted(fps_values)
                def pct(vals, p):
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
                    "p50": round(pct(fps_values_sorted, 50), 2),
                    "p90": round(pct(fps_values_sorted, 90), 2),
                    "p95": round(pct(fps_values_sorted, 95), 2),
                    "max": round(fps_values_sorted[-1], 2) if fps_values_sorted else 0,
                }

                # Top cameras by reconnections
                top = sorted(indiv, key=lambda s: s.get("reconnections", 0), reverse=True)[:5]
                analysis["top_unstable_cameras"] = [
                    {
                        "camera_id": t.get("camera_id"),
                        "reconnections": t.get("reconnections", 0),
                        "avg_fps": t.get("avg_fps", 0),
                        "errors": t.get("errors", [])
                    }
                    for t in top if t.get("reconnections", 0) > 0
                ]

            if resources:
                analysis["resource_peaks"] = {
                    "peak_cpu_percent": resources.get("peak_cpu_percent"),
                    "peak_memory_percent": resources.get("peak_memory_percent"),
                    "average_cpu_percent": resources.get("average_cpu_percent"),
                    "average_memory_percent": resources.get("average_memory_percent"),
                }
        
        # Summary
        if self.best_stable_count >= 50:
            analysis["summary"] = f"✅ EXCELLENT: System can handle {self.best_stable_count} concurrent streams stably"
        elif self.best_stable_count >= 20:
            analysis["summary"] = f"✅ GOOD: System can handle {self.best_stable_count} concurrent streams stably"
        elif self.best_stable_count >= 10:
            analysis["summary"] = f"⚠️ MODERATE: System can handle {self.best_stable_count} concurrent streams stably"
        else:
            analysis["summary"] = f"❌ LIMITED: System can only handle {self.best_stable_count} concurrent streams stably"
        
        # Recommendations
        if unstable_results:
            first_unstable = min(r["stream_count"] for r in unstable_results)
            analysis["recommendations"].append(f"Stay below {first_unstable} streams to maintain stability")
        
        analysis["recommendations"].extend([
            f"Recommended production limit: {max(1, int(self.best_stable_count * 0.8))} streams (80% of max)",
            "Monitor system resources during production use",
            "Implement gradual stream scaling in production"
        ])
        
        return analysis

def print_adaptive_summary(report: dict):
    """Print adaptive test results summary"""
    print("\n" + "="*80)
    print("🎯 ADAPTIVE CAMERA STREAM LOAD TEST RESULTS")
    print("="*80)
    
    test_info = report.get("adaptive_test_info", {})
    results = report.get("optimization_results", {})
    analysis = report.get("analysis", {})
    
    print(f"\n📊 Optimization Process:")
    print(f"   Total test iterations: {test_info.get('total_iterations', 'N/A')}")
    print(f"   Duration per test: {test_info.get('test_duration_per_iteration', 'N/A')}s")
    print(f"   Stability threshold: {test_info.get('stability_threshold', 'N/A')}")
    
    print(f"\n🎯 Results:")
    max_stable = test_info.get('maximum_stable_streams', 0)
    print(f"   Maximum stable concurrent streams: {max_stable}")
    print(f"   Recommended production limit: {max(1, int(max_stable * 0.8))}")
    print(f"   Confidence level: {results.get('confidence_level', 'unknown')}")
    
    if "performance_characteristics" in analysis:
        perf = analysis["performance_characteristics"]
        print(f"\n📈 Performance at Maximum:")
        print(f"   Average FPS per stream: {perf.get('avg_fps_at_stable', 'N/A')}")
        print(f"   Average reconnection rate: {perf.get('avg_reconnection_rate', 'N/A')}")
        print(f"   Stable range: {perf.get('stability_range', 'N/A')}")

    if analysis.get("fps_distribution"):
        dist = analysis["fps_distribution"]
        print(f"\n📊 FPS Distribution (best stable):")
        print(f"   min: {dist.get('min', 'N/A')} | p50: {dist.get('p50', 'N/A')} | p90: {dist.get('p90', 'N/A')} | p95: {dist.get('p95', 'N/A')} | max: {dist.get('max', 'N/A')}")

    if analysis.get("resource_peaks"):
        res = analysis["resource_peaks"]
        print(f"\n🖥️  System Resources (best stable):")
        print(f"   Avg CPU: {res.get('average_cpu_percent', 'N/A')}% | Peak CPU: {res.get('peak_cpu_percent', 'N/A')}%")
        print(f"   Avg MEM: {res.get('average_memory_percent', 'N/A')}% | Peak MEM: {res.get('peak_memory_percent', 'N/A')}%")
    
    print(f"\n📋 Analysis:")
    print(f"   {analysis.get('summary', 'N/A')}")
    
    if analysis.get('recommendations'):
        print(f"\n💡 Recommendations:")
        for rec in analysis.get('recommendations', []):
            print(f"   - {rec}")

    if analysis.get('top_unstable_cameras'):
        print(f"\n🔎 Top Unstable Cameras (reconnections):")
        for c in analysis['top_unstable_cameras']:
            print(f"   - Camera {c.get('camera_id')}: {c.get('reconnections')} reconnections | avg FPS {c.get('avg_fps')} | errors: {len(c.get('errors', []))}")
    
    print("\n" + "="*80)

async def main():
    """Main entry point for adaptive testing"""
    print("="*80)
    print("🎯 ADAPTIVE CAMERA STREAM LOAD TEST")
    print("Finding maximum stable concurrent FR streams")
    print("="*80)
    print()
    
    # Get user configuration
    try:
        initial_max = input("Enter initial maximum to test (default 100): ").strip()
        initial_max = int(initial_max) if initial_max else 100
        
        test_duration = input("Enter test duration per iteration in seconds (default 120): ").strip()
        test_duration = int(test_duration) if test_duration else 120
        
        threshold = input("Enter stability threshold - max reconnections per stream (default 0.1): ").strip()
        threshold = float(threshold) if threshold else 0.1
        
    except ValueError:
        print("Invalid input, using defaults")
        initial_max = 100
        test_duration = 120
        threshold = 0.1
    
    print(f"\n🔧 Configuration:")
    print(f"   Initial maximum: {initial_max} streams")
    print(f"   Test duration per iteration: {test_duration}s")
    print(f"   Stability threshold: {threshold} reconnections/stream")
    print()
    
    input("Press Enter to start adaptive testing...")
    
    # Create and run adaptive tester
    tester = AdaptiveLoadTester(
        initial_max=initial_max,
        test_duration=test_duration,
        stability_threshold=threshold
    )
    
    try:
        start_time = time.time()
        adaptive_report = await tester.find_maximum_streams()
        total_time = time.time() - start_time

        # Save adaptive report under reports/
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"adaptive_load_test_report_{timestamp}.json"
        saved = save_report(adaptive_report, filename)
        if saved:
            print(f"\n💾 Adaptive report saved to: {saved}")
        else:
            print(f"⚠️ Could not save report")

        # Display results
        print_adaptive_summary(adaptive_report)

        print(f"\n⏱️ Total testing time: {total_time/60:.1f} minutes")

        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
        return 130
    except Exception as e:
        print(f"❌ Adaptive test failed: {e}")
        return 1

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)
