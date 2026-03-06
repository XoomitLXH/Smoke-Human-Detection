import os
import cv2
import numpy as np
from tkinter import Tk, messagebox
from tkinter.filedialog import askopenfilename, asksaveasfilename
from ultralytics import YOLO, RTDETR
import tkinter as tk
from tkinter import filedialog
import pywt
from tqdm import tqdm
import time


# 实现引导滤波（Guided Filter）
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

    q = mean_a * I + mean_b
    return q


# 对比度引导去烟算法
def contrast_guided_dehaze(img, mask, t0=0.3, r=60, eps=1e-3):
    img = np.clip(img, 0, 1)
    masked_img = img * mask
    flat_masked = masked_img[mask > 0]
    if len(flat_masked) > 0:
        A = np.percentile(flat_masked, 90)
    else:
        A = np.percentile(img, 90)
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
    result = np.clip(result * 1.3, 0, 255).astype(np.uint8)
    result = result.astype(np.float32) / 255.0
    return result


def threshold_mask(img, threshold=0.6):
    mask = (img > threshold).astype(np.float32)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=2)
    return mask


def dark_channel_prior_dehaze(image):
    kernel = np.ones((15, 15), np.uint8)
    dark_channel = cv2.erode(image, kernel)
    flat = dark_channel.flatten()
    num_pixels = int(0.005 * flat.size)
    A = np.mean(np.sort(flat)[-num_pixels:])
    t = 1 - 0.90 * (dark_channel / A)
    t = np.clip(t, 0.1, 1.0)
    dehazed = (image.astype(float) - A) / t + A
    dehazed = np.clip(dehazed, 0, 255).astype(np.uint8)
    return dehazed


def enhance_contrast_and_edges(image):
    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
    contrast_enhanced = clahe.apply(image)
    bilateral_filtered = cv2.bilateralFilter(contrast_enhanced, d=9, sigmaColor=250, sigmaSpace=300)
    edges = cv2.subtract(contrast_enhanced, bilateral_filtered)
    sharpened = cv2.addWeighted(contrast_enhanced, 0.8, edges, 0.3, 0)
    return sharpened


def post_process(image):
    bilateral_filtered = cv2.bilateralFilter(image, d=9, sigmaColor=250, sigmaSpace=300)
    coeffs = pywt.wavedec2(bilateral_filtered, 'db4', level=3)
    threshold = 0.2 * np.median(np.abs(coeffs[1][0]))
    coeffs_thresh = [coeffs[0]]
    for subband in coeffs[1:]:
        subband_thresh = tuple([pywt.threshold(subsubband, threshold, mode='soft') for subsubband in subband])
        coeffs_thresh.append(subband_thresh)
    denoised = pywt.waverec2(coeffs_thresh, 'db4')
    denoised = np.clip(denoised, 0, 255).astype(np.uint8)
    median_filtered = cv2.medianBlur(denoised, 5)
    kernel = np.ones((3, 3), np.uint8)
    opening = cv2.morphologyEx(median_filtered, cv2.MORPH_OPEN, kernel, iterations=2)
    return opening


def feather_and_blur(processed_roi, original_roi):
    height, width = processed_roi.shape
    mask = np.ones((height, width), dtype=np.float32)

    center_y, center_x = height / 2, width / 2
    for i in range(height):
        for j in range(width):
            dist_y = abs(i - center_y) / center_y
            dist_x = abs(j - center_x) / center_x
            mask[i, j] = 0.5 * (1 + np.cos(np.pi * max(dist_x, dist_y)))

    max_mask = mask.max()
    if max_mask == 0:
        max_mask = 1e-8
    mask = mask / max_mask

    original_float = original_roi.astype(np.float32) / 255.0
    processed_float = processed_roi.astype(np.float32) / 255.0
    blended = processed_float * mask + original_float * (1 - mask)
    blended = np.nan_to_num(blended, nan=0, posinf=255, neginf=0)
    blended = (blended * 255).astype(np.uint8)
    return blended


def select_file(title, filetypes):
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title=title, filetypes=filetypes)
    root.destroy()
    return file_path if file_path else None


def select_save_file(title, filetypes, defaultextension):
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.asksaveasfilename(title=title, filetypes=filetypes, defaultextension=defaultextension)
    root.destroy()
    return file_path if file_path else None


def main():
    root = Tk()
    root.withdraw()

    # 直接使用预定义模型路径
    MODEL_PATH = "smoke_detect.pt"
    HUMAN_MODEL_PATH = "rtdetr-l.pt"

    # 检查模型文件是否存在
    if not os.path.exists(MODEL_PATH):
        print(f"❌ 烟雾检测模型文件不存在: {MODEL_PATH}")
        return
    if not os.path.exists(HUMAN_MODEL_PATH):
        print(f"❌ 人体检测模型文件不存在: {HUMAN_MODEL_PATH}")
        return

    # 文件选择
    input_video = select_file("选择输入视频", [("视频文件", "*.mp4;*.avi;*.mov;*.mkv")])
    if not input_video:
        print("❌ 未选择输入视频")
        return

    output_video = select_save_file("保存输出视频", [("MP4文件", "*.mp4")], ".mp4")
    if not output_video:
        print("❌ 未选择输出路径")
        return

    # 询问是否显示实时处理
    show_realtime = messagebox.askyesno("实时显示", "是否要实时显示处理结果？")

    # 初始化模型
    try:
        model = YOLO(MODEL_PATH)
        human_model = RTDETR(HUMAN_MODEL_PATH)
        print(f"✅ 烟雾检测模型加载成功: {MODEL_PATH}")
        print(f"✅ 人体检测模型加载成功: {HUMAN_MODEL_PATH}")
    except Exception as e:
        print(f"❌ 模型加载失败: {str(e)}")
        return

    # 视频处理
    cap = cv2.VideoCapture(input_video)
    if not cap.isOpened():
        print("❌ 无法打开视频文件")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # 创建输出视频
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video, fourcc, fps, (width, height))

    # 创建实时显示窗口
    if show_realtime:
        cv2.namedWindow('烟雾检测实时处理', cv2.WINDOW_NORMAL)
        # 使用原始视频尺寸
        cv2.resizeWindow('烟雾检测实时处理', width, height)

    start_time = time.time()
    processed_frames = 0

    with tqdm(total=total_frames, desc="处理进度", unit="帧") as pbar:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # 全局去雾处理
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_normalized = gray.astype(np.float32) / 255.0
            mask = threshold_mask(gray_normalized)
            dehazed_gray = contrast_guided_dehaze(gray_normalized, mask)
            dehazed_gray = (dehazed_gray * 255).astype(np.uint8)

            # 烟雾检测
            results = model.predict(frame, conf=0.1, verbose=False)
            boxes = results[0].boxes.xyxy.cpu().numpy() if results[0].boxes else []

            # HSV处理
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv)
            modified_v = dehazed_gray.astype(np.float32) / 255.0

            # 区域处理
            for box in boxes:
                x1, y1, x2, y2 = map(int, box)
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(width - 1, x2), min(height - 1, y2)

                if x2 <= x1 or y2 <= y1:
                    continue

                try:
                    original_roi = v[y1:y2, x1:x2].copy()
                    roi_v = (modified_v[y1:y2, x1:x2] * 255).astype(np.uint8)
                    dehazed_roi = dark_channel_prior_dehaze(roi_v)
                    enhanced_roi = enhance_contrast_and_edges(dehazed_roi)
                    processed_roi = post_process(enhanced_roi)
                    processed_roi = cv2.resize(processed_roi, (x2 - x1, y2 - y1), interpolation=cv2.INTER_AREA)
                    blended_roi = feather_and_blur(processed_roi, original_roi)
                    modified_v[y1:y2, x1:x2] = blended_roi.astype(np.float32) / 255.0
                except Exception as e:
                    print(f"⚠️ 区域处理异常: {str(e)}")
                    continue

            # 合并输出
            modified_hsv = cv2.merge([h, s, (modified_v * 255).astype(np.uint8)])
            output_frame = cv2.cvtColor(modified_hsv, cv2.COLOR_HSV2BGR)

            # 人体检测
            human_results = human_model.predict(output_frame, conf=0.5, classes=[0], verbose=False)
            human_boxes = human_results[0].boxes.xyxy.cpu().numpy() if human_results[0].boxes else []

            # 绘制绿色检测框
            for box in human_boxes:
                x1, y1, x2, y2 = map(int, box)
                cv2.rectangle(output_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # 写入输出视频
            out.write(output_frame)
            processed_frames += 1

            # 实时显示
            if show_realtime:
                display_frame = cv2.resize(output_frame, (int(width * 2), int(height * 2)))
                cv2.imshow('烟雾检测实时处理', display_frame)

                # 按ESC退出实时显示
                if cv2.waitKey(1) == 27:
                    print("\n⏹ 用户中断了实时显示")
                    show_realtime = False
                    cv2.destroyAllWindows()
            pbar.update(1)

    # 释放资源
    cap.release()
    out.release()
    if show_realtime:
        cv2.destroyAllWindows()

    elapsed_time = time.time() - start_time
    avg_fps = processed_frames / elapsed_time if elapsed_time > 0 else 0

    print(f"\n✅ 处理完成！")
    print(f"📊 统计信息:")
    print(f"   - 总帧数: {processed_frames}")
    print(f"   - 总耗时: {elapsed_time:.2f}秒")
    print(f"   - 平均FPS: {avg_fps:.2f}")
    print(f"💾 保存路径: {os.path.abspath(output_video)}")


if __name__ == '__main__':
    main()