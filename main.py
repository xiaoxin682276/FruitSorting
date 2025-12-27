import sys
import os
import csv
import io
from PyQt5.QtCore import Qt
from datetime import datetime
from PyQt5.QtCore import QTimer

import matplotlib

matplotlib.use("Agg")  # 防止Qt界面阻塞
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # 微软雅黑
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
# 解决OpenMP库冲突问题
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

from PyQt5.QtWidgets import QApplication, QWidget, QFileDialog, QMessageBox, QPushButton, QLabel, QHBoxLayout, \
    QVBoxLayout, QSpinBox, QTableWidget, QTableWidgetItem,QTextEdit,QPushButton
from fruit import Ui_Dialog
import yolo
from PyQt5.QtGui import QPixmap,QIcon
from qt_material import apply_stylesheet


class myWindow(QWidget, Ui_Dialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("水果分拣系统")
        self.resize(1300,1150)  # 默认启动大小
        self.setMinimumSize(900, 650)  # 最小限制，防止挤压
        self.setWindowIcon(QIcon("icon.ico"))
        self.pushButton_modelTraining.clicked.connect(self.modelTraining)
        self.pushButton_maturitySorting.clicked.connect(self.maturitySorting)
        self.pushButton_startSorting.clicked.connect(self.startSorting)

        self.pushButton_modelTraining.setStyleSheet(
            "background-color: #f44336; color: white; border: none; border-radius: 5px; padding: 10px;")
        self.pushButton_maturitySorting.setStyleSheet(
            "background-color: #2196F3; color: white; border: none; border-radius: 5px; padding: 10px;")
        self.pushButton_startSorting.setStyleSheet(
            "background-color: #4CAF50; color: white; border: none; border-radius: 5px; padding: 10px;")

        self.image_files = []
        self.current_index = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.showNextImage)

        # 新增功能：统计数据
        self.statistics = {'ripe': 0, 'half-ripe': 0, 'raw': 0, '未检测到目标': 0}
        self.detection_results = []  # 存储检测结果
        self.is_paused = False  # 暂停状态
        self.timer_interval = 1000  # 默认1秒

        # 创建额外的UI控件
        self.setupAdditionalUI()

        # 默认趋势图
        self.current_chart_type = "trend"

        self.filter_target = "全部显示"  # 当前筛选目标
        self.filter_mode = True  # 是否启用筛选

        self.applyBeautyStyle()
        self.log("系统启动完成")

    def setupAdditionalUI(self):

        # 在主布局中添加新控件
        main_layout = self.gridLayout

        # 进度表示
        self.progress_label = QLabel("进度: 0/0")
        self.progress_label.setStyleSheet("font-size: 12px; color: #666;")
        main_layout.addWidget(self.progress_label, 4, 1, 1, 1)

        # 统计信息
        self.stats_label = QLabel("统计: ripe:0 half-ripe:0 raw:0")
        self.stats_label.setStyleSheet("font-size: 12px; color: #666;")
        main_layout.addWidget(self.stats_label, 5, 1, 1, 1)

        button_layout = QHBoxLayout()

        # 暂停/继续
        self.pause_button = QPushButton("暂停")
        self.pause_button.setStyleSheet(
            "background-color: #FF9800; color: white; border: none; border-radius: 5px; padding: 8px;")
        self.pause_button.clicked.connect(self.togglePause)
        button_layout.addWidget(self.pause_button)

        # 导出结果
        self.export_button = QPushButton("导出结果")
        self.export_button.setStyleSheet(
            "background-color: #9C27B0; color: white; border: none; border-radius: 5px; padding: 8px;")
        self.export_button.clicked.connect(self.exportResults)
        button_layout.addWidget(self.export_button)

        # 保存图片
        self.save_image_button = QPushButton("保存当前结果")
        self.save_image_button.setStyleSheet(
            "background-color: #607D8B; color: white; border: none; border-radius: 5px; padding: 8px;")
        self.save_image_button.clicked.connect(self.saveCurrentResult)
        button_layout.addWidget(self.save_image_button)

        # 速度调整
        speed_layout = QHBoxLayout()
        speed_label = QLabel("速度(毫秒):")
        self.speed_spinbox = QSpinBox()
        self.speed_spinbox.setMinimum(100)
        self.speed_spinbox.setMaximum(10000)
        self.speed_spinbox.setValue(1000)
        self.speed_spinbox.setSingleStep(100)
        self.speed_spinbox.valueChanged.connect(self.changeSpeed)
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_spinbox)

        # 将按钮布局添加到主布局
        main_layout.addLayout(button_layout, 6, 1, 1, 1)
        main_layout.addLayout(speed_layout, 7, 1, 1, 1)

        # ---------------- 可视化模块（新增） ----------------
        # 图表显示区
        self.chart_label = QLabel("图表区域")
        self.chart_label.setStyleSheet(
            "background-color: #ffffff; border: 1px solid #ddd; border-radius: 8px;")
        self.chart_label.setFixedSize(320, 220)  # 根据你界面调整大小
        self.chart_label.setScaledContents(True)
        main_layout.addWidget(self.chart_label, 8, 1, 1, 1)

        # 图表按钮组
        chart_btn_layout = QHBoxLayout()

        self.btn_bar = QPushButton("柱状图")
        self.btn_pie = QPushButton("饼图")
        self.btn_trend = QPushButton("趋势图")
        self.btn_export_chart = QPushButton("导出图表")

        # 样式（统一风格）
        for b in [self.btn_bar, self.btn_pie, self.btn_trend, self.btn_export_chart]:
            b.setStyleSheet(
                "background-color: #455A64; color: white; border: none; border-radius: 5px; padding: 6px;")
            chart_btn_layout.addWidget(b)

        # 绑定事件
        self.btn_bar.clicked.connect(lambda: self.switchChart("bar"))
        self.btn_pie.clicked.connect(lambda: self.switchChart("pie"))
        self.btn_trend.clicked.connect(lambda: self.switchChart("trend"))
        self.btn_export_chart.clicked.connect(self.exportChart)

        main_layout.addLayout(chart_btn_layout, 9, 1, 1, 1)
        # ----------------------------------------------------
        # ----------- 分类筛选组件（新增）-----------
        filter_layout = QHBoxLayout()
        filter_label = QLabel("筛选显示：")
        filter_label.setStyleSheet("font-size: 12px; color: #666;")

        from PyQt5.QtWidgets import QComboBox
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部显示", "ripe", "half-ripe", "raw", "未检测到目标"])
        self.filter_combo.setStyleSheet(
            "background-color: white; border: 1px solid #ccc; border-radius: 4px; padding: 4px;"
        )

        self.filter_combo.currentTextChanged.connect(self.onFilterChanged)

        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_combo)

        main_layout.addLayout(filter_layout, 10, 1, 1, 1)
        # ------------------------------------------
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["编号", "文件名", "类别", "置信度", "时间"])
        self.table.setStyleSheet("background-color: white; border: 1px solid #ddd;")
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # 不可编辑
        self.table.setSelectionBehavior(QTableWidget.SelectRows)  # 选中整行
        self.table.cellDoubleClicked.connect(self.jumpToSelectedRow)

        # 放到 gridLayout 中（行号你自己选一个空行，比如 11）
        main_layout.addWidget(self.table, 11, 1, 2, 1)

        # 重置系统
        self.reset_button = QPushButton("重置系统")
        self.reset_button.setStyleSheet(
            "background-color: #E91E63; color: white; border: none; border-radius: 5px; padding: 8px;")
        self.reset_button.clicked.connect(self.resetAll)
        button_layout.addWidget(self.reset_button)

        # ---------------- 日志模块（左下角） ----------------
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("运行日志将在这里显示...")
        self.log_box.setStyleSheet("""
            QTextEdit{
                background: white;
                border: 1px solid #dedede;
                border-radius: 12px;
                padding: 8px;
                font-size: 12px;
                color: #333;
            }
        """)

        # 清空日志按钮
        self.btn_clear_log = QPushButton("清空日志")
        self.btn_clear_log.setFixedHeight(32)

        # 导出日志按钮
        self.btn_export_log = QPushButton("导出日志")
        self.btn_export_log.setFixedHeight(32)

        # 按钮统一样式
        btn_style = """
            QPushButton{
                background:#455A64;
                color:white;
                border:none;
                border-radius:8px;
                padding:6px 14px;
                font-size:12px;
                font-weight:600;
            }
            QPushButton:hover{
                background:#333;
            }
        """
        self.btn_clear_log.setStyleSheet(btn_style)
        self.btn_export_log.setStyleSheet(btn_style)

        # 绑定事件
        self.btn_clear_log.clicked.connect(self.log_box.clear)
        self.btn_export_log.clicked.connect(self.exportLog)

        # 按钮横排
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_clear_log)
        btn_row.addWidget(self.btn_export_log)

        # 整体布局
        log_layout = QVBoxLayout()
        log_layout.addLayout(btn_row)
        log_layout.addWidget(self.log_box)

        log_widget = QWidget()
        log_widget.setLayout(log_layout)

        # 放入 gridLayout 左下
        main_layout.addWidget(log_widget, 4, 0, 10, 1)

    def log(self, msg):
        """写入日志（自动带时间）"""
        time_str = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{time_str}] {msg}")
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def applyBeautyStyle(self):
        from PyQt5.QtWidgets import QSizePolicy
        from PyQt5.QtGui import QFont

        # ===== 全局字体 =====
        self.setFont(QFont("Microsoft YaHei", 10))

        # ===== 主布局边距（非常关键）=====
        if hasattr(self, "gridLayout"):
            self.gridLayout.setContentsMargins(28, 20, 28, 20)
            self.gridLayout.setHorizontalSpacing(22)
            self.gridLayout.setVerticalSpacing(14)

        # ===== 卡片样式 =====
        card = """
        background: white;
        border: 1px solid #dedede;
        border-radius: 14px;
        """

        # 图片显示区
        if hasattr(self, "label_picture"):
            self.label_picture.setStyleSheet(card)
            self.label_picture.setScaledContents(True)
            self.label_picture.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 图表显示区
        if hasattr(self, "chart_label"):
            self.chart_label.setStyleSheet(card)
            self.chart_label.setScaledContents(True)

        # 表格卡片化 + 表头优化
        if hasattr(self, "table"):
            self.table.setStyleSheet("""
            QTableWidget{
                background:white;
                border:1px solid #dedede;
                border-radius:14px;
                gridline-color:#eeeeee;
            }
            QTableWidget::item{
                padding:6px;
            }
            QHeaderView::section{
                background:#f5f5f5;
                padding:8px;
                border:none;
                font-weight:600;
            }
            """)
            self.table.setAlternatingRowColors(True)
            self.table.verticalHeader().setVisible(False)

        # ===== 输入框统一 =====
        input_style = """
        QSpinBox, QComboBox{
            background:white;
            border:1px solid #cfcfcf;
            border-radius:10px;
            padding:6px;
            min-height:32px;
            font-size:13px;
        }
        """
        self.setStyleSheet(self.styleSheet() + input_style)

        # ===== 按钮样式统一 =====
        def style_btn(btn, color, height=42):
            btn.setFixedHeight(height)
            btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 12px;
                padding: 10px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #3a3a3a;
            }}
            """)

        # 主按钮：三色保留，但统一圆角和高度
        style_btn(self.pushButton_modelTraining, "#F44336", 56)
        style_btn(self.pushButton_maturitySorting, "#2196F3", 56)
        style_btn(self.pushButton_startSorting, "#4CAF50", 56)

        # 功能按钮：统一深色系，只保留“暂停/重置”强调
        if hasattr(self, "pause_button"): style_btn(self.pause_button, "#FF9800", 42)
        if hasattr(self, "export_button"): style_btn(self.export_button, "#607D8B", 42)
        if hasattr(self, "save_image_button"): style_btn(self.save_image_button, "#607D8B", 42)
        if hasattr(self, "reset_button"): style_btn(self.reset_button, "#E91E63", 42)

        # 图表按钮统一
        for b in [self.btn_bar, self.btn_pie, self.btn_trend, self.btn_export_chart]:
            style_btn(b, "#455A64", 40)

        # ===== 标签文字样式（进度/统计/类别）=====
        if hasattr(self, "label_lb"):
            self.label_lb.setStyleSheet("font-size:14px; color:#333; font-weight:600;")
        if hasattr(self, "progress_label"):
            self.progress_label.setStyleSheet("font-size:13px; color:#666;")
        if hasattr(self, "stats_label"):
            self.stats_label.setStyleSheet("font-size:13px; color:#666;")

        self.pushButton_modelTraining.setMaximumWidth(700)
        self.pushButton_maturitySorting.setMaximumWidth(700)
        self.pushButton_startSorting.setMaximumWidth(700)

    def modelTraining(self):

        yolo.train("E:/IT/bigdata/project/Cover/fruitSorting/data.yaml", 2, 16, 'best')  #实际应用需要batch为50

    def maturitySorting(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Image(*.png *.jpg)")
        if not file_name:
            QMessageBox.warning(self, "警告", "未选择图片")
            return

        # 先做预测（拿到类别+置信度）
        result = yolo.predict(file_name)

        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, "temp_result.jpg")

        yolo.predict_with_image(file_name, temp_path)

        # 显示带框结果图
        self.label_picture.setPixmap(QPixmap(temp_path))

        # 显示文本结果
        if isinstance(result, tuple):
            name, conf, _ = result
            display_text = f"{name} (置信度: {conf:.2%})" if conf > 0 else name
        else:
            display_text = result

        self.label_lb.setText(display_text)

    def startSorting(self):

        directory = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if directory:
            self.image_files = [
                os.path.join(directory, f) for f in os.listdir(directory)
                if f.lower().endswith(('.png', '.jpg'))
            ]
            if self.image_files:

                self.statistics = {'ripe': 0, 'half-ripe': 0, 'raw': 0, '未检测到目标': 0}
                self.detection_results = []
                self.current_index = 0
                self.is_paused = False
                self.pause_button.setText("暂停")
                self.updateProgress()
                self.updateStatistics()
                self.showCurrentImage()
                self.timer.start(self.timer_interval)
            else:
                QMessageBox.warning(self, "警告", "文件夹中没有图片")

        self.log(f"选择文件夹：{directory}")
        self.log(f"开始分拣，共 {len(self.image_files)} 张图片")

    def resetAll(self):
        """一键重置系统到初始状态"""
        reply = QMessageBox.question(
            self, "确认重置", "确定要重置系统吗？\n将清空统计、表格、图表和当前任务。",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # 1) 停止定时器
        if self.timer.isActive():
            self.timer.stop()

        # 2) 清空数据
        self.image_files = []
        self.current_index = 0
        self.is_paused = False
        self.statistics = {'ripe': 0, 'half-ripe': 0, 'raw': 0, '未检测到目标': 0}
        self.detection_results = []

        # 3) 重置筛选模式
        self.filter_target = "全部显示"
        if hasattr(self, "filter_combo"):
            self.filter_combo.setCurrentIndex(0)

        # 4) 重置 UI 显示
        self.label_picture.clear()
        self.label_lb.setText("等待检测...")

        self.progress_label.setText("进度: 0/0")
        self.stats_label.setText("统计: ripe:0 half-ripe:0 raw:0")

        # 5) 清空表格
        if hasattr(self, "table"):
            self.table.setRowCount(0)

        # 6) 清空图表显示
        if hasattr(self, "chart_label"):
            self.chart_label.clear()
            self.chart_label.setText("图表区域")

        # 7) 重置暂停按钮状态
        self.pause_button.setText("暂停")
        self.pause_button.setStyleSheet(
            "background-color: #FF9800; color: white; border: none; border-radius: 5px; padding: 8px;"
        )

        # 8) 可选：重置图表类型为趋势图
        self.current_chart_type = "trend"

        QMessageBox.information(self, "完成","重置成功")
        self.log("系统已重置")

    def showCurrentImage(self):

        if self.current_index < len(self.image_files):
            if self.is_paused:
                return

            self.path = self.image_files[self.current_index]
            self.label_picture.setPixmap(QPixmap(self.path))

            # 进行预测
            result = yolo.predict(self.path)
            if isinstance(result, tuple):
                name, conf, result_obj = result
                if conf > 0:
                    display_text = f"{name} (置信度: {conf:.2%})"
                else:
                    display_text = name

                # 更新统计
                if name in self.statistics:
                    self.statistics[name] += 1
                else:
                    self.statistics['未检测到目标'] += 1

                # 记录结果
                self.detection_results.append({
                    '编号': self.current_index + 1,
                    '文件名': os.path.basename(self.path),
                    '图片路径': self.path,
                    '类别': name,
                    '置信度': f"{conf:.2%}" if conf > 0 else "N/A",
                    '时间': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

            else:
                display_text = result
                self.statistics['未检测到目标'] += 1
                self.detection_results.append({
                    '图片路径': self.path,
                    '类别': result,
                    '置信度': "N/A",
                    '时间': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            # ---------------- 筛选逻辑（循环版）----------------
            if self.filter_target != "全部显示":
                current_class = name if isinstance(result, tuple) else result

                while current_class != self.filter_target:
                    self.current_index += 1
                    if self.current_index >= len(self.image_files):
                        # 已经没有符合筛选的图片了
                        self.timer.stop()
                        QMessageBox.information(self, "提示", f"分拣结束：未找到更多 {self.filter_target} 类别图片")
                        return

                    # 换下一张继续识别
                    self.path = self.image_files[self.current_index]

                    # 预测
                    result = yolo.predict(self.path)

                    import tempfile
                    temp_dir = tempfile.gettempdir()
                    temp_path = os.path.join(temp_dir, "temp_sort_result.jpg")

                    yolo.predict_with_image(self.path, temp_path)
                    self.label_picture.setPixmap(QPixmap(temp_path))

                    if isinstance(result, tuple):
                        name, conf, result_obj = result
                        current_class = name
                        display_text = f"{name} (置信度: {conf:.2%})" if conf > 0 else name
                    else:
                        display_text = result
                        current_class = result

                # 找到符合的类别，继续往下显示
            # ---------------------------------------------------
            self.label_lb.setText(display_text)
            self.updateProgress()
            self.updateStatistics()
            if self.current_index % 2 == 0:  # 每2张刷新一次
                self.refreshChart()
            self.refreshTable()

        else:
            self.timer.stop()
            total = sum(self.statistics.values())
            stats_text = f"ripe: {self.statistics['ripe']}, half-ripe: {self.statistics['half-ripe']}, raw: {self.statistics['raw']}"
            QMessageBox.information(self, "提示", f"分拣完毕！\n总共检测: {total}张\n{stats_text}")

        if isinstance(result, tuple):
            self.log(f"#{self.current_index + 1} {os.path.basename(self.path)} -> {name} ({conf:.2%})")
        else:
            self.log(f"#{self.current_index + 1} {os.path.basename(self.path)} -> 未检测到目标")

    def showNextImage(self):

        if not self.is_paused:
            self.current_index += 1
            self.showCurrentImage()

    def togglePause(self):

        self.is_paused = not self.is_paused
        if self.is_paused:
            self.timer.stop()
            self.pause_button.setText("继续")
            self.pause_button.setStyleSheet(
                "background-color: #4CAF50; color: white; border: none; border-radius: 5px; padding: 8px;")
        else:
            self.timer.start(self.timer_interval)
            self.pause_button.setText("暂停")
            self.pause_button.setStyleSheet(
                "background-color: #FF9800; color: white; border: none; border-radius: 5px; padding: 8px;")

        if self.is_paused:
            self.log("已暂停")
        else:
            self.log("已继续")

    def changeSpeed(self, value):

        self.timer_interval = value
        if self.timer.isActive():
            self.timer.stop()
            self.timer.start(self.timer_interval)

    def updateProgress(self):

        total = len(self.image_files)
        current = self.current_index + 1
        self.progress_label.setText(f"进度: {current}/{total}")

    def updateStatistics(self):

        stats_text = f"统计: ripe:{self.statistics['ripe']} half-ripe:{self.statistics['half-ripe']} raw:{self.statistics['raw']}"
        self.stats_label.setText(stats_text)

    def exportResults(self):

        if not self.detection_results:
            QMessageBox.warning(self, "警告", "没有检测信息可导出")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存检测结果", f"检测结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)")

        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=['图片路径', '类别', '置信度', '时间'])
                    writer.writeheader()
                    writer.writerows(self.detection_results)

                # 添加统计信息
                with open(file_path, 'a', newline='', encoding='utf-8-sig') as f:
                    f.write(f"\n统计信息:\n")
                    f.write(f"ripe: {self.statistics['ripe']}\n")
                    f.write(f"half-ripe: {self.statistics['half-ripe']}\n")
                    f.write(f"raw: {self.statistics['raw']}\n")
                    f.write(f"未检测到目标: {self.statistics['未检测到目标']}\n")

                QMessageBox.information(self, "成功", f"结果已导出到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

        self.log(f"导出结果成功：{file_path}")

    def saveCurrentResult(self):

        if not hasattr(self, 'path') or not self.path:
            QMessageBox.warning(self, "警告", "没有当前图片可保存")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存结果图片", f"结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
            "Image Files (*.jpg *.png)")

        if file_path:
            try:
                result_obj, error = yolo.predict_with_image(self.path, file_path)
                if error:
                    QMessageBox.warning(self, "警告", error)
                else:
                    QMessageBox.information(self, "成功", f"结果图片已保存到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

        self.log(f"保存当前结果图片：{file_path}")

    def _drawAndShowChart(self, fig):
        """将matplotlib图保存到内存中并显示到QLabel（不落盘）"""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=120, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)

        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue())
        self.chart_label.setPixmap(pixmap)

    def showBarChart(self):
        """显示柱状图：各类别数量"""
        labels = ['ripe', 'half-ripe', 'raw', '未检测到目标']
        values = [self.statistics.get(k, 0) for k in labels]

        fig = plt.figure(figsize=(4, 3))
        plt.title("Sorting Statistics - Bar")
        plt.xlabel("Class")
        plt.ylabel("Count")
        plt.bar(labels, values)
        plt.xticks(rotation=20)

        self._drawAndShowChart(fig)

    def showPieChart(self):
        """显示饼图：各类别占比"""
        labels = ['ripe', 'half-ripe', 'raw', '未检测到目标']
        values = [self.statistics.get(k, 0) for k in labels]

        total = sum(values)
        if total == 0:
            QMessageBox.warning(self, "提示", "暂无统计数据，无法生成饼图")
            return

        fig = plt.figure(figsize=(4, 3))
        plt.title("Sorting Ratio - Pie")
        plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)

        self._drawAndShowChart(fig)

    def showTrendChart(self):
        """显示趋势图：置信度随图片序号变化"""
        conf_list = []
        for item in self.detection_results:
            conf_str = item.get("置信度", "N/A")
            if conf_str != "N/A" and "%" in conf_str:
                try:
                    conf_value = float(conf_str.replace("%", ""))  # 98.89
                    conf_list.append(conf_value)
                except:
                    pass

        if not conf_list:
            QMessageBox.warning(self, "提示", "暂无置信度数据，无法生成趋势图")
            return

        fig = plt.figure(figsize=(4, 3))
        plt.title("Confidence Trend")
        plt.xlabel("Index")
        plt.ylabel("Confidence (%)")
        plt.plot(conf_list, marker="o", linestyle="-")

        self._drawAndShowChart(fig)

    def exportChart(self):
        """一次性导出柱状图、饼图、趋势图"""
        if not self.detection_results and sum(self.statistics.values()) == 0:
            QMessageBox.warning(self, "提示", "暂无数据，无法导出图表")
            return

        # 选择保存文件夹
        folder = QFileDialog.getExistingDirectory(self, "选择导出文件夹")
        if not folder:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        try:
            # 生成三张图（不显示，只保存）
            self.saveBarChart(os.path.join(folder, f"柱状图_{timestamp}.png"))
            self.savePieChart(os.path.join(folder, f"饼图_{timestamp}.png"))
            self.saveTrendChart(os.path.join(folder, f"趋势图_{timestamp}.png"))

            QMessageBox.information(self, "成功", f"三张图表已导出到:\n{folder}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def refreshChart(self):
        """动态刷新当前显示的图表"""
        if self.current_chart_type == "bar":
            self.showBarChart()
        elif self.current_chart_type == "pie":
            self.showPieChart()
        elif self.current_chart_type == "trend":
            self.showTrendChart()

    def switchChart(self, chart_type):
        """切换显示图表类型"""
        self.current_chart_type = chart_type
        self.refreshChart()

    def saveBarChart(self, file_path):
        labels = ['ripe', 'half-ripe', 'raw', '未检测到目标']
        values = [self.statistics.get(k, 0) for k in labels]

        fig = plt.figure(figsize=(4, 3))
        plt.title("分拣统计柱状图")
        plt.xlabel("类别")
        plt.ylabel("数量")
        plt.bar(labels, values)
        plt.xticks(rotation=20)

        fig.savefig(file_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    def savePieChart(self, file_path):
        labels = ['ripe', 'half-ripe', 'raw', '未检测到目标']
        values = [self.statistics.get(k, 0) for k in labels]
        total = sum(values)

        fig = plt.figure(figsize=(4, 3))
        if total == 0:
            plt.title("暂无数据")
        else:
            plt.title("分拣统计比例图")
            plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)

        fig.savefig(file_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    def exportLog(self):
        """导出日志到txt文件"""
        if not hasattr(self, "log_box") or self.log_box.toPlainText().strip() == "":
            QMessageBox.warning(self, "提示", "当前没有日志内容可导出")
            return

        default_name = f"运行日志_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出日志", default_name, "Text Files (*.txt)"
        )

        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.log_box.toPlainText())

            QMessageBox.information(self, "成功", f"日志已导出到：\n{file_path}")
            self.log(f"日志导出成功：{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败：{str(e)}")

    def saveTrendChart(self, file_path):
        conf_list = []
        for item in self.detection_results:
            conf_str = item.get("置信度", "N/A")
            if conf_str != "N/A" and "%" in conf_str:
                try:
                    conf_list.append(float(conf_str.replace("%", "")))
                except:
                    pass

        fig = plt.figure(figsize=(4, 3))
        if not conf_list:
            plt.title("暂无置信度数据")
        else:
            plt.title("置信度变化趋势")
            plt.xlabel("图片序号")
            plt.ylabel("置信度(%)")
            plt.plot(conf_list, marker="o", linestyle="-")

        fig.savefig(file_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    def onFilterChanged(self, text):
        """筛选类别改变"""
        self.filter_target = text
        QMessageBox.information(self, "筛选提示", f"当前筛选模式：{text}\n分拣将只显示该类别图片（全部显示则不筛选）")
        self.log(f"筛选模式切换为：{text}")

    def getFilteredResults(self):
        """获取当前筛选模式下的结果列表"""
        if self.filter_target == "全部显示":
            return self.detection_results
        return [r for r in self.detection_results if r["类别"] == self.filter_target]

    def refreshTable(self):
        """刷新表格显示"""
        results = self.getFilteredResults()
        self.table.setRowCount(len(results))

        for row, item in enumerate(results):
            self.table.setItem(row, 0, QTableWidgetItem(str(item["编号"])))
            self.table.setItem(row, 1, QTableWidgetItem(item["文件名"]))
            self.table.setItem(row, 2, QTableWidgetItem(item["类别"]))
            self.table.setItem(row, 3, QTableWidgetItem(item["置信度"]))
            self.table.setItem(row, 4, QTableWidgetItem(item["时间"]))

    def jumpToSelectedRow(self, row, col):
        """双击表格行 → 跳转到对应编号图片"""
        results = self.getFilteredResults()
        if row >= len(results):
            return

        target = results[row]
        target_index = int(target["编号"]) - 1  # 编号从1开始，索引从0开始

        # 跳转到该图片
        self.current_index = target_index
        self.is_paused = True
        self.timer.stop()
        self.pause_button.setText("继续")
        self.showCurrentImage()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    apply_stylesheet(app, theme='light_cyan.xml')  # ✅ 你也可以换 dark_blue.xml 等

    win = myWindow()
    win.show()
    sys.exit(app.exec())
