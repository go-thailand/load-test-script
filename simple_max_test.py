#!/usr/bin/env python3
"""
Simple Maximum Capacity Test
============================

Single loop to find maximum concurrent FR streams without disconnections.
Starts high, decreases until stable, done.
"""

import asyncio
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from camera_stream_load_test import CameraStreamLoadTester, save_report

async def find_max_streams(start_max: int = 100, test_duration: int = 60, stability_threshold: float = 0.1):
    """
    Simple single loop to find maximum stable streams
    
    Args:
        start_max: Starting number to test
        test_duration: How long to test each attempt (seconds)
        stability_threshold: Max reconnections per stream (0.1 = 10%)
    """
    print(f"🎯 Finding maximum stable FR streams")
    print(f"Starting at: {start_max}, Test duration: {test_duration}s per attempt")
    print()
    
    current_test = start_max
    step_down = max(10, start_max // 10)  # Decrease by 10% or min 10
    
    while current_test > 0:
        print(f"🔄 Testing {current_test} concurrent streams...")
        
        # Create tester
        tester = CameraStreamLoadTester(
            max_concurrent=current_test,
            test_duration=test_duration
        )
        
        try:
            report = await tester.run_load_test()
            
            if "error" in report:
                print(f"❌ Failed: {report['error']}")
                current_test -= step_down
                continue
            
            # Check results
            achieved = report["test_info"]["max_concurrent_achieved"]
            reconnections = report["stream_performance"]["total_reconnections"]
            reconnect_rate = reconnections / achieved if achieved > 0 else float('inf')
            
            # Check if stable
            is_stable = (
                achieved >= current_test * 0.9 and  # Got at least 90% of target
                reconnect_rate <= stability_threshold  # Low reconnection rate
            )
            
            print(f"   Result: {achieved} streams achieved, {reconnections} reconnections (rate: {reconnect_rate:.3f})")
            
            if is_stable:
                # Success! This is our maximum
                print(f"✅ FOUND MAXIMUM: {achieved} concurrent streams")
                print(f"   Reconnection rate: {reconnect_rate:.3f} (threshold: {stability_threshold})")
                print(f"   Average FPS: {report['stream_performance']['average_fps']}")
                
                # Save final report
                filename = save_report(report, f"max_capacity_test_{achieved}_streams.json")
                if filename:
                    print(f"   Report saved: {filename}")
                
                return {
                    "max_stable_streams": achieved,
                    "reconnection_rate": reconnect_rate,
                    "avg_fps": report['stream_performance']['average_fps'],
                    "full_report": report
                }
            else:
                # Not stable, try fewer streams
                print(f"❌ Unstable - trying fewer streams")
                current_test -= step_down
                
                # Adjust step size as we get closer
                if current_test < start_max // 4:
                    step_down = max(5, step_down // 2)
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            current_test -= step_down
    
    print(f"❌ Could not find stable configuration")
    return {"max_stable_streams": 0, "error": "No stable configuration found"}

async def main():
    """Main entry point"""
    print("="*50)
    print("🎯 SIMPLE MAX CAPACITY TEST")
    print("="*50)
    print()
    
    # Use defaults or command line args
    start_max = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    test_duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    
    print(f"Configuration: Starting at {start_max} streams, {test_duration}s per test")
    print()
    
    start_time = time.time()
    result = await find_max_streams(start_max, test_duration)
    total_time = time.time() - start_time
    
    print(f"\n{'='*50}")
    print("🎯 FINAL RESULT")
    print(f"{'='*50}")
    
    if result["max_stable_streams"] > 0:
        print(f"✅ Maximum stable concurrent streams: {result['max_stable_streams']}")
        print(f"   Reconnection rate: {result.get('reconnection_rate', 0):.3f}")
        print(f"   Average FPS per stream: {result.get('avg_fps', 0):.2f}")
        print(f"   Recommended production limit: {int(result['max_stable_streams'] * 0.8)}")
    else:
        print(f"❌ Could not determine maximum capacity")
    
    print(f"\nTotal testing time: {total_time/60:.1f} minutes")
    return 0 if result["max_stable_streams"] > 0 else 1

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(result)
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)