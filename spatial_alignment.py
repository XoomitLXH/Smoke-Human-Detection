import os
import sys
import cv2
import numpy as np
import torch
import tkinter as tk
from tkinter import filedialog, simpledialog

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models.superpoint import SuperPoint
from models.superglue import SuperGlue

def select_input_file(title):
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(title=title, filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv")])
    root.destroy()
    return path

def select_output_folder(title):
    root = tk.Tk()
    root.withdraw()
    folder = filedialog.askdirectory(title=title)
    root.destroy()
    return folder

class InfraredThermalAligner:
    def __init__(self, device='cuda' if torch.cuda.is_available() else 'cpu'):
        self.device = device
        self.superpoint_config = {
            'nms_radius': 4,
            'keypoint_threshold': 0.005,
            'max_keypoints': 1024
        }
        self.superglue_config = {
            'weights': 'indoor',
            'sinkhorn_iterations': 20,
            'match_threshold': 0.2,
            'descriptor_dim': 256,
            'GNN_layers': ['self', 'cross'] * 9
        }
        self.superpoint = SuperPoint(self.superpoint_config).eval().to(self.device)
        self.superglue = SuperGlue(self.superglue_config).eval().to(self.device)

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
            return aligned_th, H, (kpts_ir, kpts_th[mask.ravel() == 1])
        else:
            raise ValueError(f"匹配点不足: {len(kpts_ir)} < {min_matches}")

def main():
    video_path_ir = select_input_file("选择可见光视频")
    if not video_path_ir:
        print("未选择可见光视频")
        return

    video_path_th = select_input_file("选择热成像视频")
    if not video_path_th:
        print("未选择热成像视频")
        return

    cap_ir = cv2.VideoCapture(video_path_ir)
    cap_th = cv2.VideoCapture(video_path_th)

    ret_ir, frame_ir = cap_ir.read()
    ret_th, frame_th = cap_th.read()
    if not ret_ir or not ret_th:
        print("无法读取第一帧")
        return

    cv2.imwrite('frame_ir.jpg', frame_ir)
    cv2.imwrite('frame_th.jpg', frame_th)
    cap_ir.release()
    cap_th.release()

    aligner = InfraredThermalAligner()
    ir_img = cv2.imread('frame_ir.jpg', cv2.IMREAD_GRAYSCALE)
    th_img = cv2.imread('frame_th.jpg', cv2.IMREAD_GRAYSCALE)

    try:
        aligned_th, H, matches = aligner.align_images(ir_img, th_img)

        output_dir = select_output_folder("选择输出视频文件夹")
        if not output_dir:
            print("未选择输出文件夹")
            return

        root = tk.Tk()
        root.withdraw()
        visible_name = simpledialog.askstring("可见光视频命名", "请输入可见光输出视频文件名（不含扩展名）:")
        thermal_name = simpledialog.askstring("热成像视频命名", "请输入热成像输出视频文件名（不含扩展名）:")
        root.destroy()

        output_path_ir = os.path.join(output_dir, f"{visible_name}.mp4")
        output_path_th = os.path.join(output_dir, f"{thermal_name}.mp4")

        cap_ir = cv2.VideoCapture(video_path_ir)
        cap_th = cv2.VideoCapture(video_path_th)
        fps = cap_th.get(cv2.CAP_PROP_FPS)
        frame_size = (ir_img.shape[1], ir_img.shape[0])
        total_frames = int(min(cap_ir.get(cv2.CAP_PROP_FRAME_COUNT), cap_th.get(cv2.CAP_PROP_FRAME_COUNT)))

        out_ir = cv2.VideoWriter(output_path_ir, cv2.VideoWriter_fourcc(*'mp4v'), fps, frame_size)
        out_th = cv2.VideoWriter(output_path_th, cv2.VideoWriter_fourcc(*'mp4v'), fps, frame_size)

        print("按'q'键可提前退出视频显示和处理")

        for i in range(total_frames):
            ret_ir, frame_ir = cap_ir.read()
            ret_th, frame_th = cap_th.read()
            if not ret_ir or not ret_th:
                break

            if len(frame_th.shape) == 3:
                frame_th_gray = cv2.cvtColor(frame_th, cv2.COLOR_BGR2GRAY)
            else:
                frame_th_gray = frame_th

            aligned_frame_th_gray = cv2.warpPerspective(frame_th_gray, H, frame_size)
            aligned_frame_th = cv2.cvtColor(aligned_frame_th_gray, cv2.COLOR_GRAY2BGR)

            out_ir.write(frame_ir)
            out_th.write(aligned_frame_th)

            # 拼接两帧图像（水平拼接）
            combined = np.hstack((frame_ir, aligned_frame_th))

            cv2.imshow('可见光和对齐后的热成像视频（按q退出）', combined)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("用户中断，退出显示")
                break

            if i % 100 == 0:
                print(f"已处理 {i}/{total_frames} 帧")

        cap_ir.release()
        cap_th.release()
        out_ir.release()
        out_th.release()
        cv2.destroyAllWindows()

        print(f"✅ 可见光视频保存至: {output_path_ir}")
        print(f"✅ 热成像视频保存至: {output_path_th}")

    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    main()
