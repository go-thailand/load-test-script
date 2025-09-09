#!/usr/bin/env python3
"""
Setup and Test Verification Script
==================================

This script verifies the installation and runs a quick test to ensure
everything is working correctly before running full load tests.
"""

import subprocess
import sys
import asyncio
import aiohttp
from datetime import datetime

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

async def test_api_connection():
    """Test connection to the camera API"""
    print("🌐 Testing API connection...")
    api_url = "https://cc.nttagid.com/api/v1/camera/"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    cameras = await response.json()
                    active_cameras = [c for c in cameras if c.get('status') == 1 and c.get('fr_url')]
                    
                    print(f"✅ API connection successful")
                    print(f"   Total cameras: {len(cameras)}")
                    print(f"   Active cameras with FR URLs: {len(active_cameras)}")
                    
                    if len(active_cameras) >= 5:
                        print(f"✅ Sufficient active cameras for testing")
                    else:
                        print(f"⚠️  Only {len(active_cameras)} active cameras - limited testing possible")
                    
                    return True, len(active_cameras)
                else:
                    print(f"❌ API returned status {response.status}")
                    return False, 0
                    
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        return False, 0

async def test_single_stream():
    """Test connecting to a single camera stream"""
    print("📹 Testing single stream connection...")
    
    try:
        # Get a camera to test
        async with aiohttp.ClientSession() as session:
            async with session.get("https://cc.nttagid.com/api/v1/camera/") as response:
                cameras = await response.json()
                active_cameras = [c for c in cameras if c.get('status') == 1 and c.get('fr_url')]
                
                if not active_cameras:
                    print("❌ No active cameras found for testing")
                    return False
                
                # Test first camera
                test_camera = active_cameras[0]
                fr_url = test_camera['fr_url']
                camera_id = test_camera['id']
                
                print(f"   Testing camera {camera_id}: {fr_url}")
                
                # Try to connect to stream
                try:
                    async with session.get(
                        fr_url,
                        headers={'Accept': 'multipart/x-mixed-replace; boundary=frame'},
                        timeout=aiohttp.ClientTimeout(total=10, sock_read=5)
                    ) as stream_response:
                        
                        if stream_response.status == 200:
                            # Try to read a small amount of data
                            data = b''
                            async for chunk in stream_response.content.iter_chunked(1024):
                                data += chunk
                                if len(data) > 10000:  # Read ~10KB
                                    break
                            
                            if data:
                                print("✅ Stream connection successful - received data")
                                print(f"   Data sample length: {len(data)} bytes")
                                
                                # Check if it looks like multipart content
                                if b'--frame' in data or b'Content-Type' in data:
                                    print("✅ Stream format appears correct (multipart)")
                                else:
                                    print("⚠️  Stream format may be different than expected")
                                
                                return True
                            else:
                                print("⚠️  Connected but no data received")
                                return False
                        else:
                            print(f"❌ Stream returned status {stream_response.status}")
                            return False
                            
                except Exception as stream_error:
                    print(f"❌ Stream connection failed: {stream_error}")
                    return False
                    
    except Exception as e:
        print(f"❌ Single stream test failed: {e}")
        return False

def check_system_resources():
    """Check system resources"""
    print("💻 Checking system resources...")
    
    try:
        import psutil
        
        cpu_count = psutil.cpu_count()
        memory = psutil.virtual_memory()
        
        print(f"   CPU cores: {cpu_count}")
        print(f"   Total RAM: {memory.total / (1024**3):.1f} GB")
        print(f"   Available RAM: {memory.available / (1024**3):.1f} GB")
        print(f"   RAM usage: {memory.percent:.1f}%")
        
        # Recommendations based on resources
        if memory.total < 2 * (1024**3):  # Less than 2GB
            print("⚠️  Low memory - recommend testing fewer than 20 concurrent streams")
            recommended_streams = 10
        elif memory.total < 4 * (1024**3):  # Less than 4GB
            print("✅ Moderate memory - can test up to ~50 concurrent streams")
            recommended_streams = 50
        else:
            print("✅ Good memory - can test 100+ concurrent streams")
            recommended_streams = 100
        
        return True, recommended_streams
        
    except ImportError:
        print("⚠️  psutil not available - cannot check system resources")
        return True, 50

async def main():
    """Main setup and verification process"""
    print("="*60)
    print("🔧 CAMERA STREAM LOAD TEST SETUP")
    print("="*60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Install dependencies
    if not install_dependencies():
        print("❌ Setup failed - could not install dependencies")
        return 1
    
    # Step 2: Test API connection
    api_ok, camera_count = await test_api_connection()
    if not api_ok:
        print("❌ Setup failed - API connection issues")
        return 1
    
    # Step 3: Test single stream
    if not await test_single_stream():
        print("❌ Setup failed - stream connection issues")
        return 1
    
    # Step 4: Check system resources
    resources_ok, recommended_max = check_system_resources()
    
    print("\n" + "="*60)
    print("✅ SETUP VERIFICATION COMPLETE")
    print("="*60)
    
    print(f"\n📊 System Status:")
    print(f"   API Connection: ✅ Working")
    print(f"   Stream Connection: ✅ Working")
    print(f"   Available Cameras: {camera_count}")
    print(f"   Recommended Max Streams: {recommended_max}")
    
    print(f"\n🚀 Ready to run load tests!")
    print(f"\nRecommended commands:")
    print(f"   1. Find maximum capacity: python adaptive_load_test.py")
    print(f"   2. Quick 5-minute test: python run_load_test.py") 
    print(f"   3. Custom test: python camera_stream_load_test.py --max-streams {min(recommended_max, camera_count)}")
    
    return 0

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(result)
    except KeyboardInterrupt:
        print("\n⏹️  Setup interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)