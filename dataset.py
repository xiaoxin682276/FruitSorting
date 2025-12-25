import os
import random
import shutil

# # 定义数据集目录和分割比例
source_root = 'data'
target_root = 'dataset'
train_ratio = 0.85
valid_ratio = 0.1
test_ratio = 0.05

# 创建目标文件夹及其子文件夹
train_dir = os.path.join(target_root, "train")
valid_dir = os.path.join(target_root, "valid")
test_dir = os.path.join(target_root, "test")
for phase in ['train', 'test', 'valid']:
    os.makedirs(os.path.join(target_root, phase, 'images'), exist_ok=True)
    os.makedirs(os.path.join(target_root, phase, 'labels'), exist_ok=True)

# 获取所有文件列表
files = os.listdir(source_root)
png_files = [f for f in files if f.endswith(".png")]

# 随机打乱文件列表
random.shuffle(png_files)

# 计算分割点
num_files = len(png_files)
num_train = int(train_ratio * num_files)
num_valid = int(valid_ratio * num_files)

# 移动文件到目标位置
# 将文件复制到相应目录
for i, file in enumerate(png_files):
    file = file.split('/')[-1].split('.')[-2]
    image_path = os.path.join(source_root, file + '.png')
    label_path = os.path.join(source_root, file + '.txt')
    print(image_path)
    print(label_path)

    if i < num_train:
        dst_dir = train_dir
    elif i < num_train + num_valid:
        dst_dir = valid_dir
    else:
        dst_dir = test_dir
    shutil.copy(image_path, os.path.join(dst_dir, 'images'))
    shutil.copy(label_path, os.path.join(dst_dir, 'labels'))

