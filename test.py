import os  
import torch  
from ultralytics import YOLO  
import numpy as np
import time
import psutil
import json
from datetime import datetime
import urllib.request
import cv2
from PIL import Image  
def _detect_optimal_device():  
    """  
    Detect optimal device with virtualized GPU awareness, inspired by source [11].  
    """  
    if not torch.cuda.is_available():  
        print("🔸 CUDA not available, using CPU")  
        return "cpu"  
    try:  
        # Test basic CUDA operation [11]  
        test_tensor = torch.tensor([1.0]).cuda()  
        test_result = test_tensor * 2  
        torch.cuda.synchronize()  # Force execution  
        # Test more complex operation (similar to what YOLO needs) [11]  
        test_conv = torch.nn.Conv2d(3, 64, 3).cuda()  
        test_input = torch.randn(1, 3, 224, 224).cuda()  
        _ = test_conv(test_input)  
        torch.cuda.synchronize()  
        gpu_name = torch.cuda.get_device_name(0)  
        print(f"✅ GPU validation passed: {gpu_name}")  
        # Special handling for virtualized GPUs [11, 12]  
        if "A2" in gpu_name or "Virtual" in gpu_name or "vGPU" in gpu_name:  
            print("⚠️  Virtualized GPU detected - using conservative settings")  
            # Even if detected as virtualized, we still try CUDA with awareness  
            return "cuda"  
        return "cuda"  
    except (torch.cuda.OutOfMemoryError, RuntimeError, torch.AcceleratorError) as e:  
        print(f"🔴 GPU test failed: {e}")  
        print("🔄 Falling back to CPU for compatibility")  
        return "cpu"  
def _load_yolo_model_safely(model_path, device_to_use):  
    """  
    Load YOLO model with robust error handling, inspired by source [13, 14].  
    """  
    print(f"🔄 Loading YOLO model: {model_path}")  
    print(f"🎯 Target device: {device_to_use}")  
    try:  
        # Load model first  
        model = YOLO(model_path)  
        # Explicitly set device with error handling [13, 14]  
        if device_to_use == "cuda":  
            try:  
                # Test the model on GPU with a small dummy input  
                dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)  
                _ = model.predict(dummy_frame, device=device_to_use, verbose=False)  
                print("✅ GPU model validation successful")  
                return model, device_to_use  
            except (torch.AcceleratorError, RuntimeError) as gpu_error:  
                print(f"🔴 GPU model test failed: {gpu_error}")  
                print("🔄 Switching to CPU mode for model inference...")  
                device_to_use = "cpu"  
                model = YOLO(model_path)  # Reload for CPU (or just move if it was already loaded)  
                print(f"✅ Model loaded successfully on {device_to_use}")  
                return model, device_to_use  
        else:  
            print(f"✅ Model loaded successfully on {device_to_use}")  
            return model, device_to_use  
    except Exception as e:  
        print(f"❌ Critical error loading model: {e}")  
        raise e

def _download_test_images():
    """
    Download test images for realistic performance testing.
    """
    print("📥 Downloading test images for realistic benchmarking...")
    
    test_images = {
        "cctv_street.jpg": "https://github.com/ultralytics/yolov5/raw/master/data/images/bus.jpg",
        "people_detection.jpg": "https://github.com/ultralytics/yolov5/raw/master/data/images/zidane.jpg", 
        "multi_person.jpg": "https://raw.githubusercontent.com/ultralytics/ultralytics/main/ultralytics/assets/bus.jpg"
    }
    
    downloaded_images = []
    
    for filename, url in test_images.items():
        local_path = f"/tmp/{filename}"
        try:
            if not os.path.exists(local_path):
                print(f"  📥 Downloading {filename}...")
                urllib.request.urlretrieve(url, local_path)
                print(f"  ✅ Downloaded: {filename}")
            else:
                print(f"  ✅ Already exists: {filename}")
            downloaded_images.append(local_path)
        except Exception as e:
            print(f"  ⚠️  Failed to download {filename}: {e}")
    
    return downloaded_images

def _download_models():
    """
    Download YOLO models for comprehensive testing.
    Based on teammate context: YOLOv5m for faces, YOLOv8m for attributes
    """
    print("📥 Downloading YOLO models for comprehensive testing...")
    
    models = {
        "yolov8s.pt": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8s.pt",
        "yolov8m.pt": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8m.pt",
        "yolov5su.pt": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov5su.pt"  # YOLOv5 via ultralytics
    }
    
    downloaded_models = {}
    
    for model_name, url in models.items():
        local_path = f"/tmp/{model_name}"
        try:
            if not os.path.exists(local_path):
                print(f"  📥 Downloading {model_name}...")
                urllib.request.urlretrieve(url, local_path)
                print(f"  ✅ Downloaded: {model_name}")
            else:
                print(f"  ✅ Already exists: {model_name}")
            downloaded_models[model_name] = local_path
        except Exception as e:
            print(f"  ⚠️  Failed to download {model_name}: {e}")
    
    return downloaded_models

def _create_test_images_different_sizes():
    """
    Create test images in different resolutions for comprehensive testing.
    """
    print("🖼️  Creating test images in different resolutions...")
    
    # Create synthetic test images if real images fail to download
    test_resolutions = [
        (640, 640),    # Standard YOLO input
        (1280, 720),   # HD
        (1920, 1080),  # Full HD  
        (2560, 1440),  # 2K
        (3840, 2160)   # 4K
    ]
    
    test_images = []
    
    for width, height in test_resolutions:
        # Create a synthetic image with some complexity (patterns, shapes)
        img = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        
        # Add some patterns to make it more realistic
        # Add rectangles (simulating objects)
        cv2.rectangle(img, (width//4, height//4), (3*width//4, 3*height//4), (255, 0, 0), -1)
        cv2.rectangle(img, (width//8, height//8), (width//2, height//2), (0, 255, 0), -1)
        
        # Add circles (simulating faces/objects)
        cv2.circle(img, (width//3, height//3), min(width, height)//8, (0, 0, 255), -1)
        cv2.circle(img, (2*width//3, 2*height//3), min(width, height)//10, (255, 255, 0), -1)
        
        filename = f"/tmp/test_image_{width}x{height}.jpg"
        cv2.imwrite(filename, img)
        test_images.append((filename, f"{width}x{height}"))
        print(f"  ✅ Created: test_image_{width}x{height}.jpg")
    
    return test_images
        
def _benchmark_fps_performance_with_images(model, device, model_name="YOLO", test_images=None, num_runs=50):
    """
    Enhanced FPS benchmark with real images and multiple resolutions.
    """
    print(f"\n🔄 Starting FPS benchmark for {model_name} on {device.upper()}...")
    
    fps_results = {}
    
    if test_images:
        # Test with real images
        for image_path, resolution in test_images:
            print(f"  📊 Testing {resolution} with real image...")
            
            try:
                # Load image
                img = cv2.imread(image_path)
                if img is None:
                    print(f"    ⚠️  Could not load {image_path}, skipping...")
                    continue
                
                # Warm up
                for _ in range(10):
                    _ = model.predict(img, device=device, verbose=False)
                
                # Benchmark
                start_time = time.time()
                for _ in range(num_runs):
                    results = model.predict(img, device=device, verbose=False)
                
                if device == "cuda":
                    torch.cuda.synchronize()
                    
                end_time = time.time()
                
                total_time = end_time - start_time
                fps = num_runs / total_time
                
                # Count detections for more detailed analysis
                detections = len(results[0].boxes) if hasattr(results[0], 'boxes') and results[0].boxes is not None else 0
                
                fps_results[f"{resolution}_real"] = {
                    "fps": round(fps, 2),
                    "avg_time_per_frame": round(total_time / num_runs * 1000, 2),
                    "detections": detections,
                    "image_type": "real"
                }
                
                print(f"    ✅ {fps:.2f} FPS ({total_time/num_runs*1000:.2f}ms per frame, {detections} objects detected)")
                
            except Exception as e:
                print(f"    ❌ Error with {image_path}: {e}")
    else:
        # Fallback to synthetic images
        print("  📊 Using synthetic test images...")
        resolutions = [(640, 640), (1280, 720), (1920, 1080), (2560, 1440)]
        
        for width, height in resolutions:
            print(f"    📊 Testing {width}x{height} resolution...")
            
            # Create synthetic image with some complexity
            dummy_frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
            cv2.rectangle(dummy_frame, (width//4, height//4), (3*width//4, 3*height//4), (255, 0, 0), -1)
            cv2.circle(dummy_frame, (width//2, height//2), min(width, height)//6, (0, 255, 0), -1)
            
            # Warm up
            for _ in range(10):
                _ = model.predict(dummy_frame, device=device, verbose=False)
            
            # Benchmark
            start_time = time.time()
            for _ in range(num_runs):
                results = model.predict(dummy_frame, device=device, verbose=False)
            
            if device == "cuda":
                torch.cuda.synchronize()
                
            end_time = time.time()
            
            total_time = end_time - start_time
            fps = num_runs / total_time
            
            detections = len(results[0].boxes) if hasattr(results[0], 'boxes') and results[0].boxes is not None else 0
            
            fps_results[f"{width}x{height}_synthetic"] = {
                "fps": round(fps, 2),
                "avg_time_per_frame": round(total_time / num_runs * 1000, 2),
                "detections": detections,
                "image_type": "synthetic"
            }
            
            print(f"      ✅ {fps:.2f} FPS ({total_time/num_runs*1000:.2f}ms per frame, {detections} objects detected)")
    
    return fps_results

def _benchmark_fps_performance(model, device, num_frames=100):
    """
    Legacy function for backward compatibility.
    """
    return _benchmark_fps_performance_with_images(model, device, "YOLO", None, num_frames)

def _test_concurrent_capability(model, device, max_concurrent=10):
    """
    Test concurrent processing capability simulation.
    """
    print(f"\n🔄 Testing concurrent capability on {device.upper()}...")
    
    concurrent_results = {}
    dummy_frame = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    
    for concurrent_level in [1, 2, 4, 8, max_concurrent]:
        print(f"  📊 Testing {concurrent_level} concurrent requests...")
        
        # Simulate concurrent requests by rapid sequential processing
        start_time = time.time()
        
        for batch in range(concurrent_level):
            for _ in range(10):  # 10 frames per "concurrent" request
                _ = model.predict(dummy_frame, device=device, verbose=False)
        
        if device == "cuda":
            torch.cuda.synchronize()
            
        end_time = time.time()
        
        total_time = end_time - start_time
        total_requests = concurrent_level * 10
        rps = total_requests / total_time  # Requests per second
        
        concurrent_results[f"{concurrent_level}_concurrent"] = {
            "requests_per_second": round(rps, 2),
            "avg_response_time": round(total_time / total_requests * 1000, 2)
        }
        
        print(f"    ✅ {rps:.2f} RPS ({total_time/total_requests*1000:.2f}ms per request)")
    
    return concurrent_results

def _get_system_specs():
    """
    Get comprehensive system specifications.
    """
    specs = {
        "timestamp": datetime.now().isoformat(),
        "cpu": {
            "model": "Unknown",
            "cores": psutil.cpu_count(logical=False),
            "threads": psutil.cpu_count(logical=True),
            "frequency": psutil.cpu_freq().max if psutil.cpu_freq() else "Unknown"
        },
        "memory": {
            "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "available_gb": round(psutil.virtual_memory().available / (1024**3), 2)
        },
        "gpu": {
            "available": torch.cuda.is_available(),
            "count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "devices": []
        }
    }
    
    # Get CPU model info
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if "model name" in line:
                    specs["cpu"]["model"] = line.split(":")[1].strip()
                    break
    except:
        pass
    
    # Get GPU info
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            gpu_props = torch.cuda.get_device_properties(i)
            gpu_info = {
                "index": i,
                "name": gpu_props.name,
                "memory_gb": round(gpu_props.total_memory / (1024**3), 2),
                "compute_capability": f"{gpu_props.major}.{gpu_props.minor}",
                "multiprocessors": gpu_props.multi_processor_count
            }
            specs["gpu"]["devices"].append(gpu_info)
    
    return specs

def _generate_comparison_report(specs, device_used, fps_results, concurrent_results, model_path):
    """
    Generate comprehensive comparison report for different server configurations.
    """
    report = {
        "test_info": {
            "timestamp": datetime.now().isoformat(),
            "model_used": model_path,
            "device_used": device_used,
            "python_version": f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}",
            "pytorch_version": torch.__version__
        },
        "system_specifications": specs,
        "performance_results": {
            "fps_benchmark": fps_results,
            "concurrent_capability": concurrent_results
        },
        "analysis": _analyze_performance(specs, device_used, fps_results, concurrent_results)
    }
    
    return report

def _analyze_performance(specs, device_used, fps_results, concurrent_results):
    """
    Analyze performance results and provide recommendations.
    """
    analysis = {
        "device_assessment": "",
        "songkhla_project_compatibility": "",
        "recommendations": [],
        "estimated_capacity": {}
    }
    
    # Device Assessment
    if device_used == "cuda":
        gpu_count = len(specs["gpu"]["devices"])
        if gpu_count > 0:
            gpu_name = specs["gpu"]["devices"][0]["name"]
            gpu_memory = specs["gpu"]["devices"][0]["memory_gb"]
            
            if "H100" in gpu_name:
                analysis["device_assessment"] = f"✅ EXCELLENT: {gpu_name} with {gpu_memory}GB VRAM - Top-tier ML performance"
            elif "A100" in gpu_name:
                analysis["device_assessment"] = f"✅ VERY GOOD: {gpu_name} with {gpu_memory}GB VRAM - High-end ML performance"
            elif "A2" in gpu_name and "Virtual" in gpu_name:
                analysis["device_assessment"] = f"⚠️  PROBLEMATIC: {gpu_name} - Virtualized GPU with limited ML capabilities"
            else:
                analysis["device_assessment"] = f"ℹ️  {gpu_name} with {gpu_memory}GB VRAM - Performance varies"
        else:
            analysis["device_assessment"] = "❌ GPU detected but no device information available"
    else:
        analysis["device_assessment"] = "❌ CPU-only mode - Not suitable for enterprise AI workloads"
    
    # Songkhla Project Compatibility (1,968 cameras)
    if fps_results and "640x640" in fps_results:
        fps_640 = fps_results["640x640"]["fps"]
        
        # Estimate capacity for Songkhla project requirements
        estimated_cameras_per_gpu = fps_640 // 40  # Assuming 40 FPS per camera
        total_estimated_cameras = estimated_cameras_per_gpu * len(specs["gpu"]["devices"]) if device_used == "cuda" else 0
        
        analysis["estimated_capacity"] = {
            "fps_per_gpu": fps_640,
            "estimated_cameras_per_gpu": estimated_cameras_per_gpu,
            "total_estimated_cameras": total_estimated_cameras,
            "songkhla_requirement": 1968
        }
        
        if total_estimated_cameras >= 1968:
            analysis["songkhla_project_compatibility"] = f"✅ SUITABLE: Can handle {total_estimated_cameras} cameras (exceeds 1,968 requirement)"
        elif total_estimated_cameras >= 1000:
            analysis["songkhla_project_compatibility"] = f"⚠️  MARGINAL: Can handle {total_estimated_cameras} cameras (below 1,968 requirement)"
        else:
            analysis["songkhla_project_compatibility"] = f"❌ INSUFFICIENT: Can only handle {total_estimated_cameras} cameras (far below 1,968 requirement)"
    
    # Recommendations
    if device_used == "cpu":
        analysis["recommendations"].extend([
            "🔧 Install CUDA-capable GPU for AI workloads",
            "🔧 Consider NVIDIA H100/H200 for enterprise scale",
            "🔧 Ensure Physical GPU (not virtualized) for ML operations"
        ])
    elif "A2" in specs["gpu"]["devices"][0]["name"] if specs["gpu"]["devices"] else False:
        analysis["recommendations"].extend([
            "🔧 Replace A2-16Q with Physical GPU (H100/H200/A100)",
            "🔧 Avoid virtualized GPUs for ML workloads",
            "🔧 Consider multiple H100 GPUs for Songkhla scale"
        ])
    else:
        gpu_count = len(specs["gpu"]["devices"]) if device_used == "cuda" else 0
        if gpu_count < 10:
            analysis["recommendations"].append(f"🔧 Consider scaling to 10-16 GPUs for full Songkhla capacity")
        analysis["recommendations"].extend([
            "✅ Current GPU configuration suitable for ML workloads",
            "🔧 Monitor memory usage for concurrent processing",
            "🔧 Implement load balancing for multiple cameras"
        ])
    
    return analysis

def _save_report(report, filename="ai_server_performance_report.json"):
    """
    Save the performance report to a JSON file.
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"📄 Report saved to: {filename}")
        return filename
    except Exception as e:
        print(f"❌ Failed to save report: {e}")
        return None

def _comprehensive_model_testing(models, device, test_images):
    """
    Test multiple YOLO models for comprehensive comparison.
    Based on teammate context: YOLOv5m for faces, YOLOv8m for attributes
    """
    print(f"\n🔄 Starting comprehensive model testing...")
    
    all_results = {}
    
    for model_name, model_path in models.items():
        if not os.path.exists(model_path):
            print(f"⚠️  Model {model_name} not found at {model_path}, skipping...")
            continue
            
        print(f"\n📋 Testing {model_name}...")
        print("-" * 40)
        
        try:
            # Load model
            model, final_device = _load_yolo_model_safely(model_path, device)
            
            # Performance benchmark
            fps_results = _benchmark_fps_performance_with_images(
                model, final_device, model_name, test_images, num_runs=30
            )
            
            # Concurrent capability test
            concurrent_results = _test_concurrent_capability(model, final_device, max_concurrent=6)
            
            all_results[model_name] = {
                "device_used": final_device,
                "fps_performance": fps_results,
                "concurrent_capability": concurrent_results,
                "model_path": model_path
            }
            
            print(f"✅ {model_name} testing completed")
            
            # Clean up model to free memory
            del model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
        except Exception as e:
            print(f"❌ Error testing {model_name}: {e}")
            all_results[model_name] = {
                "error": str(e),
                "model_path": model_path
            }
    
    return all_results  
if __name__ == "__main__":  
    print("=== AI Server Performance Testing & Comparison Tool ===")
    print("🎯 Purpose: Evaluate server capability for Songkhla CCTV Project (1,968 cameras)")
    print("=" * 60)
    
    # Step 1: System Analysis
    print("\n📋 STEP 1: System Specifications Analysis")
    specs = _get_system_specs()
    print(f"💻 CPU: {specs['cpu']['model']} ({specs['cpu']['cores']} cores, {specs['cpu']['threads']} threads)")
    print(f"🧠 Memory: {specs['memory']['total_gb']}GB total, {specs['memory']['available_gb']}GB available")
    
    if specs["gpu"]["available"]:
        print(f"🎮 GPU: {specs['gpu']['count']} device(s) detected")
        for gpu in specs["gpu"]["devices"]:
            print(f"  - {gpu['name']} ({gpu['memory_gb']}GB VRAM, Compute {gpu['compute_capability']})")
    else:
        print("🎮 GPU: Not available (CPU-only mode)")
    
    # Step 2: Download Models and Test Images
    print(f"\n📋 STEP 2: Download Models & Test Images")
    
    # Download YOLO models (YOLOv5m for faces, YOLOv8m for attributes per teammate)
    models = _download_models()
    print(f"✅ Available models: {list(models.keys())}")
    
    # Download test images
    real_images = _download_test_images()
    
    # Create synthetic test images as fallback
    synthetic_images = _create_test_images_different_sizes()
    
    # Combine test images
    test_images = []
    if real_images:
        for img_path in real_images:
            # Get image dimensions
            try:
                img = cv2.imread(img_path)
                if img is not None:
                    h, w = img.shape[:2]
                    test_images.append((img_path, f"{w}x{h}"))
            except:
                pass
    test_images.extend(synthetic_images)
    
    print(f"✅ Test images prepared: {len(test_images)} images")

    # Step 3: Device Detection & Comprehensive Model Testing
    print(f"\n📋 STEP 3: Device Compatibility & Comprehensive Model Testing")
    optimal_device = _detect_optimal_device()  
    print(f"🎯 Detected optimal device: {optimal_device}")
    
    if not models:
        print(f"❌ Error: No YOLO models available for testing")
        print("💡 Please ensure internet connection for model downloads")
        exit(1)
    
    try:
        # Comprehensive testing of multiple models
        all_model_results = _comprehensive_model_testing(models, optimal_device, test_images)
        
        # Use the first successful model for legacy compatibility
        successful_model = None
        final_device = optimal_device
        fps_results = {}
        concurrent_results = {}
        
        for model_name, results in all_model_results.items():
            if "error" not in results:
                successful_model = model_name
                final_device = results["device_used"]
                fps_results = results["fps_performance"]
                concurrent_results = results["concurrent_capability"]
                break
        
        if not successful_model:
            print(f"❌ All models failed to load - check GPU compatibility")
            raise Exception("No models could be loaded successfully")
        
        print(f"✅ Using {successful_model} for main analysis on: {final_device.upper()}")
        
        # Step 4: Generate Comprehensive Report
        print(f"\n📋 STEP 4: Analysis & Report Generation")
        
        # Enhanced report with multiple model results
        report = _generate_comparison_report(specs, final_device, fps_results, concurrent_results, models.get(successful_model))
        report["multiple_model_results"] = all_model_results
        
        # Display Analysis Results
        analysis = report["analysis"]
        print(f"\n{'='*60}")
        print("📊 PERFORMANCE ANALYSIS RESULTS")
        print(f"{'='*60}")
        
        print(f"\n🔍 Device Assessment:")
        print(f"   {analysis['device_assessment']}")
        
        print(f"\n🎯 Songkhla Project Compatibility (1,968 cameras):")
        print(f"   {analysis['songkhla_project_compatibility']}")
        
        if analysis['estimated_capacity']:
            capacity = analysis['estimated_capacity']
            print(f"\n📈 Capacity Estimation:")
            print(f"   - FPS per GPU: {capacity['fps_per_gpu']}")
            print(f"   - Estimated cameras per GPU: {capacity['estimated_cameras_per_gpu']}")
            print(f"   - Total estimated camera capacity: {capacity['total_estimated_cameras']}")
            print(f"   - Songkhla requirement: {capacity['songkhla_requirement']} cameras")
        
        print(f"\n💡 Recommendations:")
        for i, rec in enumerate(analysis['recommendations'], 1):
            print(f"   {i}. {rec}")
        
        # Display Model Comparison Summary
        print(f"\n📊 MODEL COMPARISON SUMMARY")
        print(f"{'='*60}")
        print("Based on teammate context: YOLOv5m for faces, YOLOv8m for attributes")
        
        model_performance = {}
        for model_name, results in all_model_results.items():
            if "error" not in results:
                # Get average FPS across all resolutions
                fps_values = []
                for res_name, res_data in results["fps_performance"].items():
                    fps_values.append(res_data["fps"])
                
                avg_fps = sum(fps_values) / len(fps_values) if fps_values else 0
                
                # Get concurrent capability
                concurrent_8 = results["concurrent_capability"].get("8_concurrent", {})
                rps = concurrent_8.get("requests_per_second", 0)
                
                model_performance[model_name] = {
                    "avg_fps": round(avg_fps, 1),
                    "rps_8_concurrent": rps,
                    "device": results["device_used"]
                }
                
                print(f"✅ {model_name}: {avg_fps:.1f} avg FPS, {rps:.1f} RPS (8 concurrent) on {results['device_used'].upper()}")
            else:
                print(f"❌ {model_name}: Failed - {results['error']}")
        
        # Recommend best model for Songkhla
        if model_performance:
            best_model = max(model_performance.items(), key=lambda x: x[1]["avg_fps"])
            print(f"\n🏆 Best performing model: {best_model[0]} ({best_model[1]['avg_fps']} FPS)")
            
            if "yolov8m" in model_performance:
                print(f"💡 YOLOv8m (for attributes): {model_performance['yolov8m']['avg_fps']} FPS - Recommended for Songkhla")
            if "yolov5su" in model_performance:
                print(f"💡 YOLOv5 (for faces): {model_performance['yolov5su']['avg_fps']} FPS - Good for face detection")
        
        # Save Report
        print(f"\n📋 STEP 5: Saving Report")
        report_file = _save_report(report)
        
        # Final Summary
        print(f"\n{'='*60}")
        print("🎉 TESTING COMPLETED SUCCESSFULLY")
        print(f"{'='*60}")
        print(f"📄 Detailed report saved: {report_file}")
        print(f"🎯 Device used: {final_device.upper()}")
        
        if final_device == "cpu":  
            print("\n⚠️  WARNING: Running on CPU mode")
            print("   - Not suitable for enterprise AI workloads")
            print("   - Consider installing CUDA-capable GPU")
        else:
            print(f"\n✅ GPU mode active - Ready for AI/ML workloads")
            
    except Exception as e:  
        print(f"\n❌ Testing failed: {e}")
        print("🔧 Troubleshooting:")
        print("   1. Ensure YOLO model is downloaded")
        print("   2. Check GPU drivers and CUDA installation")
        print("   3. Verify system dependencies")
        
    print(f"\n{'='*60}")
    print("🏁 AI Server Performance Testing Finished")
    print(f"{'='*60}")  
