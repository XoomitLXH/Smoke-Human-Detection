import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton,
                                QWidget, QTextEdit,QStackedWidget,
                               QVBoxLayout, QHBoxLayout, QLabel, QGridLayout)
from PySide6.QtCore import QProcess, Qt, QTimer,QSize, QRect, QPoint
from PySide6.QtGui import QFont, QPixmap, QPainter, QIcon, QPen, QBrush, QPolygon, QColor

class MainWindow(QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('明眸视觉 - 浓烟人体识别系统')
        self.setGeometry(300, 300, 1200, 900)
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
        # 创建堆叠窗口
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # 初始化所有界面
        self.init_main_ui()
        self.init_sub_uis()

    def init_main_ui(self):
        """初始化主界面"""
        # 主部件设置
        main_widget = QWidget()
        #self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        #main_widget.setLayout(main_layout)
        # 设置背景图片
        self.background_image = os.path.join(os.path.dirname(__file__), "background.png")
        # ========== 标题栏 ==========
        title_container = QWidget()
        title_container.setStyleSheet("background-color: rgba(255, 255, 255, 0); border-radius: 10px;")
        title_container.setMinimumSize(800, 300)
        title_layout = QHBoxLayout(title_container)

        # Logo图片
        self.logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path).scaled(350, 350, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(pixmap)
        else:
            # 如果没有logo则显示默认图标
            self.logo_label.setText("LOGO")
            self.logo_label.setStyleSheet("font-size: 24px; color: #666;")
        self.logo_label.setAlignment(Qt.AlignCenter)

        # 系统标题
        title_label = QLabel("""
            <div style='text-align: center;'>
                <span style='font-size: 100px; font-weight: 900; color: #F5C77E; font-family: "华文行楷", sans-serif; letter-spacing: -15px;'>明眸“算”</span>
                <span style='font-size: 60px; font-weight: 700; color: #FFD38C; letter-spacing: -3px; margin-left: -100px;'>浓烟人体识别系统</span>
            </div>
        """)
        title_label.setAlignment(Qt.AlignCenter)

        # 标题栏布局
        title_layout.addStretch(1)
        title_layout.addWidget(self.logo_label)
        title_layout.addSpacing(0)
        title_layout.addWidget(title_label)
        title_layout.addStretch(1)
        main_layout.addWidget(title_container)
        main_layout.addSpacing(30)

        # ========== 功能按钮区 ==========
        # 主界面按钮
        buttons_container = QWidget()
        buttons_container.setStyleSheet("background-color: rgba(255, 255, 255, 0); border-radius: 10px; padding: 10px;")
        grid_layout = QGridLayout(buttons_container)

        # 创建四个主按钮
        main_buttons = [
            ("时间空间对齐", ("#FFFFFF", "#FFFFFF", "#FFFFFF")),
            ("多模态融合", ("#9F1F35", "#DC143C", "#FFB6C1")),
            ("去烟雾", ("#9F1F35", "#DC143C", "#FFB6C1")),
            ("烟雾/人体识别", ("#FFFFFF", "#FFFFFF", "#FFFFFF")),
            ("集成化",("#FFFFFF", "#FFFFFF", "#FFFFFF")),
            ("联系我们", ("#9F1F35", "#DC143C", "#FFB6C1"))
        ]

        for i, (text, (color_start, color_mid, color_end)) in enumerate(main_buttons):
            btn = QPushButton(text)
            btn.setFixedSize(160, 160)
            if text in ["时间空间对齐", "烟雾/人体识别", "集成化"]:
                btn.setStyleSheet(f"""
                       QPushButton {{
                           background: qlineargradient(
                               x1:0, y1:0, x2:1, y2:0, x3:2, y3:0,
                               stop:0 {color_start},
                               stop:1 {color_mid},
                               stop:2 {color_end}
                           );
                           color: #9F1F35;
                           border-radius: 10px;
                           border: 3px solid #F5F5F5;
                           padding: 12px;
                           font-size: 20px;
                           font-weight: 900;
                           font-family: "Microsoft YaHei";
                       }}
                       QPushButton:hover {{
                           background: qlineargradient(
                               x1:0, y1:0, x2:1, y2:0, x3:2, y3:0,
                               stop:0 {self.lighten_color(color_start)},
                               stop:1 {self.lighten_color(color_mid)},
                               stop:2 {self.lighten_color(color_end)}
                           );
                       }}
                       QPushButton:pressed {{
                           background: qlineargradient(
                               x1:0, y1:0, x2:1, y2:0, x3:2, y3:0,
                               stop:0 {self.darken_color(color_start)},
                               stop:1 {self.darken_color(color_mid)},
                               stop:2 {self.darken_color(color_end)}
                           );
                       }}
                   """)
            else:
                btn.setStyleSheet(f"""
                           QPushButton {{
                               background: qlineargradient(
                                   x1:0, y1:0, x2:1, y2:0, x3:2, y3:0,
                                   stop:0 {color_start},
                                   stop:1 {color_mid},
                                   stop:2 {color_end}
                               );
                               color: white;
                               border-radius: 10px;
                               padding: 12px;
                               font-size: 22px;
                               font-weight: bold;
                               font-family: "Microsoft YaHei";
                           }}
                           QPushButton:hover {{
                               background: qlineargradient(
                                   x1:0, y1:0, x2:1, y2:0, x3:2, y3:0,
                                   stop:0 {self.lighten_color(color_start)},
                                   stop:1 {self.lighten_color(color_mid)},
                                   stop:2 {self.lighten_color(color_end)}
                               );
                           }}
                           QPushButton:pressed {{
                               background: qlineargradient(
                                   x1:0, y1:0, x2:1, y2:0, x3:2, y3:0,
                                   stop:0 {self.darken_color(color_start)},
                                   stop:1 {self.darken_color(color_mid)},
                                   stop:2 {self.darken_color(color_end)}
                               );  
                           }}
                       """)

            btn.clicked.connect(lambda _, idx=i: self.stacked_widget.setCurrentIndex(idx + 1))
            grid_layout.addWidget(btn, i // 2, i % 2)

            grid_layout.setVerticalSpacing(20)  # 设置垂直间距

        main_layout.addWidget(buttons_container)
        main_layout.addStretch()

        # 添加到堆叠窗口
        self.stacked_widget.addWidget(main_widget)

    def paintEvent(self, event):
        """重绘事件，用于绘制背景"""
        painter = QPainter(self)
        # 检查背景图片是否存在
        if os.path.exists(self.background_image):
            pixmap = QPixmap(self.background_image)
            # 缩放图片以适应窗口大小
            painter.drawPixmap(self.rect(), pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            # 如果没有背景图片，使用默认背景色
            painter.fillRect(self.rect(), Qt.GlobalColor.lightGray)

    def lighten_color(self, hex_color, factor=0.2):
        """颜色变亮"""
        # 提取RGB分量（跳过#号）
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)

        # 计算变亮后的值
        light_r = min(int(r + (255 - r) * factor), 255)
        light_g = min(int(g + (255 - g) * factor), 255)
        light_b = min(int(b + (255 - b) * factor), 255)

        # 格式化为十六进制
        return f"#{light_r:02X}{light_g:02X}{light_b:02X}"

    def darken_color(self, hex_color, factor=0.2):
        """颜色变暗"""
        # 提取RGB分量
        r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))

        # 计算变暗后的值
        dark_r = max(int(r * (1 - factor)), 0)
        dark_g = max(int(g * (1 - factor)), 0)
        dark_b = max(int(b * (1 - factor)), 0)

        return f"#{dark_r:02X}{dark_g:02X}{dark_b:02X}"

    def init_sub_uis(self):
        """初始化四个子界面"""
        # 脚本映射关系
        script_mapping = {
            "视频裁切": "video_cut.py",
            "时间对齐模块": "time_alignment.py",
            "空间对齐模块": "spatial_alignment.py",
            "多模态融合模块": "multimodal_fusion.py",
            "烟雾识别模块": "smoke_detection.py",
            "去薄雾模块": "dehaze.py",
            "去火灾烟雾模块": "smoke_removal.py",
            "人体识别模块": "person_detection.py",
            "集成化模块": "integration.py"            
        }
        # 图标映射关系
        icon_mapping = {
            "视频裁切": "video_cut1.png",
            "时间对齐模块": "time_alignment1.png",
            "空间对齐模块": "spatial_alignment1.png",
            "多模态融合模块": "multimodal_fusion1.png",
            "烟雾识别模块": "smoke_detection1.png",
            "去薄雾模块": "dehaze1.png",
            "去火灾烟雾模块": "smoke_removal1.png",
            "人体识别模块": "person_detection1.png",
            "集成化模块": "integration.png",
            "default": "default.png"  # 错误加载下的默认图标
        }
        # 按钮配色方案
        button_colors = {
            "视频裁切": {"base": "#2196F3", "hover": "#1976D2", "pressed": "#0D47A1"},
            "时间对齐模块": {"base": "#FF9800", "hover": "#F57C00", "pressed": "#E65100"},
            "空间对齐模块": {"base": "#9C27B0", "hover": "#7B1FA2", "pressed": "#4A148C"},
            "多模态融合模块": {"base": "#00BCD4", "hover": "#0097A7", "pressed": "#006064"},
            "烟雾识别模块": {"base": "#607D8B", "hover": "#455A64", "pressed": "#263238"},
            "去薄雾模块": {"base": "#FF5722", "hover": "#E64A19", "pressed": "#BF360C"},
            "去火灾烟雾模块": {"base": "#4CAF50", "hover": "#388E3C", "pressed": "#1B5E20"},
            "人体识别模块": {"base": "#F44336", "hover": "#D32F2F", "pressed": "#B71C1C"},
            "集成化模块": {"base": "#F436A8", "hover": "#D32FC2", "pressed": "#761CB7"},
        }
        # 1. 时间空间对齐子界面
        alignment_ui = SubUI(
            "时间空间对齐", 
            ["视频裁切", "时间对齐模块", "空间对齐模块"],
            script_mapping,
            icon_mapping,
            button_colors,
            self
        )
        self.stacked_widget.addWidget(alignment_ui)
        
        # 2. 多模态融合子界面
        fusion_ui = SubUI(
            "多模态融合", 
            ["多模态融合模块"],
            script_mapping,
            icon_mapping,
            button_colors,
            self
        )
        self.stacked_widget.addWidget(fusion_ui)
        
        # 3. 去烟雾子界面
        smoke_ui = SubUI(
            "去烟雾", 
            ["去薄雾模块", "去火灾烟雾模块"],
            script_mapping,
            icon_mapping,
            button_colors,
            self
        )
        self.stacked_widget.addWidget(smoke_ui)
        
        # 4. 识别子界面
        detection_ui = SubUI(
            "烟雾/人体识别", 
            ["烟雾识别模块", "人体识别模块"],
            script_mapping,
            icon_mapping,
            button_colors,
            self
        )
        self.stacked_widget.addWidget(detection_ui) 

        # 5. 集成化子界面
        integration_ui = SubUI(
            "集成化",
            ["集成化模块"],
            script_mapping,
            icon_mapping,
            button_colors,
            self
        )
        self.stacked_widget.addWidget(integration_ui) 
 
        # 6. 联系我们子界面
        connection_ui = SubUI(
            "联系我们",
            [],
            script_mapping,
            icon_mapping,
            button_colors,
            self
        )

class SubUI(QWidget):
    # 超时时间设置（单位：毫秒）
    TIMEOUT = 3000000  # 3000秒
    def __init__(self, title, button_names, script_mapping, icon_mapping, button_colors, main_window):
        super().__init__()
        self.main_window = main_window
        self.title = title
        self.button_names = button_names
        self.script_mapping = script_mapping
        self.icon_mapping = icon_mapping
        self.button_colors = button_colors

        self.process = QProcess()
        self.timer = QTimer()

        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        layout = QVBoxLayout(self)
        # 返回按钮
        back_btn = QPushButton("返回主界面")
        back_btn.setFixedSize(120, 40)
        back_btn.setStyleSheet("""
            QPushButton {
                font-size: 20px;
                background-color: #5C4209;
                color: white;
                border: None;
                border-radius: 5px;
                font-weight: bold;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #4A3507;
            }
        """)
        back_btn.clicked.connect(lambda: self.main_window.stacked_widget.setCurrentIndex(0))
        layout.addWidget(back_btn, alignment=Qt.AlignLeft)

        # 标题
        title_label = QLabel(self.title)
        title_label.setStyleSheet("""font-size: 60px; font-weight: bold; color: #F5C77E; font-family: "华文行楷", sans-serif;""")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 功能按钮区
        buttons_container = QWidget()
        buttons_container.setStyleSheet("background-color: rgba(255, 255, 255, 0.4); border-radius: 10px; padding: 20px;")
        buttons_layout = QVBoxLayout(buttons_container)
        buttons_layout.setSpacing(40)  # 设置按钮间距

        if len(self.button_names) != 2:
            # 添加顶部伸缩空间（使第一个按钮不会紧贴顶部）
            buttons_layout.addStretch()

        for name in self.button_names:
            btn = self.create_styled_button(name)
            if name == ["多模态融合模块", "集成化模块"]:
                btn.setFixedSize(350, 100)
            else:
                btn.setFixedSize(300, 80)
            buttons_layout.addWidget(btn, alignment=Qt.AlignCenter)

        # 根据按钮数量调整布局行为
        if len(self.button_names) == 2:
            # 两个按钮时添加水平排列的容器
            buttons_container.setLayout(None)
            h_layout = QHBoxLayout(buttons_container)
            for name in self.button_names:
                btn = self.create_styled_button(name)
                btn.setFixedSize(300, 80)
                h_layout.addWidget(btn, alignment=Qt.AlignCenter)
            h_layout.addStretch()
        else:
            # 1个或3个按钮使用垂直布局
            buttons_layout.addStretch()

        layout.addWidget(buttons_container)

        # ========== 集成化模块的流程图区域 ========
        if self.title == "集成化":  
            chart_container = QWidget()
            chart_container.setStyleSheet("background-color: rgba(255, 255, 255, 0.4); border-radius: 10px; padding: 10px;")
            chart_layout = QVBoxLayout(chart_container)
            """  # 流程图插入
            self.chart_label = QLabel()
            chart_path = os.path.join(os.path.dirname(__file__), "绘图1.jpg")
            if os.path.exists(chart_path):
                pixmap = QPixmap(chart_path).scaled(800, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.chart_label.setPixmap(pixmap)
            else:
                # 如果没有流程图则显示默认图标
                self.chart_label.setText("FLOW CHART")
                self.chart_label.setStyleSheet("font-size: 40px; color: #666;")
            self.chart_label.setAlignment(Qt.AlignCenter)
            chart_layout.addWidget(self.chart_label) """
            
             # 创建自定义的流程图绘制区域
            class FlowChartWidget(QWidget):
                def __init__(self, parent=None):
                    super().__init__(parent)
                    self.setMinimumSize(500, 300)
            
                def paintEvent(self, event):
                    painter = QPainter(self)
                    painter.setRenderHint(QPainter.Antialiasing)

                    # 设置字体
                    font = QFont("黑体", 27)
                    painter.setFont(font)
            
                    # 定义样式
                    box_pen = QPen(Qt.NoPen) # 边框样式
                    text_pen = QPen(Qt.white, 10) # 字体颜色
                    arrow_pen = QPen(Qt.black, 4) # 箭头线条颜色
                    arrow_pen.setStyle(Qt.SolidLine)
                    fill_color = QColor("#F5C77EE1")  # 边框颜色填充    
                    fill_brush = QBrush(fill_color)      # 创建画刷
            
                    # 定义节点位置和大小
                    node_width = 200
                    node_height = 100
                    center_x = self.width() // 2
                    center_y = self.height() // 2
            
                    # 节点1: 可见光去烟
                    node1_rect = QRect(center_x - 500, center_y - 160, node_width, node_height)
                    painter.setPen(box_pen)
                    painter.setBrush(fill_brush)        
                    painter.drawRect(node1_rect)
                    painter.setPen(text_pen)
                    painter.drawText(node1_rect, Qt.AlignCenter, "可见光去烟")
            
                    # 节点2: 时间对齐
                    node2_rect = QRect(center_x - 100 , center_y - 160, node_width, node_height)
                    painter.setPen(box_pen)
                    painter.setBrush(fill_brush) 
                    painter.drawRect(node2_rect)
                    painter.setPen(text_pen)
                    painter.drawText(node2_rect, Qt.AlignCenter, "时间对齐")
            
                    # 节点3: 空间对齐
                    node3_rect = QRect(center_x + 300, center_y - 160, node_width, node_height)
                    painter.setPen(box_pen)
                    painter.setBrush(fill_brush)        
                    painter.drawRect(node3_rect)
                    painter.setPen(text_pen)
                    painter.drawText(node3_rect, Qt.AlignCenter, "空间对齐")
            
                    # 节点4: 多模态融合
                    node4_rect = QRect(center_x + 300, center_y + 20, node_width, node_height)
                    painter.setPen(box_pen)
                    painter.setBrush(fill_brush)         
                    painter.drawRect(node4_rect)
                    painter.setPen(text_pen)
                    painter.drawText(node4_rect, Qt.AlignCenter, "多模态融合")
            
                    # 节点5: 人体识别
                    node5_rect = QRect(center_x - 500, center_y + 20, node_width, node_height)
                    painter.setPen(box_pen)
                    painter.setBrush(fill_brush)         
                    painter.drawRect(node5_rect)
                    painter.setPen(text_pen)
                    painter.drawText(node5_rect, Qt.AlignCenter, "人体识别")

                    # 绘制连接线
                    painter.setPen(arrow_pen)
            
                    # 可见光去烟 → 时间对齐
                    painter.drawLine(node1_rect.right(), node1_rect.center().y(), 
                                    node2_rect.left(), node2_rect.center().y())
                    self.drawArrow(painter, node2_rect.left(), node2_rect.center().y(), 0)
            
                    # 时间对齐 → 空间对齐
                    painter.drawLine(node2_rect.right(), node2_rect.center().y(), 
                                    node3_rect.left(), node3_rect.center().y())
                    self.drawArrow(painter, node3_rect.left(), node3_rect.center().y(), 0)
            
                    # 空间对齐 ↓ 多模态融合
                    painter.drawLine(node3_rect.center().x(), node3_rect.bottom(), 
                                    node4_rect.center().x(), node4_rect.top())
                    self.drawArrow(painter, node4_rect.center().x(), node4_rect.top(), 90)
            
                    # 多模态融合 ← 人体识别
                    painter.drawLine(node5_rect.right(), node5_rect.center().y(), 
                                    node4_rect.left(), node4_rect.center().y())
                    self.drawArrow(painter, node5_rect.right(), node4_rect.center().y(), 180)
        
                def drawArrow(self, painter, x, y, angle):
                    painter.save()
                    painter.translate(x, y)
                    painter.rotate(angle)
            
                    arrow_size = 10
                    arrow_polygon = QPolygon([
                        QPoint(0, 0),
                        QPoint(-arrow_size, -arrow_size // 2),
                        QPoint(-arrow_size, arrow_size // 2)
                    ])
            
                    painter.setBrush(QBrush(Qt.black))
                    painter.drawPolygon(arrow_polygon)
                    painter.restore()
    
            # 创建并添加流程图部件
            flow_chart = FlowChartWidget()
            chart_layout.addWidget(flow_chart)
    
            layout.addWidget(chart_container)

        # ========== 输出控制台 ==========
        console_container = QWidget()
        console_container.setStyleSheet("background-color: rgba(255, 255, 255, 0.6); border-radius: 10px; padding: 15px;")
        console_layout = QVBoxLayout(console_container)

        console_title = QLabel("执行输出:")
        console_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #444; padding-bottom: 10px;")

        self.output_area = QTextEdit()
        self.output_area.setStyleSheet("""
            QTextEdit {
                background-color: rgba(46, 46, 46, 0.9);
                color: #FFFFFF;
                font-family: 'Consolas';
                font-size: 13px;
                border-radius: 8px;
                padding: 15px;
                border: 2px solid #404040;
            }
        """)
        self.output_area.setReadOnly(True)

        console_layout.addWidget(console_title)
        console_layout.addWidget(self.output_area)
        layout.addWidget(console_container)
    
    def create_styled_button(self, name):
        """创建带个性化样式的按钮"""
        colors = self.button_colors.get(name, {})
        btn = QPushButton(name)
        # 通过映射表获取图标文件名
        icon_name = self.icon_mapping.get(name, self.icon_mapping["default"])
        icon_path = os.path.join(
            os.path.dirname(__file__),  # 当前脚本所在目录
            "icons",
            icon_name                   # 映射得到的文件名
        )
        # 设置图标（如果文件存在）
        if os.path.exists(icon_path):
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(36, 36))  # 统一图标尺寸
        # 悬停提示
        btn.setToolTip(f"执行{name}功能")
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['base']};
                color: white;
                border: 2px solid {colors['hover']};
                font-size: 30px;
                padding: 10px;
                font-weight: 700;
                padding-left: 15px;  /* 左侧留出图标空间 */
                border-radius: 10px; 
                text-align: center;    /* 文字居中对齐 */
            }}
            QPushButton:hover {{
                background-color: {self.lighten_color(colors['base'], 0.15)};
                border-color: {self.lighten_color(colors['hover'], 0.1)};
            }}
            QPushButton:pressed {{
                background-color: {colors['pressed']};
                padding-top: 7px;                 /* 按下下沉效果 */
                padding-left: 7px;
            }}
            /* 禁用状态灰色 */
            QPushButton:disabled{{
                background-color: #CCCCCC
            }}
        """)
        btn.clicked.connect(lambda _, s=self.script_mapping[name]: self.execute_script(s))
        return btn
    
    def lighten_color(self, hex_color, factor=0.1):
        """颜色变亮工具函数"""
        try:
            hex_color = hex_color.lstrip('#')
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            lighter = [min(int(c + (255 - c) * factor), 255) for c in rgb]
            return "#" + "".join([format(c, '02X') for c in lighter])
        except:
            return hex_color  # 出错时返回原色
        
    def setup_connections(self):
        """连接信号与槽"""
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.script_finished)
        self.timer.timeout.connect(self.handle_timeout)

    def execute_script(self, script_name):
        """执行指定脚本"""
        if self.process.state() == QProcess.Running:
            self.process.kill()
            self.process.waitForFinished()

        script_path = os.path.join(os.path.dirname(__file__), script_name)
        if not os.path.exists(script_path):
            self.show_message(f"错误：找不到脚本 {script_name}", "red")
            return

        self.output_area.clear()
        self.show_message(f"启动 {script_name} 执行...", "cyan")
        self.process.start(sys.executable, [script_path])
        self.timer.start(self.TIMEOUT)

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        self.show_message(data.data().decode().strip(), "white")

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        self.show_message(data.data().decode().strip(), "red")

    def script_finished(self, exit_code, exit_status):
        self.timer.stop()
        color = "lime" if exit_code == 0 else "red"
        self.show_message(
            f"\n执行完成 [状态码: {exit_code} | 退出状态: {exit_status}]",
            color
        )

    def handle_timeout(self):
        if self.process.state() == QProcess.Running:
            self.process.kill()
            self.show_message("\n超时错误：进程执行超过限制时间", "darkorange")
        self.timer.stop()

    def show_message(self, message, color):
        """彩色信息显示"""
        if not message:
            return
        color_map = {
            "white": "#FFFFFF",
            "red": "#FF4444",
            "cyan": "#00FFFF",
            "lime": "#00FF00",
            "darkorange": "#FF8C00"
        }
        hex_color = color_map.get(color, "#FFFFFF")
        self.output_area.append(f"<font color='{hex_color}'>{message}</font>")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())