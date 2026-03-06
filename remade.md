# 浓烟环境下可见光与热成像多模态人体识别系统

**Smoke-Human-Detection** · 第十六届服务外包创新创业大赛国二作品 Demo · 中电海康命题（A25）

[![GitHub](https://img.shields.io/badge/GitHub-XoomitLXH-181717?logo=github)](https://github.com/XoomitLXH)

---

## 项目简介

本仓库为**第十六届中国大学生服务外包创新创业大赛**国家级二等奖作品演示项目，面向**中电海康**「浓烟人体识别」命题。系统在浓烟、低可见度场景下，融合**可见光**与**热成像**双路视频，实现时间对齐、空间配准、去烟增强、多模态融合与人体检测的完整流程，为应急救援与安防监控提供可用的算法 Demo。

### 主要功能

| 模块 | 说明 |
|------|------|
| **时间对齐** | 基于光流运动特征与动态规划，对双路视频做时间轴对齐，提取重合片段 |
| **空间对齐** | 基于 SuperPoint + SuperGlue 特征匹配与单应变换，实现可见光与热成像的像素级配准 |
| **去烟雾** | 对比度引导的去雾算法（引导滤波 + 透射图估计），提升可见光在烟尘下的可辨识度 |
| **多模态融合** | 可见光 + 热成像双分支 CNN 融合（类 YOLOv4-Tiny 结构），输出增强后的融合图像 |
| **人体检测** | 基于 RT-DETR 的实时人体检测，支持视频/实时流与结果保存 |

### 技术栈

- **深度学习**: PyTorch、Ultralytics（YOLO/RT-DETR）
- **图像处理**: OpenCV、NumPy、SciPy、PyWavelets
- **特征匹配**: SuperPoint、SuperGlue（`models/`）
- **界面**: Tkinter（单功能脚本）、PySide6（主界面「明眸视觉」）

---

## 项目结构

```
├── README.md                 # 说明文件
├── requirements.txt          # Python 依赖
├── UI_2.py                   # 主界面：明眸视觉 - 浓烟人体识别系统（PySide6）
├── integration.py            # 一键流程：时间对齐→空间对齐→去烟→融合→人体检测（Tkinter）
├── time_alignment.py         # 时间对齐：双路视频重合段查找与裁剪
├── spatial_alignment.py      # 空间对齐：可见光/热成像配准（SuperPoint+SuperGlue）
├── dehaze.py                 # 去烟雾：对比度引导去雾
├── smoke_detection.py        # 烟雾检测（YOLO）
├── smoke_removal.py          # 烟雾去除与人体检测联合流程
├── person_detection.py       # 人体检测演示（RT-DETR）
├── multimodal_fusion.py      # 可见光+热成像多模态融合
├── video_cut.py              # 视频裁剪工具
├── models/                   # 特征匹配与模型工具
│   ├── superpoint.py         # SuperPoint 特征提取
│   ├── superglue.py          # SuperGlue 特征匹配
│   ├── matching.py           # 匹配与配准封装
│   └── utils.py              # 通用工具
└── .gitignore                # Git 忽略配置
```

---

## 环境要求

- **Python**: 3.8+
- **CUDA**（可选）: 用于 GPU 加速推理

---

## 安装与运行

### 1. 克隆仓库

```bash
git clone https://github.com/XoomitLXH/Smoke-Human-Detection.git
cd Smoke-Human-Detection
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行方式

**方式一：主界面（推荐）**  
启动「明眸视觉」主界面，可分别进入时间空间对齐、多模态融合、去烟雾、烟雾/人体识别、集成化等入口：

```bash
python UI_2.py
```

**方式二：集成流程（Tkinter）**  
选择可见光视频、热成像视频与输出目录后，自动完成：时间对齐 → 空间对齐 → 去烟 → 多模态融合 → 人体检测：

```bash
python integration.py
```

**方式三：单功能脚本**

- 时间对齐：`python time_alignment.py`
- 空间对齐：`python spatial_alignment.py`
- 去烟雾：`python dehaze.py`
- 多模态融合：`python multimodal_fusion.py`
- 人体检测：`python person_detection.py`
- 烟雾检测：`python smoke_detection.py`
- 烟雾去除+人体检测：`python smoke_removal.py`

---

## 使用说明

1. **双路视频**：请准备**同一场景、时间上大致重合**的可见光视频与热成像视频（格式如 mp4/avi 等）。
2. **模型权重**：  
   - RT-DETR 人体检测会通过 Ultralytics 自动下载 `rtdetr-l.pt`。  
   - 融合模型若使用预训练权重，请将 `fusion_model.pth` 放在项目根目录，`integration.py` 会自动加载。
3. **SuperPoint/SuperGlue**：空间对齐使用 `models` 下代码，如需使用官方权重，请按 `models/` 内说明放置权重文件。

---

## 赛事与命题信息

- **赛事**: 第十六届中国大学生服务外包创新创业大赛  
- **奖项**: 国家级二等奖  
- **命题**: 中电海康（A25）· 浓烟人体识别  
- **作品**: 浓烟环境下可见光与热成像多模态人体识别系统  

---

## 作者与仓库

- **GitHub**: [XoomitLXH](https://github.com/XoomitLXH)  
- **仓库**: [Smoke-Human-Detection](https://github.com/XoomitLXH/Smoke-Human-Detection)

仅供学习与竞赛交流使用，请勿用于商业目的。

---

## 许可证

本项目为竞赛作品 Demo，使用与再分发请遵守赛事规定及院校要求。
