import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.transforms as transforms
import cv2
import numpy as np
import os
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox

# 1. 检查是否有可用GPU，否则使用CPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"使用设备: {device}")

# 2. 定义Mish激活函数,比ReLU保留更多特征信息
class Mish(nn.Module):
    def forward(self, x):
        return x * torch.tanh(F.softplus(x))

# 3. 定义基于YOLOv4-Tiny的特征融合模型
#    修改红外分支为可见光分支
class YOLOv4TinyFusion(nn.Module):
    def __init__(self):
        super(YOLOv4TinyFusion, self).__init__()
        # 主干网络：CSPDarknet53-Tiny 通过三个卷积层与批量归一化层（BatchNorm）提取特征
        # 第一层卷积步长为2，将图像尺寸缩小一半；第二层同样步长为2进一步缩小；第三层步长为1保持尺寸不变
        # 可见光分支
        self.vis_conv1 = nn.Conv2d(3, 32, kernel_size=3, stride=2, padding=1, bias=False)
        self.vis_bn1 = nn.BatchNorm2d(32)
        self.vis_conv2 = nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1, bias=False)
        self.vis_bn2 = nn.BatchNorm2d(64)
        self.vis_conv3 = nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.vis_bn3 = nn.BatchNorm2d(64)

        # 热成像分支
        self.thermal_conv1 = nn.Conv2d(3, 32, kernel_size=3, stride=2, padding=1, bias=False)
        self.thermal_bn1 = nn.BatchNorm2d(32)
        self.thermal_conv2 = nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1, bias=False)
        self.thermal_bn2 = nn.BatchNorm2d(64)
        self.thermal_conv3 = nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.thermal_bn3 = nn.BatchNorm2d(64)

        # 融合层：拼接两个分支特征后融合
        # 将两个分支的特征在通道维度上拼接（从各自的64通道变为128通道），然后通过一个卷积层与BN层将通道数降为64，同时用Mish激活。
        self.fusion_conv = nn.Conv2d(128, 64, kernel_size=3, padding=1, bias=False)
        self.fusion_bn = nn.BatchNorm2d(64)

        # 上采样恢复到1920x1080 使用转置卷积（ConvTranspose2d）将特征图上采样回原始图像尺寸（1080x1920），再经过一个卷积层调整输出通道数为3（RGB图像）
        self.up1 = nn.ConvTranspose2d(64, 32, kernel_size=4, stride=4, padding=0)
        self.up_conv1 = nn.Conv2d(32, 3, kernel_size=3, padding=1)

        self.mish = Mish()

    def forward(self, vis_img, thermal_img):
        # 可见光特征提取
        vis_x = self.mish(self.vis_bn1(self.vis_conv1(vis_img)))   # [1, 32, 540, 960]
        vis_x = self.mish(self.vis_bn2(self.vis_conv2(vis_x)))        # [1, 64, 270, 480]
        vis_x = self.mish(self.vis_bn3(self.vis_conv3(vis_x)))        # [1, 64, 270, 480]

        # 热成像特征提取
        thermal_x = self.mish(self.thermal_bn1(self.thermal_conv1(thermal_img)))  # [1, 32, 540, 960]
        thermal_x = self.mish(self.thermal_bn2(self.thermal_conv2(thermal_x)))      # [1, 64, 270, 480]
        thermal_x = self.mish(self.thermal_bn3(self.thermal_conv3(thermal_x)))      # [1, 64, 270, 480]

        # 特征融合
        fused_x = torch.cat((vis_x, thermal_x), dim=1)  # [1, 128, 270, 480]
        fused_x = self.mish(self.fusion_bn(self.fusion_conv(fused_x)))  # [1, 64, 270, 480]

        # 上采样回原始尺寸
        fused_img = self.mish(self.up1(fused_x))  # [1, 32, 1080, 1920]
        fused_img = self.up_conv1(fused_img)      # [1, 3, 1080, 1920]
        return torch.sigmoid(fused_img)           # 输出范围 [0,1]

# 4. 图像预处理
transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((1080, 1920)),
    transforms.ToTensor(),
])

def load_frame(frame, device):
    # frame 为 BGR 格式，转换为 RGB 后处理
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    tensor = transform(frame_rgb).unsqueeze(0).to(device)
    return tensor

def fuse_frame(model, vis_frame, thermal_frame, device):
    vis_tensor = load_frame(vis_frame, device)
    thermal_tensor = load_frame(thermal_frame, device)
    with torch.no_grad():
        fused_tensor = model(vis_tensor, thermal_tensor)
    # 转换 fused_tensor 为 Numpy 格式，并调整为 BGR
    fused_frame = fused_tensor.squeeze(0).permute(1, 2, 0).cpu().numpy()
    fused_frame = (fused_frame * 255).astype(np.uint8)
    fused_frame = cv2.cvtColor(fused_frame, cv2.COLOR_RGB2BGR)
    return fused_frame

# 5. 定义视频融合函数
def fuse_video(model, vis_video_path, thermal_video_path, output_path, device):
    vis_cap = cv2.VideoCapture(vis_video_path)
    thermal_cap = cv2.VideoCapture(thermal_video_path)

    if not vis_cap.isOpened() or not thermal_cap.isOpened():
        messagebox.showerror("错误", "无法打开视频文件，请检查路径是否正确！")
        return

    # 读取可见光视频的帧率（假设两视频帧率一致）
    fps = vis_cap.get(cv2.CAP_PROP_FPS)
    # 融合后视频输出尺寸 (1920, 1080)
    frame_width = 1920
    frame_height = 1080
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out_writer = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

    while True:
        ret_vis, vis_frame = vis_cap.read()
        ret_thermal, thermal_frame = thermal_cap.read()

        # 任一视频结束则退出循环
        if not ret_vis or not ret_thermal:
            break

        fused_frame = fuse_frame(model, vis_frame, thermal_frame, device)
        out_writer.write(fused_frame)

        # 可选：显示实时融合效果，按 'q' 键退出显示
        cv2.imshow("Fused Video", fused_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    vis_cap.release()
    thermal_cap.release()
    out_writer.release()
    cv2.destroyAllWindows()
    print(f"融合视频已保存至: {output_path}")

# 6. Tkinter 辅助函数：选择文件和保存路径
def select_file(title, filetypes=(("Video files", "*.mp4;*.avi"), ("All files", "*.*"))):
    return filedialog.askopenfilename(title=title, filetypes=filetypes)

def process_video_fusion():
    vis_video_path = select_file("选择可见光视频文件")
    thermal_video_path = select_file("选择热成像视频文件")
    output_path = filedialog.asksaveasfilename(title="保存融合视频", defaultextension=".mp4",
                                               filetypes=(("MP4 files", "*.mp4"), ("AVI files", "*.avi")))
    if not vis_video_path or not thermal_video_path or not output_path:
        messagebox.showerror("错误", "请确保选择所有视频文件和保存路径！")
        return

    model = YOLOv4TinyFusion().to(device)
    # 加载训练好的模型
    model = YOLOv4TinyFusion().to(device)
    if os.path.exists("fusion_model.pth"):
        model.load_state_dict(torch.load("fusion_model.pth", map_location=device))
        print("已加载训练模型")
    else:
        messagebox.showwarning("警告", "未找到训练模型，使用初始模型")

    fuse_video(model, vis_video_path, thermal_video_path, output_path, device)
    messagebox.showinfo("成功", "视频融合完成！")

# 7. 创建 Tkinter 图形界面
root = tk.Tk()
root.title("视频融合工具")

video_fuse_button = tk.Button(root, text="开始视频融合", command=process_video_fusion, width=25, height=2)
video_fuse_button.pack(pady=20)

root.mainloop()
