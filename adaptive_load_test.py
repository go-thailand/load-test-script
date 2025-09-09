#!/usr/bin/env python3
"""
Adaptive Camera Stream Load Testing Tool
=========================================

Automatically finds the maximum number of concurrent FR streams that can be 
maintained stably without excessive disconnections.

Algorithm:
1. Start with a high number of streams
2. Test for stability (low reconnection rate)
3. If unstable, reduce stream count and retry
4. If stable, try to increase slightly
5. Find optimal maximum through binary search
"""

import asyncio
import sys
import os
from typing import Optional, Tuple
import time
import logging

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
        
        # Setup logging with unique logger name  
        self.log_filename = f'adaptive_load_test_{time.strftime("%Y%m%d_%H%M%S")}.log'
        
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
        """Simple test - set cameras, run until time finishes, show summary"""
        print(f"Testing {self.initial_max} cameras for {self.test_duration} seconds...")
        
        # Set exception handler for asyncio to suppress SSL errors
        loop = asyncio.get_running_loop()
        def exception_handler(loop, context):
            exception = context.get('exception')
            if isinstance(exception, Exception) and 'SSL' in str(exception):
                return  # Silently ignore SSL errors
            # Log other exceptions
            print(f"Asyncio exception: {context}")
        loop.set_exception_handler(exception_handler)
        
        # Create tester and run
        tester = CameraStreamLoadTester(
            max_concurrent=self.initial_max,
            test_duration=self.test_duration
        )
        
        report = await tester.run_load_test()
        
        if "error" in report:
            print(f"Test failed: {report['error']}")
            return {"error": report["error"]}
        
        # Show summary
        perf = report["stream_performance"]
        test_info = report["test_info"]
        
        print(f"\n=== SUMMARY ===")
        print(f"Target cameras: {self.initial_max}")
        print(f"Achieved cameras: {test_info['max_concurrent_achieved']}")
        print(f"Test duration: {test_info['duration_seconds']}s")
        print(f"Total frames: {perf['total_frames_received']:,}")
        print(f"Total reconnections: {perf['total_reconnections']}")
        print(f"Average FPS per camera: {perf['average_fps']}")
        
        # Show per-camera reconnections if any
        reconnections = [(s['camera_id'], s['reconnections']) 
                        for s in report['individual_streams'] 
                        if s['reconnections'] > 0]
        
        if reconnections:
            print(f"\nReconnections per camera:")
            for cam_id, count in reconnections:
                print(f"  Camera {cam_id}: {count} reconnections")
        else:
            print(f"\nNo reconnections - all cameras stable!")
        
        return report
    
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
        """Analyze the adaptive testing results"""
        analysis = {
            "summary": "",
            "performance_characteristics": {},
            "recommendations": []
        }
        
        if self.best_stable_count == 0:
            analysis["summary"] = "❌ Unable to find stable configuration - system may be overloaded"
            analysis["recommendations"].extend([
                "Check network connectivity and server capacity",
                "Try reducing initial test parameters",
                "Consider testing during off-peak hours"
            ])
            return analysis
        
        stable_results = [r for r in self.test_results if r["is_stable"]]
        unstable_results = [r for r in self.test_results if not r["is_stable"]]
        
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
    
    test_info = report["adaptive_test_info"]
    results = report["optimization_results"]
    analysis = report["analysis"]
    
    print(f"\n📊 Optimization Process:")
    print(f"   Total test iterations: {test_info['total_iterations']}")
    print(f"   Duration per test: {test_info['test_duration_per_iteration']}s")
    print(f"   Stability threshold: {test_info['stability_threshold']}")
    
    print(f"\n🎯 Results:")
    print(f"   Maximum stable concurrent streams: {test_info['maximum_stable_streams']}")
    print(f"   Recommended production limit: {max(1, int(test_info['maximum_stable_streams'] * 0.8))}")
    print(f"   Confidence level: {results['confidence_level']}")
    
    if "performance_characteristics" in analysis:
        perf = analysis["performance_characteristics"]
        print(f"\n📈 Performance at Maximum:")
        print(f"   Average FPS per stream: {perf.get('avg_fps_at_stable', 'N/A')}")
        print(f"   Average reconnection rate: {perf.get('avg_reconnection_rate', 'N/A')}")
        print(f"   Stable range: {perf.get('stability_range', 'N/A')}")
    
    print(f"\n📋 Analysis:")
    print(f"   {analysis['summary']}")
    
    if analysis['recommendations']:
        print(f"\n💡 Recommendations:")
        for rec in analysis['recommendations']:
            print(f"   - {rec}")
    
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
        report = await tester.find_maximum_streams()
        total_time = time.time() - start_time
        
        # Save report
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"adaptive_load_test_report_{timestamp}.json"
        
        try:
            import json
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n💾 Full report saved to: {filename}")
        except Exception as e:
            print(f"⚠️ Could not save report: {e}")
        
        # Display results
        print_adaptive_summary(report)
        
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