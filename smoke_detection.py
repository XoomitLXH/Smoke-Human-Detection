from ultralytics import YOLO
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import cv2
import time
import numpy as np
from tqdm import tqdm
import logging
from datetime import datetime

# 设置日志记录
logging.basicConfig(
    filename=f"smoke_detection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def select_file(title, filetypes):
    """选择文件并返回 Path 对象"""
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title=title, filetypes=filetypes)
    root.destroy()
    if not file_path:
        logging.warning("未选择文件")
        return None
    return Path(file_path)


def select_folder(title):
    """选择文件夹并返回 Path 对象"""
    root = tk.Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory(title=title)
    root.destroy()
    if not folder_path:
        logging.warning("未选择文件夹")
        return None
    return Path(folder_path)


def get_video_frames(video_path):
    """获取视频的总帧数"""
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            logging.error(f"无法打开视频文件: {video_path}")
            return 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        return total_frames
    except Exception as e:
        logging.error(f"读取视频帧数失败: {video_path}, 错误: {str(e)}")
        return 0


def process_video(model, video_path, output_dir, show_realtime=True):
    """处理单个视频文件并保存检测结果"""
    # 支持的视频格式
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.mpeg', '.mpg']
    if video_path.suffix.lower() not in video_extensions:
        print(f"❌ 不支持的视频格式：{video_path.suffix}（支持格式：{', '.join(video_extensions)}）")
        logging.warning(f"不支持的视频格式: {video_path.suffix}")
        return False

    # 创建结果保存目录
    results_dir = output_dir / f"detection_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    results_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🔍 正在处理视频: {video_path.name}")
    logging.info(f"开始处理视频: {video_path.name}")

    total_frames = get_video_frames(video_path)
    if total_frames == 0:
        print(f"⚠️ 无法读取视频：{video_path.name}")
        logging.warning(f"无法读取视频: {video_path.name}")
        return False

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"⚠️ 无法打开视频：{video_path.name}")
        logging.error(f"无法打开视频: {video_path.name}")
        return False

    fps = cap.get(cv2.CAP_PROP_FPS)
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"视频分辨率: {width}x{height}, FPS: {fps:.2f}")
    logging.info(f"视频分辨率: {width}x{height}, FPS: {fps:.2f}")

    # 输出视频路径
    output_video_path = results_dir / f"result_{video_path.stem}_{datetime.now().strftime('%H%M%S')}.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_video_path), fourcc, fps, (width, height))

    if not out.isOpened():
        print(f"⚠️ 无法创建输出视频文件：{output_video_path}")
        logging.error(f"无法创建输出视频文件: {output_video_path}")
        cap.release()
        return False

    current_frame, start_time = 0, time.time()

    # 创建实时显示窗口（调整为原始尺寸的80%）
    if show_realtime:
        window_name = 'Smoke Detection - Real Time (Press ESC to Exit)'
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        # 计算窗口大小（保持宽高比）
        display_width = int(width * 2)
        display_height = int(height * 2)
        cv2.resizeWindow(window_name, display_width, display_height)

    try:
        results = model.predict(
            source=str(video_path),
            stream=True,
            conf=0.1,
            imgsz=640,
            verbose=False
        )

        for result in tqdm(results, total=total_frames, desc="处理帧", unit="frame"):
            current_frame += 1
            frame = result.orig_img

            # 绘制检测框
            boxes = result.boxes.xyxy.cpu().numpy()
            confidences = result.boxes.conf.cpu().numpy()
            class_ids = result.boxes.cls.cpu().numpy()
            logging.info(f"帧 {current_frame}: 检测到 {len(boxes)} 个目标，类别: {class_ids}, 置信度: {confidences}")

            for box, conf, cls_id in zip(boxes, confidences, class_ids):
                if cls_id == 0:  # 假设烟雾 ID 为 0
                    x1, y1, x2, y2 = map(int, box)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    label = f"Smoke: {conf:.2f}"
                    cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            out.write(frame)

            # 实时显示（保持宽高比）
            if show_realtime:
                display_frame = cv2.resize(frame, (display_width, display_height))
                cv2.imshow(window_name, display_frame)

                # 按ESC退出
                if cv2.waitKey(1) == 27:
                    print("\n⏹ 用户中断了实时显示")
                    logging.info("用户中断了实时显示")
                    show_realtime = False
                    cv2.destroyAllWindows()

    except Exception as e:
        print(f"\n⚠️ 处理视频 {video_path.name} 时出错: {str(e)}")
        logging.error(f"处理视频 {video_path.name} 时出错: {str(e)}")
        cap.release()
        out.release()
        if show_realtime:
            cv2.destroyAllWindows()
        return False

    cap.release()
    out.release()
    if show_realtime:
        cv2.destroyAllWindows()

    elapsed_time = time.time() - start_time
    print(f"\n✅ 已完成 {video_path.name} (耗时: {elapsed_time:.1f}s)")
    logging.info(f"完成处理视频: {video_path.name}, 耗时: {elapsed_time:.1f}s")
    return True


def detect_smoke_video():
    """主函数：检测单个视频中的烟雾"""
    # 直接加载模型
    model_path = "smoke_detect.pt"  # 确保模型文件存在

    try:
        model = YOLO(model_path)
        print(f"✅ 已加载模型: smoke_detect.pt")
        logging.info(f"已加载模型: smoke_detect.pt")
    except Exception as e:
        print(f"❌ 模型加载失败: {str(e)}")
        logging.error(f"模型加载失败: {str(e)}")
        return

    video_path = select_file(
        "选择视频文件",
        [("视频文件", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.mpeg *.mpg"), ("所有文件", "*.*")]
    )
    if not video_path or not video_path.exists():
        print("❌ 未选择有效视频文件")
        logging.error("未选择有效视频文件")
        return

    output_dir = select_folder("选择结果输出目录")
    if not output_dir:
        print("❌ 未选择输出目录")
        logging.error("未选择输出目录")
        return

    # 询问用户是否要实时显示
    root = tk.Tk()
    root.withdraw()
    show_realtime = messagebox.askyesno("实时显示", "是否要实时显示处理结果？")
    root.destroy()

    if process_video(model, video_path, output_dir, show_realtime):
        print(f"\n🎉 视频处理完成！结果保存在：{output_dir}")
        logging.info(f"视频处理完成，结果保存在: {output_dir}")
    else:
        print("\n⚠️ 视频处理未完成，请检查日志")
        logging.warning("视频处理未完成")


if __name__ == '__main__':
    detect_smoke_video()