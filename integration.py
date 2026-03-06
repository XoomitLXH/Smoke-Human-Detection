import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import cv2
import numpy as np
import torch
import os
from scipy.spatial.distance import cdist
from PIL import Image, ImageTk
from tqdm import tqdm
from ultralytics import RTDETR
import torchvision.transforms as transforms
import torch.nn as nn
import torch.nn.functional as F

# Device setup
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Time Alignment Functions
def extract_motion_features(prev_frame, curr_frame):
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
    flow = cv2.calcOpticalFlowFarneback(prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    ang = ang * 180 / np.pi / 2
    hist_ang = cv2.calcHist([ang], [0], None, [32], [0, 180])
    hist_mag = cv2.calcHist([mag], [0], None, [32], [0, np.max(mag)])
    hist_ang = cv2.normalize(hist_ang, hist_ang).flatten()
    hist_mag = cv2.normalize(hist_mag, hist_mag).flatten()
    feature = np.concatenate([hist_ang * 0.6, hist_mag * 0.4])
    return feature / (np.linalg.norm(feature) + 1e-6)

def get_frame_timestamps(cap):
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    return [i / fps for i in range(frame_count)]

def find_max_overlap(video1_path, video2_path, threshold=0.9, tolerance=2):
    cap1 = cv2.VideoCapture(video1_path)
    cap2 = cv2.VideoCapture(video2_path)
    if not cap1.isOpened() or not cap2.isOpened():
        raise ValueError("无法打开视频文件")
    timestamps1 = get_frame_timestamps(cap1)
    timestamps2 = get_frame_timestamps(cap2)
    features1, frames1 = [], []
    ret, prev_frame = cap1.read()
    if not ret:
        raise ValueError("视频1首帧读取失败")
    frames1.append(prev_frame)
    while cap1.isOpened():
        ret, curr_frame = cap1.read()
        if not ret:
            break
        frames1.append(curr_frame)
        features1.append(extract_motion_features(prev_frame, curr_frame))
        prev_frame = curr_frame.copy()
    features2, frames2 = [], []
    ret, prev_frame = cap2.read()
    if not ret:
        raise ValueError("视频2首帧读取失败")
    frames2.append(prev_frame)
    while cap2.isOpened():
        ret, curr_frame = cap2.read()
        if not ret:
            break
        frames2.append(curr_frame)
        features2.append(extract_motion_features(prev_frame, curr_frame))
        prev_frame = curr_frame.copy()
    similarity_matrix = 1 - cdist(features1, features2, 'cosine')
    dp = np.zeros_like(similarity_matrix)
    dp[0][0] = similarity_matrix[0][0] if similarity_matrix[0][0] > threshold else 0
    for i in range(1, len(features1)):
        for j in range(1, len(features2)):
            sim = similarity_matrix[i][j]
            if sim > threshold:
                dp[i][j] = dp[i - 1][j - 1] + sim
            else:
                max_prev = 0
                for k in range(1, min(tolerance + 1, i + 1)):
                    if i - k >= 0 and j - k >= 0 and dp[i - k][j - k] > 0:
                        max_prev = max(max_prev, dp[i - k][j - k] - k * 0.05)
                dp[i][j] = max_prev
    max_dp = 0
    end_i, end_j = 0, 0
    for i in range(len(features1)):
        for j in range(len(features2)):
            if dp[i][j] > max_dp:
                max_dp = dp[i][j]
                end_i, end_j = i, j
    matches = []
    i, j = end_i, end_j
    while i >= 0 and j >= 0 and dp[i][j] > 0:
        matches.append((i, j))
        i -= 1
        j -= 1
    if not matches:
        raise ValueError("未找到连续重合段")
    return list(reversed(matches))

def trim_video(input_path, frame_indices, output_path, target_fps=25):
    cap = cv2.VideoCapture(input_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, target_fps, (width, height))
    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx + 1)
        ret, frame = cap.read()
        if ret:
            out.write(frame)
    cap.release()
    out.release()

# Spatial Alignment Functions
class InfraredThermalAligner:
    def __init__(self):
        from models.superpoint import SuperPoint
        from models.superglue import SuperGlue
        self.device = device
        self.superpoint = SuperPoint({'nms_radius': 4, 'keypoint_threshold': 0.005, 'max_keypoints': 1024}).eval().to(device)
        self.superglue = SuperGlue({'weights': 'indoor', 'sinkhorn_iterations': 20, 'match_threshold': 0.2, 'descriptor_dim': 256, 'GNN_layers': ['self', 'cross'] * 9}).eval().to(device)

    def preprocess_image(self, img):
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img = clahe.apply(img)
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        img = cv2.filter2D(img, -1, kernel)
        return img.astype(np.float32) / 255.

    def extract_features(self, img):
        img_tensor = torch.from_numpy(img).unsqueeze(0).unsqueeze(0).to(self.device)
        with torch.no_grad():
            features = self.superpoint({'image': img_tensor})
        return {
            'keypoints': features['keypoints'][0].cpu().numpy(),
            'descriptors': features['descriptors'][0].cpu().numpy(),
            'scores': features['scores'][0].cpu().numpy(),
            'image_shape': img.shape
        }

    def match_features(self, feat0, feat1):
        data = {
            'keypoints0': torch.from_numpy(feat0['keypoints']).unsqueeze(0).to(self.device),
            'keypoints1': torch.from_numpy(feat1['keypoints']).unsqueeze(0).to(self.device),
            'descriptors0': torch.from_numpy(feat0['descriptors']).unsqueeze(0).to(self.device),
            'descriptors1': torch.from_numpy(feat1['descriptors']).unsqueeze(0).to(self.device),
            'scores0': torch.from_numpy(feat0['scores']).unsqueeze(0).to(self.device),
            'scores1': torch.from_numpy(feat1['scores']).unsqueeze(0).to(self.device),
            'image0': torch.zeros(1, 1, *feat0['image_shape']).to(self.device),
            'image1': torch.zeros(1, 1, *feat1['image_shape']).to(self.device)
        }
        with torch.no_grad():
            matches = self.superglue(data)
        return matches['matches0'][0].cpu().numpy(), matches['matching_scores0'][0].cpu().numpy()

    def align_images(self, ir_img, thermal_img, min_matches=30):
        ir_preprocessed = self.preprocess_image(ir_img)
        th_preprocessed = self.preprocess_image(thermal_img)
        feat_ir = self.extract_features(ir_preprocessed)
        feat_th = self.extract_features(th_preprocessed)
        matches, scores = self.match_features(feat_ir, feat_th)
        valid = matches > -1
        kpts_ir = feat_ir['keypoints'][valid]
        kpts_th = feat_th['keypoints'][matches[valid]]
        if len(kpts_ir) >= min_matches:
            H, mask = cv2.findHomography(kpts_th, kpts_ir, cv2.RANSAC, 3.0)
            aligned_th = cv2.warpPerspective(thermal_img, H, (ir_img.shape[1], ir_img.shape[0]))
            return aligned_th, H
        else:
            raise ValueError(f"匹配点不足: {len(kpts_ir)} < {min_matches}")

# Dehaze Functions
def guided_filter(I, p, r=60, eps=1e-3):
    mean_I = cv2.boxFilter(I, -1, (r, r))
    mean_p = cv2.boxFilter(p, -1, (r, r))
    mean_Ip = cv2.boxFilter(I * p, -1, (r, r))
    cov_Ip = mean_Ip - mean_I * mean_p
    mean_II = cv2.boxFilter(I * I, -1, (r, r))
    var_I = mean_II - mean_I * mean_I
    a = cov_Ip / (var_I + eps)
    b = mean_p - a * mean_I
    mean_a = cv2.boxFilter(a, -1, (r, r))
    mean_b = cv2.boxFilter(b, -1, (r, r))
    return mean_a * I + mean_b

def contrast_guided_dehaze(img, mask, t0=0.3, r=60, eps=1e-3):
    img = np.clip(img, 0, 1)
    masked_img = img * mask
    flat_masked = masked_img[mask > 0]
    A = np.percentile(flat_masked, 90) if len(flat_masked) > 0 else np.percentile(img, 90)
    A = max(A, 0.1)
    sobel_x = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=3)
    contrast = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
    contrast = np.clip(contrast, 0, 1)
    t_initial = 1 - contrast
    t_refined = guided_filter(img, t_initial, r=r, eps=eps)
    t_refined = np.maximum(t_refined, t0)
    J = (img - A) / t_refined + A
    J = np.clip(J, 0, 1)
    result = J * mask + img * (1 - mask)
    result = (result * 255).astype(np.uint8)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    result = clahe.apply(result)
    return np.clip(result * 1.3, 0, 255).astype(np.uint8)

def threshold_mask(img, threshold=0.6):
    mask = (img > threshold).astype(np.float32)
    kernel = np.ones((5, 5), np.uint8)
    return cv2.dilate(mask, kernel, iterations=2)

# Multimodal Fusion Functions
class Mish(nn.Module):
    def forward(self, x):
        return x * torch.tanh(F.softplus(x))

class YOLOv4TinyFusion(nn.Module):
    def __init__(self):
        super(YOLOv4TinyFusion, self).__init__()
        self.vis_conv1 = nn.Conv2d(3, 32, kernel_size=3, stride=2, padding=1, bias=False)
        self.vis_bn1 = nn.BatchNorm2d(32)
        self.vis_conv2 = nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1, bias=False)
        self.vis_bn2 = nn.BatchNorm2d(64)
        self.vis_conv3 = nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.vis_bn3 = nn.BatchNorm2d(64)
        self.thermal_conv1 = nn.Conv2d(3, 32, kernel_size=3, stride=2, padding=1, bias=False)
        self.thermal_bn1 = nn.BatchNorm2d(32)
        self.thermal_conv2 = nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1, bias=False)
        self.thermal_bn2 = nn.BatchNorm2d(64)
        self.thermal_conv3 = nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.thermal_bn3 = nn.BatchNorm2d(64)
        self.fusion_conv = nn.Conv2d(128, 64, kernel_size=3, padding=1, bias=False)
        self.fusion_bn = nn.BatchNorm2d(64)
        self.up1 = nn.ConvTranspose2d(64, 32, kernel_size=4, stride=4, padding=0)
        self.up_conv1 = nn.Conv2d(32, 3, kernel_size=3, padding=1)
        self.mish = Mish()

    def forward(self, vis_img, thermal_img):
        vis_x = self.mish(self.vis_bn1(self.vis_conv1(vis_img)))
        vis_x = self.mish(self.vis_bn2(self.vis_conv2(vis_x)))
        vis_x = self.mish(self.vis_bn3(self.vis_conv3(vis_x)))
        thermal_x = self.mish(self.thermal_bn1(self.thermal_conv1(thermal_img)))
        thermal_x = self.mish(self.thermal_bn2(self.thermal_conv2(thermal_x)))
        thermal_x = self.mish(self.thermal_bn3(self.thermal_conv3(thermal_x)))
        fused_x = torch.cat((vis_x, thermal_x), dim=1)
        fused_x = self.mish(self.fusion_bn(self.fusion_conv(fused_x)))
        fused_img = self.mish(self.up1(fused_x))
        fused_img = self.up_conv1(fused_img)
        return torch.sigmoid(fused_img)

transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((1080, 1920)),
    transforms.ToTensor(),
])

def load_frame(frame, device):
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return transform(frame_rgb).unsqueeze(0).to(device)

def fuse_frame(model, vis_frame, thermal_frame, device):
    vis_tensor = load_frame(vis_frame, device)
    thermal_tensor = load_frame(thermal_frame, device)
    with torch.no_grad():
        fused_tensor = model(vis_tensor, thermal_tensor)
    fused_frame = fused_tensor.squeeze(0).permute(1, 2, 0).cpu().numpy()
    fused_frame = (fused_frame * 255).astype(np.uint8)
    return cv2.cvtColor(fused_frame, cv2.COLOR_RGB2BGR)

# Person Detection Functions
def detect_persons(model, frame, conf=0.5, iou=0.45):
    results = model(frame, conf=conf, iou=iou)
    result = results[0]
    for box in result.boxes:
        if int(box.cls[0]) == 0:  # 0表示人体
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"Person: {confidence:.2f}"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            cv2.rectangle(frame, (x1, y1 - 20), (x1 + w, y1), (0, 255, 0), -1)
            cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    return frame

# Main Integration Class
class VideoProcessor:
    def __init__(self, root):
        self.root = root
        self.root.title("视频处理工具")
        self.root.geometry("600x400")
        self.vis_video_path = ""
        self.thermal_video_path = ""
        self.output_dir = ""
        self.is_saving = False
        self.create_ui()

    def create_ui(self):
        tk.Label(self.root, text="选择可见光视频").grid(row=0, column=0, padx=5, pady=5)
        self.vis_entry = tk.Entry(self.root, width=40)
        self.vis_entry.grid(row=0, column=1)
        tk.Button(self.root, text="浏览", command=lambda: self.select_file(self.vis_entry, "可见光")).grid(row=0, column=2)

        tk.Label(self.root, text="选择热成像视频").grid(row=1, column=0, padx=5, pady=5)
        self.thermal_entry = tk.Entry(self.root, width=40)
        self.thermal_entry.grid(row=1, column=1)
        tk.Button(self.root, text="浏览", command=lambda: self.select_file(self.thermal_entry, "热成像")).grid(row=1, column=2)

        tk.Label(self.root, text="选择输出目录").grid(row=2, column=0, padx=5, pady=5)
        self.output_entry = tk.Entry(self.root, width=40)
        self.output_entry.grid(row=2, column=1)
        tk.Button(self.root, text="浏览", command=self.select_output_dir).grid(row=2, column=2)

        self.save_var = tk.IntVar()
        tk.Checkbutton(self.root, text="保存处理后的视频", variable=self.save_var).grid(row=3, column=0, columnspan=3, pady=5)

        tk.Button(self.root, text="开始处理", command=self.process_videos).grid(row=4, column=0, columnspan=3, pady=10)

    def select_file(self, entry, video_type):
        path = filedialog.askopenfilename(title=f"选择{video_type}视频", filetypes=[("视频文件", "*.mp4 *.avi *.mov")])
        if path:
            entry.delete(0, tk.END)
            entry.insert(0, path)

    def select_output_dir(self):
        dir_path = filedialog.askdirectory(title="选择输出目录")
        if dir_path:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, dir_path)

    def process_videos(self):
        self.vis_video_path = self.vis_entry.get()
        self.thermal_video_path = self.thermal_entry.get()
        self.output_dir = self.output_entry.get()
        self.is_saving = bool(self.save_var.get())

        if not all([self.vis_video_path, self.thermal_video_path, self.output_dir]):
            messagebox.showerror("错误", "请确保选择所有视频文件和输出目录！")
            return

        try:
            # Step 1: Time Alignment
            matches = find_max_overlap(self.vis_video_path, self.thermal_video_path)
            vis_indices = [m[0] for m in matches]
            thermal_indices = [m[1] for m in matches]
            time_aligned_vis = os.path.join(self.output_dir, "time_aligned_vis.mp4")
            time_aligned_thermal = os.path.join(self.output_dir, "time_aligned_thermal.mp4")
            trim_video(self.vis_video_path, vis_indices, time_aligned_vis)
            trim_video(self.thermal_video_path, thermal_indices, time_aligned_thermal)

            # Step 2: Spatial Alignment
            aligner = InfraredThermalAligner()
            cap_vis = cv2.VideoCapture(time_aligned_vis)
            cap_thermal = cv2.VideoCapture(time_aligned_thermal)
            ret_vis, frame_vis = cap_vis.read()
            ret_thermal, frame_thermal = cap_thermal.read()
            if not ret_vis or not ret_thermal:
                raise ValueError("无法读取时间对齐视频的首帧")
            gray_vis = cv2.cvtColor(frame_vis, cv2.COLOR_BGR2GRAY)
            gray_thermal = cv2.cvtColor(frame_thermal, cv2.COLOR_BGR2GRAY)
            aligned_thermal, H = aligner.align_images(gray_vis, gray_thermal)
            spatial_vis_out = os.path.join(self.output_dir, "spatial_aligned_vis.mp4")
            spatial_thermal_out = os.path.join(self.output_dir, "spatial_aligned_thermal.mp4")
            fps = cap_vis.get(cv2.CAP_PROP_FPS)
            frame_size = (gray_vis.shape[1], gray_vis.shape[0])
            total_frames = int(min(cap_vis.get(cv2.CAP_PROP_FRAME_COUNT), cap_thermal.get(cv2.CAP_PROP_FRAME_COUNT)))
            out_vis = cv2.VideoWriter(spatial_vis_out, cv2.VideoWriter_fourcc(*'mp4v'), fps, frame_size)
            out_thermal = cv2.VideoWriter(spatial_thermal_out, cv2.VideoWriter_fourcc(*'mp4v'), fps, frame_size)
            for _ in tqdm(range(total_frames), desc="空间对齐"):
                ret_vis, frame_vis = cap_vis.read()
                ret_thermal, frame_thermal = cap_thermal.read()
                if not ret_vis or not ret_thermal:
                    break
                gray_thermal = cv2.cvtColor(frame_thermal, cv2.COLOR_BGR2GRAY) if len(frame_thermal.shape) == 3 else frame_thermal
                aligned_frame_thermal = cv2.warpPerspective(gray_thermal, H, frame_size)
                aligned_thermal_bgr = cv2.cvtColor(aligned_frame_thermal, cv2.COLOR_GRAY2BGR)
                out_vis.write(frame_vis)
                out_thermal.write(aligned_thermal_bgr)
            cap_vis.release()
            cap_thermal.release()
            out_vis.release()
            out_thermal.release()

            # Step 3: Dehaze
            cap = cv2.VideoCapture(spatial_vis_out)
            dehazed_out = os.path.join(self.output_dir, "dehazed_vis.mp4")
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            out = cv2.VideoWriter(dehazed_out, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
            for _ in tqdm(range(total_frames), desc="去烟处理"):
                ret, frame = cap.read()
                if not ret:
                    break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray_norm = gray.astype(np.float32) / 255.0
                mask = threshold_mask(gray_norm)
                dehazed = contrast_guided_dehaze(gray_norm, mask)
                output_frame = cv2.cvtColor(dehazed, cv2.COLOR_GRAY2BGR)
                out.write(output_frame)
            cap.release()
            out.release()

            # Step 4: Multimodal Fusion
            model = YOLOv4TinyFusion().to(device)
            if os.path.exists("fusion_model.pth"):
                model.load_state_dict(torch.load("fusion_model.pth", map_location=device))
            fused_out = os.path.join(self.output_dir, "fused_video.mp4")
            vis_cap = cv2.VideoCapture(dehazed_out)
            thermal_cap = cv2.VideoCapture(spatial_thermal_out)
            fps = vis_cap.get(cv2.CAP_PROP_FPS)
            frame_width, frame_height = 1920, 1080
            out_writer = cv2.VideoWriter(fused_out, cv2.VideoWriter_fourcc(*'mp4v'), fps, (frame_width, frame_height))
            total_frames = int(min(vis_cap.get(cv2.CAP_PROP_FRAME_COUNT), thermal_cap.get(cv2.CAP_PROP_FRAME_COUNT)))
            for _ in tqdm(range(total_frames), desc="多模态融合"):
                ret_vis, vis_frame = vis_cap.read()
                ret_thermal, thermal_frame = thermal_cap.read()
                if not ret_vis or not ret_thermal:
                    break
                fused_frame = fuse_frame(model, vis_frame, thermal_frame, device)
                out_writer.write(fused_frame)
            vis_cap.release()
            thermal_cap.release()
            out_writer.release()

            # Step 5: Person Detection and Real-time Display
            detection_model = RTDETR('rtdetr-l.pt').to(device)
            cap = cv2.VideoCapture(fused_out)
            if self.is_saving:
                detected_out = os.path.join(self.output_dir, "detected_video.mp4")
                out = cv2.VideoWriter(detected_out, cv2.VideoWriter_fourcc(*'mp4v'), fps, (frame_width, frame_height))
            else:
                out = None
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                processed_frame = detect_persons(detection_model, frame.copy())
                if out:
                    out.write(processed_frame)
                cv2.imshow("处理结果", processed_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            cap.release()
            if out:
                out.release()
            cv2.destroyAllWindows()
            messagebox.showinfo("完成", "视频处理完成！")

        except Exception as e:
            messagebox.showerror("错误", f"处理失败: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoProcessor(root)
    root.mainloop()