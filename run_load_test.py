#!/usr/bin/env python3
"""
Simple Camera Stream Load Test Runner
=====================================

Quick script to run camera stream load tests with common configurations.
"""

import asyncio
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from camera_stream_load_test import CameraStreamLoadTester, save_report, print_summary

async def quick_test():
    """Run a quick 5-minute test with moderate concurrent streams"""
    print("🎯 Starting 5-minute camera stream load test...")
    print("📊 Configuration:")
    print("   - Duration: 5 minutes (300 seconds)")
    print("   - API: https://cc.nttagid.com/api/v1/camera/")
    print("   - Will test cameras with status=1 using fr_url")
    print("   - Automatic reconnection on disconnect")
    print("   - System resource monitoring")
    print()
    
    # Ask user for max streams
    while True:
        try:
            max_streams = input("Enter maximum concurrent streams to test (default 20): ").strip()
            if not max_streams:
                max_streams = 20
            else:
                max_streams = int(max_streams)
            
            if max_streams <= 0:
                print("Please enter a positive number")
                continue
            elif max_streams > 200:
                print("⚠️  Warning: Testing more than 200 streams may overload your system")
                confirm = input("Continue? (y/n): ").strip().lower()
                if confirm != 'y':
                    continue
            
            break
        except ValueError:
            print("Please enter a valid number")
    
    # Create tester
    tester = CameraStreamLoadTester(
        api_url="https://cc.nttagid.com/api/v1/camera/",
        max_concurrent=max_streams,
        test_duration=300  # 5 minutes
    )
    
    try:
        report = await tester.run_load_test()
        
        if "error" in report:
            print(f"❌ Test failed: {report['error']}")
            return 1
        
        # Save report
        filename = save_report(report)
        if filename:
            print(f"\n💾 Full report saved to: {filename}")
        
        # Display summary
        print_summary(report)
        
        # Show log file location
        if hasattr(tester, 'log_filename'):
            print(f"\n📝 Execution log saved to: {tester.log_filename}")
        
        # Show key metrics matching user requirements
        print("\n🎯 KEY METRICS (as requested):")
        perf = report["stream_performance"]
        test_info = report["test_info"]
        
        print(f"   ✅ Successfully opened: {test_info['max_concurrent_achieved']} concurrent FR streams")
        print(f"   🔄 Total reconnections: {perf['total_reconnections']}")
        print(f"   ⏱️  Test duration: {test_info['duration_seconds']}s (target: 300s)")
        print(f"   📊 Total frames received: {perf['total_frames_received']:,}")
        print(f"   🚀 Average FPS per stream: {perf['average_fps']}")
        
        # Show per-camera reconnection stats
        reconnect_cameras = [s for s in report["individual_streams"] if s["reconnections"] > 0]
        if reconnect_cameras:
            print(f"\n🔄 CAMERAS WITH RECONNECTIONS:")
            for stream in reconnect_cameras:
                print(f"   Camera {stream['camera_id']}: {stream['reconnections']} reconnections")
        else:
            print(f"\n✅ No reconnections needed - all streams stable!")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        return 130
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1

def main():
    """Main entry point"""
    print("="*60)
    print("🎥 CAMERA STREAM LOAD TEST")
    print("="*60)
    print()
    
    try:
        result = asyncio.run(quick_test())
        sys.exit(result)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()