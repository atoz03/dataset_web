# 服务器部署与模型训练指南

本指南详细说明了如何将本项目部署到远程SSH服务器，并启动多模态模型的训练流程。

## 目录
1.  [准备服务器环境](#1-准备服务器环境)
2.  [部署项目文件与数据](#2-部署项目文件与数据)
3.  [编写并运行训练脚本](#3-编写并运行训练脚本)

---

### 1. 准备服务器环境

此步骤旨在服务器上配置一个干净、独立的Python环境。

#### 1.1 SSH连接
通过SSH客户端登录到你的服务器。
```bash
ssh username@your_server_ip
```

#### 1.2 安装Python及相关工具
确保服务器上装有 Python 3.9+。如果未安装或版本过低，可使用包管理器安装。
```bash
# 适用于 Ubuntu/Debian
sudo apt update
sudo apt install python3.9 python3-pip python3.9-venv
```

#### 1.3 创建项目目录
在服务器上为项目创建一个专用目录。
```bash
mkdir ~/project
cd ~/project
```

#### 1.4 创建并激活虚拟环境
使用`venv`创建独立的Python环境。
```bash
# 创建虚拟环境
python3.9 -m venv env

# 激活虚拟环境
source env/bin/activate
```
激活后，终端提示符前会出现`(env)`标识。

---

### 2. 部署项目文件与数据

将本地的项目代码和数据集传输到服务器。

#### 2.1 方法A: 使用Git (推荐用于代码)
如果项目已使用Git进行版本控制，这是最简洁的方式。
```bash
# 在服务器上运行
cd ~/project
git clone <你的Git仓库URL> .
```

#### 2.2 方法B: 使用rsync (推荐用于数据和初始部署)
`rsync`能高效地同步文件，尤其适合大型数据集。
```bash
# 在你的本地电脑上运行
# 同步整个项目，排除不必要的文件
rsync -avz --exclude '.git' --exclude '.idea' --exclude '.vscode' --exclude '__pycache__' --exclude 'env' --exclude '.venv' --exclude '.trash' ./ username@your_server_ip:~/project/

# 单独、高效地同步庞大的datasets目录
rsync -avz ./datasets/ username@your_server_ip:~/project/datasets/
```
`rsync`支持断点续传，非常可靠。

#### 2.3 安装项目依赖
在服务器上安装所有必需的Python库。
```bash
# 在服务器上运行
cd ~/project
source env/bin/activate
pip install -r requirements.txt
```

---

### 3. 编写并运行训练脚本

最后一步是创建并运行训练脚本。

#### 3.1 编写训练脚本 (`train.py`)
在项目根目录下创建一个`train.py`文件。以下是一个基于PyTorch和Hugging Face `transformers`的示例框架。

```python
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoProcessor, AutoModelForCausalLM
import json
from PIL import Image
import os

# 1. 定义数据集类
class AgricultureDataset(Dataset):
    def __init__(self, jsonl_path, image_dir, processor):
        self.processor = processor
        self.image_dir = image_dir
        self.data = []
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                self.data.append(json.loads(line))

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        image_path = os.path.join(self.image_dir, item['image_path'])
        try:
            image = Image.open(image_path).convert("RGB")
        except FileNotFoundError:
            print(f"Warning: Image not found at {image_path}. Skipping.")
            return self.__getitem__((idx + 1) % len(self))

        text = item.get('caption', item.get('text', ''))
        inputs = self.processor(text=[text], images=image, return_tensors="pt", padding=True)
        inputs['labels'] = inputs['input_ids'].clone()
        return {key: val.squeeze(0) for key, val in inputs.items()}

# 2. 主训练逻辑
def main():
    # --- 配置参数 ---
    MODEL_ID = "microsoft/Phi-3-vision-128k-instruct" # 示例模型
    JSONL_PATH = "data.jsonl"
    IMAGE_DIR = "datasets"
    BATCH_SIZE = 4
    EPOCHS = 3
    LEARNING_RATE = 5e-5

    # --- 环境设置 ---
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    processor = AutoProcessor.from_pretrained(MODEL_ID, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, trust_remote_code=True).to(device)

    # --- 数据加载 ---
    dataset = AgricultureDataset(jsonl_path=JSONL_PATH, image_dir=IMAGE_DIR, processor=processor)
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

    # --- 训练循环 ---
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)
    model.train()
    for epoch in range(EPOCHS):
        for i, batch in enumerate(dataloader):
            batch = {k: v.to(device) for k, v in batch.items()}
            outputs = model(**batch)
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
            if (i + 1) % 10 == 0:
                print(f"Epoch {epoch+1}, Batch {i+1}/{len(dataloader)}, Loss: {loss.item():.4f}")

    # --- 保存模型 ---
    print("Training finished. Saving model...")
    model.save_pretrained("./trained_model")
    processor.save_pretrained("./trained_model")

if __name__ == "__main__":
    main()
```

#### 3.2 运行训练
在服务器上安全地启动训练任务。

1.  **安装训练依赖**:
    ```bash
    # 在服务器上运行 (虚拟环境已激活)
    # 根据你的CUDA版本从PyTorch官网获取正确的命令
    pip install torch transformers
    ```

2.  **后台运行训练脚本**:
    使用`nohup`可以防止SSH断开连接时训练中断。
    ```bash
    # 在服务器上运行
    nohup python -u train.py > training.log 2>&1 &
    ```

3.  **监控训练进度**:
    ```bash
    tail -f training.log
    ```
训练完成后，模型文件将保存在`./trained_model`目录中。