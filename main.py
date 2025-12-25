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
    QVBoxLayout, QSpinBox,QTableWidget, QTableWidgetItem
from fruit import Ui_Dialog
import yolo
from PyQt5.QtGui import QPixmap


class myWindow(QWidget, Ui_Dialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("水果分拣系统")

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

    def modelTraining(self):

        yolo.train("E:/IT/bigdata/project/Cover/fruitSorting/data.yaml", 2, 16, 'best')  #实际应用需要batch为50

    def maturitySorting(self):

        file_name, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Image(*.png *.jpg)")
        if file_name:
            self.label_picture.setPixmap(QPixmap(file_name))
            result = yolo.predict(file_name)
            if isinstance(result, tuple):
                name, conf, _ = result
                if conf > 0:
                    display_text = f"{name} (置信度: {conf:.2%})"
                else:
                    display_text = name
            else:
                display_text = result
            self.label_lb.setText(display_text)
        else:
            QMessageBox.warning(self, "警告", "未选择图片")
            return

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
                    self.label_picture.setPixmap(QPixmap(self.path))
                    result = yolo.predict(self.path)

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
    win = myWindow()
    win.show()
    sys.exit(app.exec())
