import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, simpledialog
from tkinter import ttk
from PIL import Image, ImageTk
import os
from scipy.spatial.distance import cdist


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
    timestamps = [i / fps for i in range(frame_count)]
    return timestamps


def find_max_overlap(video1_path, video2_path, threshold=0.1, tolerance=2):
    cap1 = cv2.VideoCapture(video1_path)
    cap2 = cv2.VideoCapture(video2_path)

    if not cap1.isOpened() or not cap2.isOpened():
        print("错误：无法打开视频文件！")
        return []

    timestamps1 = get_frame_timestamps(cap1)
    timestamps2 = get_frame_timestamps(cap2)

    features1 = []
    frames1 = []
    ret, prev_frame = cap1.read()
    if not ret:
        print("错误：视频1首帧读取失败")
        return []
    frames1.append(prev_frame)
    while cap1.isOpened():
        ret, curr_frame = cap1.read()
        if not ret:
            break
        frames1.append(curr_frame)
        features1.append(extract_motion_features(prev_frame, curr_frame))
        prev_frame = curr_frame.copy()

    features2 = []
    frames2 = []
    ret, prev_frame = cap2.read()
    if not ret:
        print("错误：视频2首帧读取失败")
        return []
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
        print("未找到连续重合段")
        return []

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


def play_videos_in_tkinter(video1_path, video2_path):
    window = tk.Toplevel()
    window.title("对齐后视频播放")

    label = ttk.Label(window)
    label.pack()

    cap1 = cv2.VideoCapture(video1_path)
    cap2 = cv2.VideoCapture(video2_path)

    def update():
        ret1, frame1 = cap1.read()
        ret2, frame2 = cap2.read()

        if not ret1 or not ret2:
            cap1.release()
            cap2.release()
            return

        h = min(frame1.shape[0], frame2.shape[0])
        w = min(frame1.shape[1], frame2.shape[1])
        frame1 = cv2.resize(frame1, (w, h))
        frame2 = cv2.resize(frame2, (w, h))
        combined = np.hstack((frame1, frame2))
        combined_rgb = cv2.cvtColor(combined, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(combined_rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        label.imgtk = imgtk
        label.config(image=imgtk)
        window.after(40, update)  # 约25fps

    update()
    window.mainloop()


def main():
    root = tk.Tk()
    root.withdraw()

    video1_path = filedialog.askopenfilename(title="选择第一个视频", filetypes=[("视频文件", "*.mp4 *.avi *.mov")])
    video2_path = filedialog.askopenfilename(title="选择第二个视频", filetypes=[("视频文件", "*.mp4 *.avi *.mov")])
    output_dir = filedialog.askdirectory(title="选择输出文件夹")

    output_name1 = simpledialog.askstring("输入", "请输入第一个输出视频的名称（不含扩展名）：", initialvalue="trimmed_video1")
    output_name2 = simpledialog.askstring("输入", "请输入第二个输出视频的名称（不含扩展名）：", initialvalue="trimmed_video2")
    threshold = simpledialog.askfloat("输入", "请输入相似度阈值（0-1，建议0.8-0.95）：", initialvalue=0.9, minvalue=0.0, maxvalue=1.0)

    print("正在分析视频内容...")
    matches = find_max_overlap(video1_path, video2_path, threshold=threshold)

    if not matches:
        print("未找到时间重合部分")
        return

    video1_indices = [m[0] for m in matches]
    video2_indices = [m[1] for m in matches]

    output1 = os.path.join(output_dir, f"{output_name1}.mp4")
    output2 = os.path.join(output_dir, f"{output_name2}.mp4")

    print(f"找到重合段：{len(matches)}帧")
    trim_video(video1_path, video1_indices, output1, target_fps=25)
    trim_video(video2_path, video2_indices, output2, target_fps=25)

    print(f"处理完成！结果保存至：\n{output1}\n{output2}")
    play_videos_in_tkinter(output1, output2)


if __name__ == "__main__":
    main()
