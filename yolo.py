from ultralytics import YOLO

def train(data,epochs,batch,model_name):
    model = YOLO('yolov8n.pt')
    model.train(data=data,epochs=epochs,batch=batch,name=model_name,imgsz=640)

def predict(path):
    import os
    # 查找训练好的模型路径
    model_path = 'runs/detect/best/weights/best.pt'
    if not os.path.exists(model_path):
        model_path = 'best.pt'  # 尝试根目录下的模型
        if not os.path.exists(model_path):
            return "未找到训练模型，请先进行模型训练", 0.0, None
    
    try:
        model = YOLO(model_path)
        results = model(path)
        for result in results:
            boxes = result.boxes
            if len(boxes) > 0:
                id = boxes[0].cls[0].item()
                name = result.names[id]
                conf = boxes[0].conf[0].item()
                return name, conf, result  # 返回名称、置信度和结果对象
        return "未检测到目标", 0.0, None
    except Exception as e:
        return f"预测错误: {str(e)}", 0.0, None

def predict_with_image(path, save_path=None):
    """预测并保存带标注的图片"""
    import os
    model_path = 'runs/detect/best/weights/best.pt'
    if not os.path.exists(model_path):
        model_path = 'best.pt'
        if not os.path.exists(model_path):
            return None, "未找到训练模型"
    
    try:
        model = YOLO(model_path)
        results = model(path)
        if save_path:
            results[0].save(save_path)
        return results[0], None
    except Exception as e:
        return None, str(e)
