import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from ultralytics import RTDETR
import cv2
import os
import torch
import numpy as np
from datetime import datetime


class VideoPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("RT-DETR 人体检测实时演示")
        self.video_path = ""
        self.output_dir = ""
        self.cap = None
        self.model = None
        self.is_playing = False
        self.is_saving = False
        self.delay = 10  # ms
        self.confidence_threshold = 0.5
        self.iou_threshold = 0.45
        self.video_writer = None

        # 创建界面
        self.create_widgets()

    def create_widgets(self):
        """创建界面组件"""
        # 控制面板
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=10)

        # 文件选择按钮
        self.btn_open = tk.Button(
            control_frame,
            text="选择视频文件",
            command=self.open_video,
            width=15
        )
        self.btn_open.pack(side=tk.LEFT, padx=5)

        # 输出文件夹按钮
        self.btn_output = tk.Button(
            control_frame,
            text="选择输出文件夹",
            command=self.select_output_dir,
            width=15
        )
        self.btn_output.pack(side=tk.LEFT, padx=5)

        # 置信度阈值
        tk.Label(control_frame, text="置信度阈值:").pack(side=tk.LEFT, padx=5)
        self.conf_entry = tk.Entry(control_frame, width=5)
        self.conf_entry.insert(0, "0.5")
        self.conf_entry.pack(side=tk.LEFT, padx=5)

        # IOU阈值
        tk.Label(control_frame, text="IOU阈值:").pack(side=tk.LEFT, padx=5)
        self.iou_entry = tk.Entry(control_frame, width=5)
        self.iou_entry.insert(0, "0.45")
        self.iou_entry.pack(side=tk.LEFT, padx=5)

        # 播放/暂停按钮
        self.btn_play = tk.Button(
            control_frame,
            text="播放",
            command=self.toggle_play,
            state=tk.DISABLED,
            width=10
        )
        self.btn_play.pack(side=tk.LEFT, padx=5)

        # 保存视频复选框
        self.save_var = tk.IntVar()
        self.save_check = tk.Checkbutton(
            control_frame,
            text="保存处理后的视频",
            variable=self.save_var,
            command=self.toggle_saving
        )
        self.save_check.pack(side=tk.LEFT, padx=5)

        # 视频显示区域
        self.video_label = tk.Label(self.root)
        self.video_label.pack()

        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("准备就绪")
        tk.Label(
            self.root,
            textvariable=self.status_var,
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W
        ).pack(fill=tk.X)

    def open_video(self):
        """打开视频文件"""
        file_path = filedialog.askopenfilename(
            filetypes=[("视频文件", "*.mp4 *.avi *.mov")]
        )
        if file_path:
            self.video_path = file_path
            self.status_var.set(f"已加载: {os.path.basename(file_path)}")

            # 初始化模型
            if self.model is None:
                self.model = RTDETR('rtdetr-l.pt').to(
                    'cuda' if torch.cuda.is_available() else 'cpu'
                )

            # 启用播放按钮
            self.btn_play.config(state=tk.NORMAL)

    def select_output_dir(self):
        """选择输出文件夹"""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.output_dir = dir_path
            self.status_var.set(f"输出文件夹: {dir_path}")

    def toggle_saving(self):
        """切换保存视频状态"""
        self.is_saving = bool(self.save_var.get())
        if self.is_saving and not self.output_dir:
            messagebox.showwarning("警告", "请先选择输出文件夹")
            self.save_var.set(0)
            self.is_saving = False

    def toggle_play(self):
        """切换播放/暂停状态"""
        if not self.is_playing:
            self.play_video()
            self.btn_play.config(text="暂停")
        else:
            self.pause_video()
            self.btn_play.config(text="播放")
        self.is_playing = not self.is_playing

    def play_video(self):
        """播放视频"""
        if not hasattr(self, 'cap') or self.cap is None:
            self.cap = cv2.VideoCapture(self.video_path)

            # 初始化视频写入器
            if self.is_saving and self.output_dir:
                fps = self.cap.get(cv2.CAP_PROP_FPS)
                width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                # 生成输出文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                input_name = os.path.splitext(os.path.basename(self.video_path))[0]
                output_name = f"{input_name}_detected_{timestamp}.mp4"
                output_path = os.path.join(self.output_dir, output_name)

                # 创建视频写入器
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                self.video_writer = cv2.VideoWriter(
                    output_path, fourcc, fps, (width, height)
                )
                self.status_var.set(f"正在保存到: {output_path}")

        self.update_frame()

    def pause_video(self):
        """暂停视频"""
        if hasattr(self, 'after_id'):
            self.root.after_cancel(self.after_id)

    def update_frame(self):
        """更新视频帧"""
        ret, frame = self.cap.read()
        if ret:
            try:
                self.confidence_threshold = float(self.conf_entry.get())
                self.iou_threshold = float(self.iou_entry.get())
            except ValueError:
                self.confidence_threshold = 0.5
                self.iou_threshold = 0.45
                self.conf_entry.delete(0, tk.END)
                self.conf_entry.insert(0, "0.5")
                self.iou_entry.delete(0, tk.END)
                self.iou_entry.insert(0, "0.5")
                messagebox.showerror("输入错误", "请输入有效的阈值(0-1之间的小数)")

            # 检测人体
            processed_frame = self.detect_persons(frame.copy())

            # 保存处理后的帧
            if self.is_saving and self.video_writer is not None:
                self.video_writer.write(processed_frame)

            # 显示帧
            display_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            img = tk.PhotoImage(data=cv2.imencode('.png', display_frame)[1].tobytes())
            self.video_label.config(image=img)
            self.video_label.image = img

            # 继续播放
            self.after_id = self.root.after(self.delay, self.update_frame)
        else:
            # 视频结束
            self.cap.release()
            self.cap = None
            self.is_playing = False
            self.btn_play.config(text="播放", state=tk.NORMAL)

            # 关闭视频写入器
            if self.video_writer is not None:
                self.video_writer.release()
                self.video_writer = None
                if self.is_saving:
                    self.status_var.set(f"视频已保存到: {self.output_dir}")
            else:
                self.status_var.set("播放完成")

    def detect_persons(self, frame):
        """使用RT-DETR检测人体"""
        results = self.model(
            frame,
            conf=self.confidence_threshold,
            iou=self.iou_threshold
        )
        result = results[0]

        for box in result.boxes:
            if int(box.cls[0]) == 0:  # 0表示人体
                confidence = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                # 绘制检测框
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # 显示置信度
                label = f"Person: {confidence:.2f}"
                (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                cv2.rectangle(frame, (x1, y1 - 20), (x1 + w, y1), (0, 255, 0), -1)
                cv2.putText(frame, label, (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)

        return frame

    def on_closing(self):
        """窗口关闭时释放资源"""
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()
        if hasattr(self, 'video_writer') and self.video_writer is not None:
            self.video_writer.release()
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app = VideoPlayer(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()