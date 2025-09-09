#!/usr/bin/env python3
"""
Simple Camera Stream Test
=========================

Simple flow:
1. Set number of cameras
2. Run test until time finishes 
3. Show summary
"""

import asyncio
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from camera_stream_load_test import CameraStreamLoadTester

async def run_simple_test(num_cameras: int, duration: int):
    """Run simple test with specified cameras for specified time"""
    print(f"Testing {num_cameras} cameras for {duration} seconds...")
    
    # Create tester
    tester = CameraStreamLoadTester(
        max_concurrent=num_cameras,
        test_duration=duration
    )
    
    # Run test
    report = await tester.run_load_test()
    
    if "error" in report:
        print(f"Test failed: {report['error']}")
        return
    
    # Show summary
    perf = report["stream_performance"]
    test_info = report["test_info"]
    
    print(f"\n=== SUMMARY ===")
    print(f"Target cameras: {num_cameras}")
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

def main():
    # Get parameters from command line
    if len(sys.argv) < 2:
        print("Usage: python simple_test.py <num_cameras> [duration_seconds]")
        print("Example: python simple_test.py 32 300")
        sys.exit(1)
    
    try:
        num_cameras = int(sys.argv[1])
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 300  # Default 5 minutes
    except ValueError:
        print("Error: Please provide valid numbers")
        sys.exit(1)
    
    if num_cameras <= 0:
        print("Error: Number of cameras must be > 0")
        sys.exit(1)
    
    try:
        result = asyncio.run(run_simple_test(num_cameras, duration))
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()