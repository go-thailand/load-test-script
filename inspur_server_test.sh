#!/bin/bash

# Inspur H100 GPU Server Testing Script
# Purpose: Comprehensive testing for Songkhla CCTV Project (1,968 cameras)
# Requirements: Verify Physical GPU capabilities, not virtualized GPU issues

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log file
LOG_FILE="inspur_test_$(date +%Y%m%d_%H%M%S).log"

# Function to log and print
log_print() {
    local message="$1"
    local color="$2"
    echo -e "${color}${message}${NC}" | tee -a "$LOG_FILE"
}

# Header
echo "==============================================================================="
echo "         INSPUR H100 GPU SERVER TESTING SCRIPT"
echo "   Purpose: Evaluate server for Songkhla CCTV Project (1,968 cameras)"
echo "==============================================================================="
echo ""

log_print "🚀 Starting Inspur H100 GPU Server Testing..." "$BLUE"
log_print "📁 Log file: $LOG_FILE" "$BLUE"
echo ""

# Step 1: System Information
log_print "📋 STEP 1: System Information Collection" "$BLUE"
echo "----------------------------------------"

log_print "💻 CPU Information:" "$YELLOW"
if command -v lscpu &> /dev/null; then
    lscpu | grep -E "Model name|CPU\(s\)|Thread|Architecture|CPU MHz" | tee -a "$LOG_FILE"
else
    cat /proc/cpuinfo | grep -E "model name|processor|cpu cores" | head -10 | tee -a "$LOG_FILE"
fi

echo ""
log_print "🧠 Memory Information:" "$YELLOW"
free -h | tee -a "$LOG_FILE"
echo ""
if [ -f /proc/meminfo ]; then
    grep -E "MemTotal|MemAvailable" /proc/meminfo | tee -a "$LOG_FILE"
fi

echo ""
log_print "💾 Storage Information:" "$YELLOW"
df -h | tee -a "$LOG_FILE"
echo ""
lsblk | tee -a "$LOG_FILE"

echo ""

# Step 2: NVIDIA Driver and CUDA Check
log_print "📋 STEP 2: NVIDIA Driver & CUDA Verification" "$BLUE"
echo "--------------------------------------------"

if command -v nvidia-smi &> /dev/null; then
    log_print "✅ nvidia-smi found, checking GPU status..." "$GREEN"
    echo ""
    nvidia-smi | tee -a "$LOG_FILE"
    
    # Extract specific information
    echo ""
    log_print "🔍 GPU Analysis:" "$YELLOW"
    
    # Check GPU model
    gpu_name=$(nvidia-smi --query-gpu=name --format=csv,noheader,nounits)
    log_print "GPU Model: $gpu_name" "$NC"
    
    if [[ "$gpu_name" == *"H100"* ]]; then
        log_print "✅ EXCELLENT: H100 GPU detected - Enterprise-grade ML performance" "$GREEN"
    elif [[ "$gpu_name" == *"A100"* ]]; then
        log_print "✅ VERY GOOD: A100 GPU detected - High-end ML performance" "$GREEN"
    elif [[ "$gpu_name" == *"A2"* ]] && [[ "$gpu_name" == *"Virtual"* ]]; then
        log_print "⚠️  CRITICAL ISSUE: Virtualized A2 GPU detected - Known compatibility problems!" "$RED"
        log_print "   This matches the A2-16Q virtualization issue from Songkhla project" "$RED"
    else
        log_print "ℹ️  GPU: $gpu_name - Performance assessment needed" "$YELLOW"
    fi
    
    # Check memory
    gpu_memory=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits)
    log_print "GPU Memory: ${gpu_memory} MB" "$NC"
    
    # Check CUDA version
    cuda_version=$(nvidia-smi | grep "CUDA Version" | awk '{print $9}')
    log_print "CUDA Version: $cuda_version" "$NC"
    
    if [[ "$cuda_version" > "12.0" ]]; then
        log_print "✅ CUDA version is suitable for modern AI frameworks" "$GREEN"
    else
        log_print "⚠️  CUDA version may need updating for optimal performance" "$YELLOW"
    fi
    
    # Check compute capability
    echo ""
    log_print "🔍 CUDA Compute Capability Check:" "$YELLOW"
    if command -v nvidia-smi &> /dev/null; then
        nvidia-smi --query-gpu=compute_cap --format=csv,noheader | while read cap; do
            log_print "Compute Capability: $cap" "$NC"
            if (( $(echo "$cap >= 8.0" | bc -l) )); then
                log_print "✅ Excellent compute capability for AI/ML workloads" "$GREEN"
            elif (( $(echo "$cap >= 7.0" | bc -l) )); then
                log_print "✅ Good compute capability for AI/ML workloads" "$GREEN"
            else
                log_print "⚠️  Limited compute capability - may impact performance" "$YELLOW"
            fi
        done 2>/dev/null || log_print "ℹ️  Compute capability check requires specific tools" "$YELLOW"
    fi
    
else
    log_print "❌ CRITICAL: nvidia-smi not found!" "$RED"
    log_print "   - NVIDIA drivers may not be installed" "$RED"
    log_print "   - GPU may not be properly configured" "$RED"
    log_print "   - This server cannot run AI/ML workloads" "$RED"
fi

echo ""

# Step 3: Python and Dependencies Check
log_print "📋 STEP 3: Python Environment Verification" "$BLUE"
echo "--------------------------------------------"

if command -v python3 &> /dev/null; then
    python_version=$(python3 --version)
    log_print "✅ Python found: $python_version" "$GREEN"
    
    # Check if pip is available
    if command -v pip3 &> /dev/null; then
        log_print "✅ pip3 available" "$GREEN"
    else
        log_print "⚠️  pip3 not found - may need installation" "$YELLOW"
        log_print "   Install with: sudo apt update && sudo apt install python3-pip -y" "$YELLOW"
    fi
    
    # Check key Python packages
    log_print "🔍 Checking AI/ML Python packages:" "$YELLOW"
    
    packages=("torch" "numpy" "ultralytics" "psutil")
    for package in "${packages[@]}"; do
        if python3 -c "import $package" 2>/dev/null; then
            version=$(python3 -c "import $package; print(getattr($package, '__version__', 'unknown'))" 2>/dev/null)
            log_print "✅ $package: $version" "$GREEN"
        else
            log_print "❌ $package: Not installed" "$RED"
        fi
    done
    
else
    log_print "❌ CRITICAL: Python3 not found!" "$RED"
    log_print "   Install with: sudo apt update && sudo apt install python3 python3-pip -y" "$RED"
fi

echo ""

# Step 4: Network Configuration Check
log_print "📋 STEP 4: Network Configuration Assessment" "$BLUE"
echo "----------------------------------------------"

log_print "🌐 Network Interfaces:" "$YELLOW"
ip addr show | grep -E "inet|mtu" | tee -a "$LOG_FILE"

echo ""
log_print "🔍 Network Speed Assessment:" "$YELLOW"
network_interfaces=$(ip link show | grep -E "^[0-9]+:" | grep -v lo | awk -F': ' '{print $2}' | awk '{print $1}')

for interface in $network_interfaces; do
    if [[ -f "/sys/class/net/$interface/speed" ]]; then
        speed=$(cat "/sys/class/net/$interface/speed" 2>/dev/null || echo "unknown")
        if [[ "$speed" != "unknown" && "$speed" -ge 10000 ]]; then
            log_print "✅ $interface: ${speed} Mbps (10Gbps+) - Suitable for enterprise load" "$GREEN"
        elif [[ "$speed" != "unknown" && "$speed" -ge 1000 ]]; then
            log_print "⚠️  $interface: ${speed} Mbps (1Gbps) - May be insufficient for 1,968 cameras" "$YELLOW"
        else
            log_print "ℹ️  $interface: Speed unknown or not available" "$NC"
        fi
    fi
done

# Network requirements assessment
echo ""
log_print "📊 Songkhla Project Network Requirements:" "$YELLOW"
log_print "   - Edge Layer: ~10 Gbps required" "$NC"
log_print "   - Aggregation Layer: 15 Gbps required" "$NC"
log_print "   - Core Layer: 20 Gbps backbone recommended" "$NC"
log_print "   - Current system should have 2x 10Gbps NICs minimum" "$NC"

echo ""

# Step 5: Storage Assessment
log_print "📋 STEP 5: Storage Capacity & Performance Assessment" "$BLUE"
echo "-----------------------------------------------------"

log_print "💾 Current Storage Configuration:" "$YELLOW"
df -h | tee -a "$LOG_FILE"

echo ""
log_print "🔍 Storage Type Analysis:" "$YELLOW"
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE | tee -a "$LOG_FILE"

echo ""
# Check for NVMe drives (high performance)
if ls /dev/nvme* 1> /dev/null 2>&1; then
    log_print "✅ NVMe drives detected - High performance storage available" "$GREEN"
    nvme_info=$(lsblk | grep nvme | wc -l)
    log_print "   NVMe devices: $nvme_info" "$NC"
else
    log_print "⚠️  No NVMe drives detected - May impact performance" "$YELLOW"
fi

# Storage requirements assessment
echo ""
log_print "📊 Songkhla Project Storage Requirements:" "$YELLOW"
log_print "   - Face Recognition Only: ~17.7TB/month" "$NC"
log_print "   - Face + LPR: 30-50TB for enterprise scale" "$NC"
log_print "   - Recommended: Tiered storage (Hot NVMe, Warm SSD, Cold HDD)" "$NC"

echo ""

# Step 6: Performance Estimation
log_print "📋 STEP 6: Performance Estimation for Songkhla Project" "$BLUE"
echo "-------------------------------------------------------"

# GPU count estimation
if command -v nvidia-smi &> /dev/null; then
    gpu_count=$(nvidia-smi --list-gpus | wc -l)
    log_print "🎮 GPU Count: $gpu_count" "$NC"
    
    gpu_name=$(nvidia-smi --query-gpu=name --format=csv,noheader,nounits | head -1)
    
    if [[ "$gpu_name" == *"H100"* ]]; then
        fps_per_gpu=3500  # Conservative estimate for H100
        log_print "📈 Estimated Performance (H100):" "$YELLOW"
    elif [[ "$gpu_name" == *"A100"* ]]; then
        fps_per_gpu=2500  # Conservative estimate for A100
        log_print "📈 Estimated Performance (A100):" "$YELLOW"
    else
        fps_per_gpu=1000  # Conservative estimate for unknown GPU
        log_print "📈 Estimated Performance (Unknown GPU):" "$YELLOW"
    fi
    
    total_fps=$((fps_per_gpu * gpu_count))
    estimated_cameras=$((total_fps / 40))  # Assuming 40 FPS per camera
    
    log_print "   - FPS per GPU: $fps_per_gpu" "$NC"
    log_print "   - Total estimated FPS: $total_fps" "$NC"
    log_print "   - Estimated camera capacity: $estimated_cameras cameras" "$NC"
    log_print "   - Songkhla requirement: 1,968 cameras" "$NC"
    
    if [[ $estimated_cameras -ge 1968 ]]; then
        log_print "✅ EXCELLENT: System can handle Songkhla project requirements" "$GREEN"
    elif [[ $estimated_cameras -ge 1000 ]]; then
        log_print "⚠️  MARGINAL: System may handle partial requirements - scaling needed" "$YELLOW"
    else
        log_print "❌ INSUFFICIENT: System cannot handle Songkhla project requirements" "$RED"
        log_print "   Recommendation: Multiple servers or more GPUs needed" "$RED"
    fi
    
else
    log_print "❌ Cannot estimate performance without GPU information" "$RED"
fi

echo ""

# Step 7: Download YOLO Model (if not exists)
log_print "📋 STEP 7: YOLO Model Preparation" "$BLUE"
echo "-----------------------------------"

model_path="/tmp/yolov8s.pt"
if [[ ! -f "$model_path" ]]; then
    log_print "📥 Downloading YOLOv8s model for testing..." "$YELLOW"
    if command -v wget &> /dev/null; then
        wget https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8s.pt -O "$model_path" | tee -a "$LOG_FILE"
        if [[ -f "$model_path" ]]; then
            log_print "✅ YOLO model downloaded successfully" "$GREEN"
        else
            log_print "❌ Failed to download YOLO model" "$RED"
        fi
    else
        log_print "⚠️  wget not found - manual model download required" "$YELLOW"
        log_print "   Download: wget https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8s.pt -O /tmp/yolov8s.pt" "$YELLOW"
    fi
else
    log_print "✅ YOLO model already exists" "$GREEN"
fi

echo ""

# Step 8: Dependencies Installation Check
log_print "📋 STEP 8: Dependencies Installation Verification" "$BLUE"
echo "--------------------------------------------------"

if [[ -f "requirements.txt" ]]; then
    log_print "📄 Found requirements.txt" "$GREEN"
    cat requirements.txt | tee -a "$LOG_FILE"
    
    log_print "💡 To install dependencies, run:" "$YELLOW"
    log_print "   pip3 install -r requirements.txt" "$YELLOW"
else
    log_print "⚠️  requirements.txt not found in current directory" "$YELLOW"
    log_print "💡 Required packages: torch, ultralytics, numpy, psutil" "$YELLOW"
fi

echo ""

# Step 9: Test Script Verification
log_print "📋 STEP 9: Test Script Verification" "$BLUE"
echo "------------------------------------"

if [[ -f "test.py" ]]; then
    log_print "✅ Found test.py - Advanced performance testing script available" "$GREEN"
    log_print "💡 To run comprehensive testing:" "$YELLOW"
    log_print "   python3 test.py" "$YELLOW"
else
    log_print "⚠️  test.py not found - advanced testing not available" "$YELLOW"
fi

echo ""

# Step 10: Critical Issues Summary
log_print "📋 STEP 10: Critical Issues & Recommendations Summary" "$BLUE"
echo "------------------------------------------------------"

critical_issues=0

# Check for virtualized GPU issue
if command -v nvidia-smi &> /dev/null; then
    gpu_name=$(nvidia-smi --query-gpu=name --format=csv,noheader,nounits)
    if [[ "$gpu_name" == *"A2"* ]] && [[ "$gpu_name" == *"Virtual"* ]]; then
        log_print "🚨 CRITICAL ISSUE: Virtualized GPU detected!" "$RED"
        log_print "   - Same issue as Songkhla A2-16Q problem" "$RED"
        log_print "   - Will cause torch.AcceleratorError in AI workloads" "$RED"
        log_print "   - Recommendation: Replace with Physical H100/H200/A100" "$RED"
        ((critical_issues++))
    fi
fi

# Check GPU count for enterprise scale
if command -v nvidia-smi &> /dev/null; then
    gpu_count=$(nvidia-smi --list-gpus | wc -l)
    if [[ $gpu_count -lt 10 ]]; then
        log_print "⚠️  SCALING CONCERN: Only $gpu_count GPU(s) detected" "$YELLOW"
        log_print "   - Songkhla project requires 10-16 H100s or 7-12 H200s" "$YELLOW"
        log_print "   - Current configuration may not meet enterprise scale" "$YELLOW"
    fi
fi

if [[ $critical_issues -eq 0 ]]; then
    log_print "✅ No critical issues detected for AI/ML workloads" "$GREEN"
else
    log_print "⚠️  $critical_issues critical issue(s) found - review required" "$RED"
fi

echo ""

# Final Summary
echo "==============================================================================="
log_print "🏁 INSPUR H100 SERVER TESTING COMPLETED" "$BLUE"
echo "==============================================================================="

log_print "📄 Detailed log saved to: $LOG_FILE" "$NC"
log_print "🎯 Next Steps:" "$YELLOW"
log_print "   1. Review critical issues above" "$NC"
log_print "   2. Install missing dependencies: pip3 install -r requirements.txt" "$NC"
log_print "   3. Run comprehensive testing: python3 test.py" "$NC"
log_print "   4. Compare results with Songkhla project requirements" "$NC"

echo ""
log_print "💡 For Inspur meeting, verify:" "$YELLOW"
log_print "   - Physical H100 GPU (not virtualized)" "$NC"
log_print "   - Multiple GPUs per server for enterprise scale" "$NC"
log_print "   - 10Gbps+ network capability" "$NC"
log_print "   - Sufficient storage for 17.7TB+/month" "$NC"

echo "==============================================================================="