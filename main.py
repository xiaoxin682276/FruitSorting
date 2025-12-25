import sys
import os
import csv
from datetime import datetime

from PyQt5.QtCore import QTimer

# 解决OpenMP库冲突问题
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

from  PyQt5.QtWidgets import QApplication,QWidget,QFileDialog,QMessageBox,QPushButton,QLabel,QHBoxLayout,QVBoxLayout,QSpinBox
from  fruit import Ui_Dialog
import yolo
from PyQt5.QtGui import QPixmap

class myWindow(QWidget,Ui_Dialog):
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

    def modelTraining(self):

        yolo.train("E:/IT/bigdata/project/Cover/fruitSorting/data.yaml",2,16,'best')#实际应用需要batch为50

    def maturitySorting(self):

        file_name,_ = QFileDialog.getOpenFileName(self,"选择图片","","Image(*.png *.jpg)")
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
            QMessageBox.warning(self,"警告","未选择图片")
            return

    def startSorting(self):

        directory = QFileDialog.getExistingDirectory(self,"选择文件夹")
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
                QMessageBox.warning(self,"警告","文件夹中没有图片")

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
            
            self.label_lb.setText(display_text)
            self.updateProgress()
            self.updateStatistics()
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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = myWindow()
    win.show()
    sys.exit(app.exec())