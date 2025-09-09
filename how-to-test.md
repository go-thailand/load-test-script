คู่มือทดสอบและคำถามเซิร์ฟเวอร์ Inspur H100 GPU
เรียนท่าน
สำหรับการประชุมกับทาง Inspur ในวันนี้ ทางผมได้เตรียมคำสั่ง Ubuntu สำหรับการทดสอบเซิร์ฟเวอร์ และรายการคำถามที่ควรสอบถามในระหว่างการประชุม เพื่อให้แน่ใจว่าเครื่องที่เสนอมานั้นรองรับการทำงานตามความต้องการของเราได้อย่างแท้จริง โดยเฉพาะอย่างยิ่งในประเด็นปัญหาเรื่อง Virtual GPU ที่เคยเกิดขึ้นกับ NVIDIA A2-16Q ที่สงขลา [1]
--------------------------------------------------------------------------------
คำสั่ง Ubuntu สำหรับทดสอบเซิร์ฟเวอร์ (สำหรับ SSH)
เป้าหมายหลักของการทดสอบคือการยืนยันว่า NVIDIA H100 80GB GPU ที่ Inspur เสนอมานั้นเป็น Physical GPU ที่รองรับการประมวลผล AI/ML ได้อย่างเต็มที่ ไม่ใช่ Virtual GPU ที่มีข้อจำกัดด้านการคำนวณเหมือน A2-16Q [1-3]
1. **ตรวจสอบสถานะไดรเวอร์ NVIDIA และเวอร์ชัน CUDA:**นี่คือคำสั่งพื้นฐานที่จะแสดงข้อมูล GPU, ไดรเวอร์, และเวอร์ชัน CUDA [4-7]
nvidia-smi  
สิ่งที่ควรตรวจสอบจากผลลัพธ์:
• GPU Model: ต้องแสดงเป็น "NVIDIA H100 80GB" [8, 9] หรือใกล้เคียง
• CUDA Version: ควรเป็นเวอร์ชันที่รองรับ PyTorch และไลบรารี AI ล่าสุด (เช่น 12.x ขึ้นไป)
• Persistence-M: ควรเป็น "On" เพื่อให้ GPU ทำงานอย่างต่อเนื่อง
• Disp.A, Volatile Uncorr. ECC: ควรมีค่าตามปกติ (Off, 0)
• Memory-Usage: ควรแสดงขนาดหน่วยความจำทั้งหมดของ H100 (80GB) [8, 9] และการใช้งานปัจจุบันที่ต่ำ (เช่น 1MiB) หากยังไม่มีโปรเซสใดทำงานอยู่ [6]
• Processes: ควรแสดง "No running processes found" หากไม่มีการรันแอปพลิเคชันใดๆ [7]
2. **ทดสอบการทำงานของ CUDA และ PyTorch ด้วย Python Script:**ปัญหาก่อนหน้านี้คือ torch.AcceleratorError: CUDA error: operation not supported ซึ่งเกิดจากข้อจำกัดของ Virtual GPU [1, 10] เราจะใช้สคริปต์ Python เพื่อตรวจสอบการทำงานของ CUDA และการโหลดโมเดล YOLO บน GPU อย่างละเอียด ขั้นตอนการเตรียม (อาจต้องติดตั้งหากไม่มี):
    ◦ ติดตั้ง pip (ถ้ายังไม่ได้ติดตั้ง): sudo apt update && sudo apt install python3-pip -y
    ◦ ติดตั้ง torch พร้อม cuda (เลือกเวอร์ชัน CUDA ที่เหมาะสมกับผลลัพธ์จาก nvidia-smi):
    ◦ ติดตั้ง ultralytics สำหรับ YOLO:
    ◦ ดาวน์โหลดโมเดล YOLOv8s (ขนาดเล็กเพื่อการทดสอบ):
**Python Script (test_gpu_compatibility.py):**ให้สร้างไฟล์ชื่อ test_gpu_compatibility.py และคัดลอกโค้ดด้านล่างนี้ลงไป:
import os  
import torch  
from ultralytics import YOLO  
import numpy as np  
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
if __name__ == "__main__":  
    print("--- Starting GPU Compatibility Test ---")  
    optimal_device = _detect_optimal_device()  
    print(f"Detected optimal device: {optimal_device}")  
    # Define model path (assuming yolov8s.pt is in /tmp/)  
    model_path = "/tmp/yolov8s.pt"  
    if not os.path.exists(model_path):  
        print(f"❌ Error: YOLO model not found at {model_path}. Please download it first.")  
        exit(1)  
    try:  
        model, final_device = _load_yolo_model_safely(model_path, optimal_device)  
        print(f"\n🎉 Test Completed. Model is ready to use on: {final_device}")  
        if final_device == "cpu":  
            print("⚠️  Warning: Model is running on CPU. This might indicate GPU limitations for ML workloads.")  
    except Exception as e:  
        print(f"\n❌ Overall test failed: {e}")  
    print("--- GPU Compatibility Test Finished ---")  
วิธีรันสคริปต์:
python3 test_gpu_compatibility.py  
สิ่งที่ควรตรวจสอบจากผลลัพธ์:
• ควรเห็น "✅ GPU validation passed: NVIDIA H100 80GB"
• ไม่ควรเห็น "⚠️ Virtualized GPU detected" [11, 12]
• ไม่ควรเห็น "🔴 GPU test failed" หรือ "🔴 GPU model test failed" [13, 14]
• สุดท้ายควรแสดง "🎉 Test Completed. Model is ready to use on: cuda" [14]
--------------------------------------------------------------------------------
คำถามที่ควรสอบถามใน Meeting กับ Inspur
จากปัญหาที่เคยเกิดขึ้นและข้อกำหนดของโครงการสงขลา (Face Detection Fusion Model ที่ต้องการความเร็ว, ความแม่นยำ และความเสถียร รวมถึงการรองรับกล้อง 100+ ตัวและ API requests 500+ พร้อมการประมวลผล 40 FPS ต่อ Stream ใน Original Setup) [15-17] รวมถึงข้อกำหนด Enterprise-Scale (1,968 กล้อง, ผู้ใช้ 31-50 คน) [18, 19] และความต้องการ GPU H100/H200 จำนวนมาก [20-23]
1. การยืนยันคุณสมบัติ GPU และสถาปัตยกรรม:
    ◦ ยืนยัน GPU: NVIDIA H100 80GB ที่เสนอมาเป็น Physical GPU 100% ใช่หรือไม่ [8, 9]? และไม่ใช้ Virtualized GPU ที่มีข้อจำกัดด้าน Compute Capability สำหรับ ML Workloads เหมือนกับ A2-16Q ที่เกิดปัญหาใน Songkhla [1-3]?
    ◦ สามารถให้ข้อมูล CUDA Compute Capability ของ H100 ที่เสนอมาได้หรือไม่?
    ◦ ทาง Inspur สามารถ รับประกันการทำงานเต็มรูปแบบของ CUDA operations ที่จำเป็นสำหรับ Deep Learning frameworks เช่น PyTorch/YOLO ได้หรือไม่? [1, 3]
    ◦ จำนวน GPU ต่อเซิร์ฟเวอร์: สำหรับ Inspur ในเอกสารระบุเพียง 1x NVIDIA H100 80GB [9] ซึ่งไม่เพียงพอต่อความต้องการของโครงการสงขลา (1,968 กล้อง) ที่ต้องการอย่างน้อย 10-12 H100s สำหรับ Face Recognition Only หรือ 14-16 H100s สำหรับ Face + LPR [20-22] ทาง Inspur เสนอมาเป็นอย่างไร?
2. ประสิทธิภาพและการปรับขนาด (Scalability) สำหรับโครงการสงขลา:
    ◦ การรองรับ 1,968 กล้อง: ด้วยสเปกที่เสนอมา (ซึ่ง Inspur ระบุเพียง 1x NVIDIA H100 80GB [9]) จะรองรับการประมวลผล Face Detection + LPR สำหรับกล้อง 1,968 ตัวที่ Enterprise-Scale (465-2,000 FPS, 31K-375K API calls/วัน) ได้อย่างไร [19, 24]?
    ◦ จำนวน Concurrent Users: ระบบที่เสนอรองรับ Concurrent API Requests 500+ และ Concurrent Users จำนวนมาก (เช่น 50 คน) ได้หรือไม่? [15, 18, 19, 25]
    ◦ แผนการขยายระบบ (Scaling Strategy): Inspur มีแนวทางและข้อเสนอแนะสำหรับการขยายระบบในอนาคตอย่างไร หากความต้องการด้านผู้ใช้งานและกล้องเพิ่มขึ้นเกินกว่าสเปกของแต่ละยูนิต (เช่น การทำ Horizontal Scaling) [23, 26-29]?
3. รายละเอียด Hardware และ Software:
    ◦ CPU: ขอรายละเอียดรุ่นและจำนวนคอร์ของ Intel Xeon Gold 6438Y (Inspur ระบุ 2x Intel Xeon 6438Y) [8, 9]
    ◦ Memory (RAM): ยืนยันว่า RAM เป็น ECC DDR5 ขนาด 512GB (16x 32GB) และสามารถอัปเกรดเพิ่มได้หรือไม่ [9, 30]?
    ◦ Storage: * ยืนยันรายละเอียดของ SSD (2x 3.84TB U.2 SSD) และ HDD (6x 20TB SATA Enterprise HDD) พร้อมกับคอนฟิกูเรชัน RAID (RAID 9560-16i) [8, 9, 30, 31] * สามารถจัดสรร Storage เป็น Tiered Storage (Hot, Warm, Cold) ได้อย่างไร เพื่อรองรับข้อมูล 17.7TB/เดือน สำหรับ Face Recognition Only หรือ 30-50TB สำหรับ Enterprise Scale [19, 20, 32]?
    ◦ Network (NIC): ยืนยันว่ามี 2x 10Gbps NIC [9] และจะเพียงพอต่อความต้องการ Network Bandwidth ของโครงการสงขลา (Edge Layer ~10 Gbps, Aggregation Layer 15 Gbps, Core Layer 20 Gbps) ได้อย่างไร [22, 23, 33, 34]?
    ◦ ระบบปฏิบัติการและซอฟต์แวร์: * Ubuntu ที่ติดตั้งมาเป็นเวอร์ชันใด? * มีการติดตั้ง NVIDIA Driver และ CUDA Toolkit เวอร์ชันอะไรบ้าง? * มีการ Pre-install Deep Learning frameworks (เช่น PyTorch, TensorFlow) และไลบรารี YOLO มาให้ด้วยหรือไม่? หากมี เป็นเวอร์ชันใด?
4. ความน่าเชื่อถือและการรองรับ (Reliability & Support):
    ◦ Fault Tolerance/Redundancy: Inspur มีกลยุทธ์ด้าน N+1 หรือ N+2 Redundancy สำหรับ Workloads ที่สำคัญอย่างไร เพื่อให้มั่นใจถึงความต่อเนื่องของการทำงานของระบบ ในกรณีที่เกิดความผิดพลาดของ Hardware (เช่น GPU, PSU, Storage) [27, 35, 36]?
    ◦ การสนับสนุน: Inspur มีเงื่อนไขการรับประกันและแผนการบำรุงรักษา (SLA, 24/7 support) สำหรับ GPU และอุปกรณ์อื่นๆ อย่างไร [37]? รวมถึงการอัปเดตไดรเวอร์และซอฟต์แวร์?
    ◦ Case Study: Inspur มีกรณีศึกษาหรือ Reference Sites ที่นำเซิร์ฟเวอร์ H100 ไปใช้ในโครงการ AI/ML ขนาดใหญ่ ที่มีความต้องการด้านการประมวลผลสูงและมีกล้อง CCTV จำนวนมาก คล้ายกับโครงการ Songkhla CCTV Integration Project หรือไม่?
--------------------------------------------------------------------------------
หวังว่าข้อมูลและคำถามเหล่านี้จะเป็นประโยชน์สำหรับการประชุมในวันนี้ครับ ขอให้การประชุมราบรื่นและได้ข้อมูลที่ครบถ้วนตามต้องการครับ.