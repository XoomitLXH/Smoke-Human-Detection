import os
import cv2
import numpy as np
from tkinter import Tk
import tkinter as tk
from tkinter import filedialog
from tqdm import tqdm


# 引导滤波实现
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


# 对比度引导去雾算法
def contrast_guided_dehaze(img, mask, t0=0.3, r=60, eps=1e-3):
    img = np.clip(img, 0, 1)
    masked_img = img * mask

    # 估计大气光
    flat_masked = masked_img[mask > 0]
    A = np.percentile(flat_masked, 90) if len(flat_masked) > 0 else np.percentile(img, 90)
    A = max(A, 0.1)

    # 计算对比度图
    sobel_x = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=3)
    contrast = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
    contrast = np.clip(contrast, 0, 1)

    # 透射率估计与优化
    t_initial = 1 - contrast
    t_refined = guided_filter(img, t_initial, r=r, eps=eps)
    t_refined = np.maximum(t_refined, t0)

    # 图像复原
    J = (img - A) / t_refined + A
    J = np.clip(J, 0, 1)

    # 结果融合与增强
    result = J * mask + img * (1 - mask)
    result = (result * 255).astype(np.uint8)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    result = clahe.apply(result)
    return np.clip(result * 1.3, 0, 255).astype(np.uint8)


# 阈值掩码生成
def threshold_mask(img, threshold=0.6):
    mask = (img > threshold).astype(np.float32)
    kernel = np.ones((5, 5), np.uint8)
    return cv2.dilate(mask, kernel, iterations=2)


# 文件选择对话框
def select_file(title, filetypes):
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(title=title, filetypes=filetypes)
    root.destroy()
    return path


def select_save_file(title, filetypes, defaultextension):
    root = tk.Tk()
    root.withdraw()
    path = filedialog.asksaveasfilename(title=title, filetypes=filetypes, defaultextension=defaultextension)
    root.destroy()
    return path


def main():
    # 选择输入输出文件（单张图像）
    input_path = select_file("选择输入图像", [("图像文件", "*.png;*.jpg;*.jpeg;*.bmp")])
    if not input_path:
        print("❌ 未选择输入图像")
        return

    output_path = select_save_file("保存输出图像", [("PNG文件", "*.png"), ("JPEG文件", "*.jpg;*.jpeg")], ".png")
    if not output_path:
        print("❌ 未选择输出路径")
        return

    # 读取图像
    img_bgr = cv2.imread(input_path, cv2.IMREAD_COLOR)
    if img_bgr is None:
        print("❌ 无法读取图像文件")
        return

    height, width = img_bgr.shape[:2]

    # 设置预览窗口大小（放大两倍）
    preview_width = int(width * 2)
    preview_height = int(height * 2)

    # 创建预览窗口
    cv2.namedWindow('Dehazed Image', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Dehazed Image', preview_width, preview_height)

    # 灰度转换与归一化
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray_norm = gray.astype(np.float32) / 255.0

    # 生成掩码并去雾（在灰度域进行）
    mask = threshold_mask(gray_norm)
    dehazed = contrast_guided_dehaze(gray_norm, mask)

    # 恢复彩色：使用 HSV，将去雾后的结果作为亮度通道
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    hsv[..., 2] = dehazed  # 替换 V 通道
    output_img = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    # 预览显示
    preview_frame = cv2.resize(output_img, (preview_width, preview_height))
    cv2.imshow('Dehazed Image', preview_frame)
    cv2.waitKey(0)  # 任意键关闭

    # 保存结果
    ok = cv2.imwrite(output_path, output_img)
    cv2.destroyAllWindows()

    if ok:
        print(f"\n✅ 处理完成！保存路径: {os.path.abspath(output_path)}")
    else:
        print("❌ 保存失败，请检查路径或权限")


if __name__ == '__main__':
    main()