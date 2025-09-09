การประเมินและเสนอระบบ AI Server สำหรับ CCTV สงขลา
เอกสารสรุป: การประเมินระบบ AI สำหรับโครงการ Songkhla CCTV Integration
1. ภาพรวมโครงการและความต้องการหลัก
โครงการ Songkhla CCTV Integration มีความต้องการระบบ AI สำหรับการตรวจจับใบหน้า (Face Detection Fusion Model) และอาจรวมถึงการตรวจจับป้ายทะเบียนรถ (License Plate Recognition - LPR) ในอนาคต โครงการนี้ถือเป็น "Enterprise Scale" เนื่องจากมีจำนวนกล้องสูงถึง 1,968 ตัว และคาดการณ์ผู้ใช้งานพร้อมกัน (concurrent users) ระหว่าง 31-50 คน ระบบจะต้องสามารถรองรับ:
• FPS Processing: 465-2,000 FPS (สำหรับผู้ใช้งาน) และรวมโหลดจากกล้องแล้วสูงสุด 80,720 FPS (Face Detection Only) หรือ 128,920 FPS (Face + LPR)
• API Calls: 31K-375K ครั้งต่อวัน
• Storage: 30-50TB (สำหรับการใช้งานร่วมกับผู้ใช้) หรือ 17.7TB ต่อเดือน (สำหรับ Face Recognition Only จากกล้อง)
• RAM: 1,536-2,048GB (สำหรับผู้ใช้งาน) หรือรวมโหลดจากกล้องแล้วสูงสุด 4,096GB
2. ข้อจำกัดของ AWS Solution และความจำเป็นในการเปลี่ยนผ่านสู่ AI Server
โซลูชัน AWS ปัจจุบันมีข้อจำกัดที่สำคัญ ทำให้ไม่สามารถรองรับความต้องการของโครงการ Songkhla ได้อย่างมีประสิทธิภาพ:
• ข้อจำกัด CPU Cores: "For AWS, the limit of CPU core for a company is limited to 24 CPU cores for automatic scaling. Above the 24 CPU cores allowance will require AWS Administrator approval." การตรวจจับใบหน้าและการค้นหาใบหน้า (Generative AI) ที่มีผู้ใช้งานพร้อมกันจำนวนมากใช้ CPU Core สูงมาก ซึ่ง AWS ไม่รองรับการ Scaling อัตโนมัติเกิน 24 Cores
• Scalability ของ CPU: "For a large project like Songkhla CCTV Integration, it’s not possible to rely on AWS CPU core. First, AWS doesn’t allow automatic scaling. Therefore, it doesn’t serve an effective operation for 4 and above concurrent users."
• ประสิทธิภาพการประมวลผล: "AWS scaling will not sustain the surge of computation power." โดยเฉพาะอย่างยิ่งสำหรับฟังก์ชัน "Face Search" ที่เป็น Generative AI
ดังนั้น การเปลี่ยนไปใช้ AI Server (On-premise) จึงเป็นคำแนะนำที่แข็งขันสำหรับโครงการนี้
3. การเปรียบเทียบ AI Server Hardware (Original, Dell, Inspur)
มีข้อเสนอ AI Server 3 รูปแบบที่ถูกเปรียบเทียบ โดยเน้นที่ GPU เป็นหลัก:
Component
Original Setup (Recommended)
Dell (SR650V3)
Inspur (H100)
GPU
1x NVIDIA A100 80GB
10x NVIDIA H100
1x NVIDIA H100 80GB
CPU
Intel Xeon Gold 6438Y (32 cores)
Not explicitly mentioned
2x Intel Xeon 6438Y (32 cores each)
Memory (RAM)
512GB ECC DDR4 RAM
Not explicitly mentioned
512GB (16x 32GB DDR5-5600MHz ECC-RDIMM)
Storage
2x 4TB NVMe SSD (RAID 1), 8x 16TB HDD (RAID 6)
2x 960GB SATA SSD
2x 3.84TB U.2 SSD, 6x 20TB SATA HDD (RAID 9560-16i)
PSU
Dual 1600W Titanium PSU
Not explicitly mentioned
4x 3000W Platinum PSU
Networking
Not explicitly mentioned
Not explicitly mentioned
2x 10Gbps NIC
Capacity
100+ CCTV, 40 FPS/stream, 500+ API req
Assumed scalable
Assumed scalable
ข้อสังเกตสำคัญ:
• GPU Performance: NVIDIA H100 เป็น GPU รุ่นล่าสุดที่มีประสิทธิภาพสูงกว่า A100 อย่างมาก
    ◦ Dell เสนอ 10x NVIDIA H100 ซึ่งให้ "unparalleled scalability" และเหมาะสำหรับความต้องการ FPS สูงและการประมวลผลพร้อมกันจำนวนมาก
    ◦ Inspur ระบุเพียง 1x NVIDIA H100 ในเอกสารเปรียบเทียบ ซึ่งไม่เพียงพอสำหรับความต้องการระดับ Enterprise ของโครงการ Songkhla ที่ต้องการอย่างน้อย 10-16 H100 GPUs (ตามข้อมูลการคำนวณ)
• RAM: Inspur ใช้ DDR5 ซึ่งเร็วกว่า DDR4 ใน Original Setup
• Storage: Original Setup และ Inspur มีตัวเลือก Storage ที่ดีกว่า Dell ทั้งในด้านความเร็วและความจุ
• Power Supply: Inspur เสนอ PSU ที่มีกำลังสูงกว่าและมีประสิทธิภาพสูง (Platinum)
4. ปัญหา Virtual GPU Incompatibility กับ NVIDIA A2-16Q
ปัญหาสำคัญที่เคยเกิดขึ้นกับระบบปัจจุบันคือ "CUDA Virtualization Incompatibility" บน NVIDIA A2-16Q
• สาเหตุ: "Your NVIDIA A2-16Q is a virtualized GPU - designed primarily for graphics workloads, not compute-intensive ML operations" ทำให้เกิดข้อผิดพลาด torch.AcceleratorError: CUDA error: operation not supported เมื่อพยายามใช้โมเดล YOLO บน GPU
• ลักษณะปัญหา: A2-16Q มี "Limited CUDA compute capability" และ "Virtualization overhead" ซึ่งไม่รองรับการทำงานของ CUDA operations ที่ PyTorch/YOLO ต้องการ
• การแก้ไข (ที่เสนอมา): เพิ่มการตรวจสอบ GPU ที่แข็งแกร่ง (Proactive GPU Testing) ในโค้ดเพื่อตรวจจับ Virtualized GPU และ fallback ไปใช้ CPU โดยอัตโนมัติหาก GPU ไม่รองรับการประมวลผล ML
บทเรียนสำคัญ: การเลือก GPU สำหรับงาน AI/ML จำเป็นต้องเป็น Physical GPU ที่รองรับ Compute Capability เต็มรูปแบบ ไม่ใช่ Virtual GPU ที่มีข้อจำกัดด้านการคำนวณ
5. การประเมินทรัพยากรสำหรับ 1,968 กล้อง และตัวเลือก GPU (H100 vs H200)
สำหรับจำนวนกล้อง 1,968 ตัว มีการวิเคราะห์ 2 Scenario:
Option 1: Face Recognition/Detection Only
• Computational Load: 29,520-78,720 FPS
• Storage: 590.4GB/วัน (~17.7TB/เดือน)
• H100 Configuration: ต้องการ 10-12 units H100 GPUs (3,000-4,000 FPS/GPU)
• H200 Configuration: ต้องการ 7-9 units H200 GPUs (4,200-5,600 FPS/GPU)
• Network (H100/H200): Total Network Load 7.87 Gbps, Recommended: 10 Gbps
Option 2: Face Recognition + License Plate Detection
• Computational Load: 59,040-128,920 FPS (รวม LPR)
• H100 Configuration: ต้องการ 14-16 units H100 GPUs (2,500-3,500 FPS/GPU)
• H200 Configuration: ต้องการ 10-12 units H200 GPUs (3,500-4,900 FPS/GPU)
• Network (H100/H200): Total Network Load 9.44 Gbps, Recommended: 10 Gbps
คำแนะนำสำหรับโครงการ Songkhla (Face + LPR with Concurrent Users):
• Recommended: H200 Configuration
    ◦ Rationale: "Significant reduction in hardware units", "Better parallel processing capability", "More efficient for dual workload", "Lower overall TCO despite higher unit cost"
    ◦ Configuration: 14 H200 GPUs, 6TB System RAM, 25Gbps Network Backbone, 200TB NVMe Storage
    ◦ Estimated Performance: 1,000 concurrent users, 130,000 FPS processing, 400K daily API calls
6. สถาปัตยกรรมเครือข่ายและการจัดเก็บข้อมูล (Network & Storage Architecture)
• Network Architecture (Hierarchical):
    ◦ Edge Layer: ~10 Gbps (Camera Streams: 7.87 Gbps, User Sessions: 2 Gbps)
    ◦ Aggregation Layer: 15 Gbps (Processing Traffic: 12 Gbps, User Interface Traffic: 3 Gbps)
    ◦ Core Layer: Recommended: 20 Gbps backbone
• Storage Tiered Approach:
    ◦ Hot Storage (NVMe): 150 TB
    ◦ Warm Storage (SAS/SATA SSD): 750 TB
    ◦ Cold Storage (HDDs): 1.5 PB
7. สถาปัตยกรรมแบบ Double Fault-Tolerant (สำหรับ Songkhla)
เพื่อรับประกันความต่อเนื่องในการทำงาน โครงการ Songkhla แนะนำสถาปัตยกรรมแบบ "Double False Tolerant" หรือ "Double Fault-Tolerant Architecture"
• Physical Distribution Model: แบ่งเป็น 2 Zone (Primary: Songkhla City, Secondary: Hat Yai) โดยแต่ละ Zone มี 2 Active Clusters
    ◦ แต่ละ Cluster: 6 H200 GPUs, 2TB RAM, 100TB NVMe Storage
    ◦ Total Components: 24 H200 GPUs, 8TB Total RAM, 400TB Total NVMe Storage, 40Gbps Total Network Capacity
• Redundancy Levels:
    ◦ Per Zone: Active-Active cluster pair, Synchronous data replication, Shared storage pool, Load-balanced processing
    ◦ Between Zones: Asynchronous replication, Independent power grids, Separate network providers, Different physical locations
• Failover Scenarios:
    ◦ Single GPU Failure: Response < 30s, Impact: None (N+1 redundancy)
    ◦ Single Cluster Failure: Response < 2 min, Impact: 25% capacity reduction
    ◦ Single Zone Failure: Response < 5 min, Impact: 50% capacity reduction
• Cost Impact (จากการเพิ่ม Concurrent Users):
    ◦ Hardware: 25-30% increase
    ◦ Storage: 40-45% increase
    ◦ Network: 35-40% increase
    ◦ Cooling: 20-25% increase
8. คำถามสำคัญสำหรับการประชุมกับ Inspur
จากข้อมูลทั้งหมด Inspur จำเป็นต้องตอบคำถามเพื่อยืนยันว่าข้อเสนอของพวกเขาตรงกับความต้องการของโครงการ โดยเฉพาะประเด็นที่เกี่ยวกับ Virtual GPU:
1. การยืนยันคุณสมบัติ GPU และสถาปัตยกรรม:
    ◦ "NVIDIA H100 80GB ที่เสนอมาเป็น Physical GPU 100% ใช่หรือไม่ และไม่ใช้ Virtualized GPU ที่มีข้อจำกัดด้าน Compute Capability สำหรับ ML Workloads เหมือนกับ A2-16Q ที่เกิดปัญหาใน Songkhla ใช่หรือไม่?"
    ◦ สามารถให้ข้อมูล CUDA Compute Capability ของ H100 ได้หรือไม่?
    ◦ รับประกันการทำงานเต็มรูปแบบของ CUDA operations ที่จำเป็นสำหรับ Deep Learning frameworks (PyTorch/YOLO) ได้หรือไม่?
    ◦ จำนวน GPU ต่อเซิร์ฟเวอร์: Inspur เสนอจำนวน H100 GPUs ต่อเซิร์ฟเวอร์อย่างไร เพื่อรองรับความต้องการ 10-16 H100s (หรือ 7-12 H200s) สำหรับโครงการ Songkhla ที่มี 1,968 กล้อง?
2. ประสิทธิภาพและการปรับขนาด (Scalability):
    ◦ ด้วยสเปกที่เสนอมา (ต้องระบุจำนวน GPU ที่เพียงพอ) จะรองรับ 1,968 กล้องที่ Enterprise-Scale (465-2,000 FPS, 31K-375K API calls/วัน) ได้อย่างไร?
    ◦ ระบบรองรับ Concurrent API Requests 500+ และ Concurrent Users จำนวนมาก (เช่น 50 คน) ได้หรือไม่?
    ◦ มีแผนการขยายระบบ (Scaling Strategy) สำหรับอนาคตอย่างไร (เช่น Horizontal Scaling, N+1/N+2 Redundancy)?
3. รายละเอียด Hardware และ Software:
    ◦ ยืนยันรายละเอียด CPU (2x Intel Xeon 6438Y+), Memory (512GB ECC DDR5-5600MHz), Storage (SSD, HDD, RAID) และสามารถอัปเกรดได้หรือไม่?
    ◦ Network (2x 10Gbps NIC) จะเพียงพอต่อความต้องการ Network Bandwidth ของโครงการ Songkhla (Edge Layer ~10 Gbps, Aggregation Layer 15 Gbps, Core Layer 20 Gbps) ได้อย่างไร?
    ◦ ระบบปฏิบัติการ (Ubuntu), NVIDIA Driver, CUDA Toolkit, และ Deep Learning frameworks (PyTorch, TensorFlow, YOLO) ที่ติดตั้งมาเป็นเวอร์ชันใดบ้าง?
4. ความน่าเชื่อถือและการรองรับ (Reliability & Support):
    ◦ มีกลยุทธ์ Fault Tolerance/Redundancy (N+1 หรือ N+2) สำหรับ Hardware ที่สำคัญอย่างไร?
    ◦ เงื่อนไขการรับประกันและแผนการบำรุงรักษา (SLA, 24/7 support) รวมถึงการอัปเดตซอฟต์แวร์?
    ◦ มี Case Study หรือ Reference Sites ที่ใช้เซิร์ฟเวอร์ H100 ในโครงการ AI/ML ขนาดใหญ่ที่มีกล้อง CCTV จำนวนมากหรือไม่?
บทสรุป:
โครงการ Songkhla ต้องการระบบ AI Server ที่มีประสิทธิภาพสูงและมีความทนทานต่อความผิดพลาด (Fault-Tolerant) เพื่อรองรับการประมวลผลวิดีโอจากกล้อง CCTV จำนวนมากและการใช้งานของผู้ใช้งานพร้อมกันจำนวนมาก การเลือก GPU (โดยเฉพาะ H200) และการออกแบบสถาปัตยกรรมเครือข่ายและ Storage ที่เหมาะสม รวมถึงการรับประกันว่า GPU ที่ใช้เป็น Physical GPU ที่รองรับการประมวลผล AI/ML เต็มรูปแบบ เป็นปัจจัยสำคัญในการเลือกโซลูชัน.