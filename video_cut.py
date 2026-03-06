import cv2
import os
import tkinter as tk
from tkinter import filedialog

def process_ir_video(input_video_path, output_video_path):
    """
    处理IR视频：缩放为704x419，然后水平裁剪为640x419。
    """
    cap = cv2.VideoCapture(input_video_path)
    if not cap.isOpened():
        print(f"无法打开视频文件: {input_video_path}")
        return

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    output_width, output_height = 640, 419
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (output_width, output_height))

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        resized_frame = cv2.resize(frame, (704, 419), cv2.INTER_AREA)
        cropped_frame = resized_frame[:, 32:672]

        if cropped_frame.shape[:2] != (output_height, output_width):
            print(f"裁剪后的帧尺寸不匹配: {cropped_frame.shape}")
            continue

        out.write(cropped_frame)

    cap.release()
    out.release()
    print(f"IR视频处理完成: {output_video_path}")

def process_thermal_video(input_video_path, output_video_path):
    """
    处理Thermal视频：缩放为640x419，并加速1.2倍(通过跳帧实现)
    但保持原始帧率不变。
    """
    cap = cv2.VideoCapture(input_video_path)
    if not cap.isOpened():
        print(f"无法打开视频文件: {input_video_path}")
        return

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    output_width, output_height = 640, 419
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (output_width, output_height))

    # 加速参数
    speed_factor = 1.2
    frame_counter = 0
    frame_interval = 1.0 / speed_factor

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 根据加速因子决定是否写入当前帧
        if frame_counter % speed_factor < 1.0:
            resized_frame = cv2.resize(frame, (output_width, output_height), cv2.INTER_AREA)
            out.write(resized_frame)

        frame_counter += 1

    cap.release()
    out.release()
    print(f"Thermal视频处理完成(加速{speed_factor}倍): {output_video_path}")

def select_input_file(title):
    """选择输入视频文件"""
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    file_path = filedialog.askopenfilename(
        title=title,
        filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv")]
    )
    root.destroy()
    return file_path

def select_output_file(title, default_extension=".mp4"):
    """选择输出视频文件路径"""
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    file_path = filedialog.asksaveasfilename(
        title=title,
        defaultextension=default_extension,
        filetypes=[("MP4文件", "*.mp4")]
    )
    root.destroy()
    return file_path

def main():
    # 选择IR视频输入和输出路径
    ir_input_path = select_input_file("选择IR输入视频")
    if not ir_input_path:
        print("❌ 未选择IR输入视频")
        return

    ir_output_path = select_output_file("保存处理后的IR视频")
    if not ir_output_path:
        print("❌ 未选择IR输出路径")
        return

    # 确保IR输出目录存在
    os.makedirs(os.path.dirname(ir_output_path), exist_ok=True)

    # 选择Thermal视频输入和输出路径
    thermal_input_path = select_input_file("选择Thermal输入视频")
    if not thermal_input_path:
        print("❌ 未选择Thermal输入视频")
        return

    thermal_output_path = select_output_file("保存处理后的Thermal视频")
    if not thermal_output_path:
        print("❌ 未选择Thermal输出路径")
        return

    # 确保Thermal输出目录存在
    os.makedirs(os.path.dirname(thermal_output_path), exist_ok=True)

    # 处理视频
    process_ir_video(ir_input_path, ir_output_path)
    process_thermal_video(thermal_input_path, thermal_output_path)

if __name__ == "__main__":
    main()