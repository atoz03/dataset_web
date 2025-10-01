# 农业多模态视觉数据集知识库

本文档是项目核心知识库，旨在为数据集的构建、使用和未来发展提供一个清晰、连贯且全面的指南。它整合了项目的所有历史记录、处理流程、设计规范和战略规划。

---

## 第一部分：项目愿景与核心战略

本项目的核心目标是构建一个高质量、大规模、多模态的农业视觉知识库，而不仅仅是一个简单的图像分类数据集。所有的数据处理和标注工作都应服务于这一最终愿景。

### 核心战略原则

1.  **统一的多模态标注范式**:
    *   **目标**: 将每一张图片转化为包含丰富信息的“**图像-文本对 + 标签**”样本。
    *   **实现**: 为每张图片生成两种核心文本：
        *   **图像描述 (Caption)**: 中英双语的陈述句，描述图像内容。
            *   病害示例 (zh): “一张[作物]叶片，患有[病害名]。”
            *   健康示例 (en): “A healthy [crop] leaf.”
        *   **问答对 (VQA)**: 中英双语的指令化问答样本，用于训练模型的理解和推理能力。
            *   Q: “这张叶片得了什么病？” → A: “玉米锈病”
            *   Q: “这片叶子是否健康？” → A: “否”
            *   Q: “作物是什么？” → A: “玉米”

2.  **建立统一的本体 (Ontology)**:
    *   所有数据源的“作物”、“病害”、“是否健康”等标签必须规范化，确保跨数据源的一致性。
    *   详细的中英文对照表见 **附录 B**。

3.  **数据质量优先**:
    *   通过严格的去重、模糊检测和尺寸过滤，剔除低质量样本。
    *   色彩空间统一为 sRGB，训练分辨率建议不低于 448x448，以保留病斑细节。

4.  **可追溯性与可复现性**:
    *   所有数据处理步骤、脚本和参数都必须被记录。
    *   通过文件名中的来源标签，确保每一张图片都能追溯到其原始出处。

---

## 第二部分：数据集架构与核心规范

所有贡献者和使用者都必须严格遵守以下架构和规范。

### 2.1 目录结构

项目采用统一的分类目录结构：

```
datasets/
├── crops/      # 农作物图像
├── pests/      # 农业害虫图像
└── diseases/   # 植物病害图像
```

### 2.2 文件命名规范

所有数据集中的文件必须遵循以下格式，**文件名全部小写**：

`<类别名>__<来源标签>__<uuid>.<ext>`

-   **<类别名>**: 文件所属的标准化类别名称（英文），例如 `corn rust leaf`。
-   **<来源标签>**: 两个下划线包围的来源标识符，用于数据溯源。
-   **<uuid>**: 一个唯一的标识符，防止文件名冲突。
-   **<ext>**: 小写的文件扩展名，例如 `jpg`。

#### 来源标签释义

-   `__cd__`: 来自本地的 `Crop Diseases` 数据集。
-   `__pd__`: 来自 `PlantDoc` 或其他通用病害数据集。
-   `__kd__`: 来自 `Kaggle` 的病害数据集 (如 PlantVillage)。
-   `__ac__`: 来自各类农作物 (`crops`) 数据集。
-   `__ap__`: 来自各类害虫 (`pests`) 数据集。

### 2.3 数据标注范式 (JSONL 格式)

所有图像的元数据和文本标注都存储在统一的 `JSONL` 文件中。每一行代表一个样本。

#### JSONL 字段定义

-   `image`: 图像的相对路径。
-   `task`: 任务类型，`caption` 或 `vqa`。
-   `text`: 任务文本。对于 `caption`，这是图像描述；对于 `vqa`，这是问题。
-   `answer`: 仅用于 `vqa` 任务，表示问题的答案。
-   `lang`: 语言，`zh` 或 `en`。
-   `split`: 数据集划分，`train`, `val`, 或 `test`。
-   `labels`: 一个包含详细信息的对象，用于精细化训练和分析。
    -   `root`: 根目录 (`crops`, `pests`, `diseases`)。
    -   `class`: 标准化类名。
    -   `crop`/`disease`/`pest`: 从类名中解析出的具体实体。
    -   `healthy`: 布尔值，表示是否健康。
    -   `source`: 从文件名中解析出的来源标签 (`cd`, `pd`, `ac`, `ap`, `kd`)。

---

## 第三部分：数据处理工作流 (Playbook)

这是一个从零开始处理和整合新数据源的标准化流程。

### 第 1 步：合并新数据源

-   **策略**: 始终采用“**拷贝而非移动**”的策略，将新数据拷贝到 `datasets/` 目录中，以保留原始数据，便于回滚和审计。
-   **脚本**:
    -   `scripts/merge_crop_diseases.py`: 用于合并 `Crop Diseases` 数据集。
    -   `scripts/merge_140_crops.py`: 用于合并 `140-most-popular-crops` 数据集。
    -   `scripts/merge_kaggle_disease.py`: 用于合并从 Kaggle 下载的病害数据集。
-   **核心**: 在合并前，必须在脚本中定义好新旧类别名的映射关系，确保新数据能被正确归类。

### 第 2 步：标准化文件名

-   **目的**: 对新合入的、文件名不规范的数据进行统一重命名。
-   **脚本**: `scripts/bulk_rename_by_class.py`
-   **用法**:
    ```bash
    python3 scripts/bulk_rename_by_class.py --root <target_dir> --tag <source_tag>
    ```
-   **注意**: 此脚本会跳过已包含来源标签（如 `__cd__`）的文件，可安全地重复运行。

### 第 3 步：数据清洗

-   **目的**: 移除低质量、重复或损坏的图像。
-   **脚本**: `scripts/deduplicate_images.py`
-   **核心功能**:
    -   **尺寸过滤**: 剔除小于指定 `min-width` 和 `min-height` 的图像。
    -   **模糊检测**: 使用 Laplacian 方差检测并剔除模糊图像。
    -   **重复检测**: 使用感知哈希 (pHash/aHash) 检测并剔除重复或高度相似的图像。
-   **安全操作**:
    -   强烈建议首次运行时使用 `--action move`，脚本会将待删除文件移动到相应目录下的 `.trash/` 文件夹中。
    -   人工检查 `.trash/` 中的文件后，再决定是手动删除，还是使用 `--action delete` 进行永久删除。
-   **示例命令**:
    ```bash
    python3 scripts/deduplicate_images.py \
        --roots datasets/diseases datasets/crops datasets/pests \
        --min-width 224 --min-height 224 \
        --blur-threshold 60 --ham-threshold 3 \
        --action move
    ```

### 第 4 步：生成数据索引 (JSONL)

-   **目的**: 为清洗干净的数据集生成包含多模态标注的 `JSONL` 索引文件。
-   **脚本**: `scripts/build_jsonl.py`
-   **核心功能**:
    -   扫描 `datasets/` 下的所有图像。
    -   根据文件名和中英文对照表，自动生成中英双语的 **Caption** 和 **VQA** 样本。
    -   按类别进行分层抽样，划分 `train`, `val`, `test` 集。
    -   解析文件名，生成丰富的 `labels` 信息。
    -   基于病害关键字（`blight`, `rust`, `spot`, `mildew`, `virus`, `mite`, `rot`, `bacterial`, `blast`, `septoria`, `mold`, `scab` 等）推断健康与病害字段。
-   **示例命令**:
    ```bash
    python3 scripts/build_jsonl.py \
        --roots datasets/diseases datasets/crops datasets/pests \
        --out data.jsonl \
        --train 0.8 --val 0.1 --test 0.1 \
        --seed 42
    ```

### 第 5 步：验证与统计

-   **目的**: 确保数据集的质量和分布符合预期。
-   **方法 (待办)**:
    -   编写统计脚本，按类别和来源生成图像数量的统计报告 (CSV)。
    -   随机抽取各类别样本进行人工目视检查，验证标签准确性。
    -   分析图像尺寸和长宽比的分布。

---

## 第四部分：模型训练与评测路线图

基于当前数据集的结构和内容，推荐以下技术路线。

### 4.1 视觉编码器选型

-   **推荐**: `CLIP/SigLIP ViT-L/14`, `EVA-02`, `CoCa` 等强大的预训练模型。
-   **输入分辨率**: 建议 **≥ 448x448**，以捕捉精细的病斑特征。可考虑多尺度训练策略。

### 4.2 多模态架构选型

-   **推荐**: `LLaVA`, `InternVL`, `Qwen-VL`, `InstructBLIP` 等主流的多模态大模型架构。

### 4.3 训练策略

建议采用三阶段训练范式：

1.  **视觉-文本对齐预训练**: 使用生成的 Caption 数据，进行弱监督的图文对齐训练。
2.  **指令微调 (Instruction Tuning)**: 使用生成的 VQA 数据，对模型进行指令跟随能力的微调。
3.  **下游任务微调**: 针对具体的分类或判别任务，进行有监督微调。

### 4.4 评测指标

-   **分类任务**: Top-1 / Top-5 准确率。
-   **VQA 任务**: 字符串完全匹配 (EM)、F1 分数。
-   **关键分析**:
    -   **混淆矩阵**: 重点分析易混淆的病害类别（如早疫病 vs 晚疫病）。
    -   **跨域泛化**: 在不同来源的数据集上进行交叉测试（如用 `__cd__` 训练，在 `__pd__` 上测试）。
    -   **失效分析**: 使用 Grad-CAM 等工具可视化模型注意力，检查错误分类样本的关注区域是否正确。

---

## 第五部分：未来规划与待办事项 (TODOs)

这是一个整合的、高优先级的待办事项列表。

-   `[ ]` **统计与可视化脚本**:
    -   `[ ]` 按类与来源输出详细计数的 CSV 报告。
    -   `[ ]` 尺寸/长宽比分布的可视化脚本。
    -   `[ ]` 随机抽样并进行可视化检查的脚本。
-   `[ ]` **数据划分与打包**:
    -   `[ ]` 在 `build_jsonl.py` 中增加 `--holdout-source` 选项，以创建专门的跨来源测试集。
    -   `[ ]` 将 `data.jsonl` 按 `split` 字段拆分为 `train.jsonl`, `val.jsonl`, `test.jsonl`。
    -   `[ ]` 编写脚本将 `JSONL` 数据打包为 `WebDataset` (.tar) 格式，以提高训练吞吐。
-   `[ ]` **质量与合规**:
    -   `[ ]` 编写一个命名规范/类名白名单的校验器，作为预提交检查。
    -   `[ ]` 在 `origin.md` 中为每个数据来源补充 `License` 和 `Citation` 字段。
    -   `[ ]` 在清洗脚本中加入 EXIF 方向修正和 sRGB 颜色空间标准化功能。

---

## 附录 A：数据来源与合并历史

本部分详细记录了所有数据源信息及历史操作，以保证完全的可追溯性。

### A.1 数据源列表

1.  **Agricultural-crops**: [Kaggle Link](https://www.kaggle.com/datasets/mdwaquarazam/agricultural-crops-image-classification)
2.  **agricultural-pests-image-dataset**: [Kaggle Link](https://www.kaggle.com/datasets/vencerlanz09/agricultural-pests-image-dataset)
3.  **Agriculture crop images**: [Kaggle Link](https://www.kaggle.com/datasets/aman2000jaiswal/agriculture-crop-images/data?select=test_crop_image)
4.  **PlantDoc-Dataset**: [GitHub Link](https://github.com/pratikkayal/PlantDoc-Dataset/tree/master)
5.  **Agriculture Crops Dataset**: [Kaggle Link](https://www.kaggle.com/datasets/osamajalilhassan/agriculture-crops-dataset)
6.  **Top Agriculture Crop Disease**: [Kaggle Link](https://www.kaggle.com/datasets/kamal01/top-agriculture-crop-disease)
7.  **140-most-popular-crops-image-dataset**: [Kaggle Link](https://www.kaggle.com/datasets/omrathod2003/140-most-popular-crops-image-dataset)
8.  **PlantVillage Dataset**: [Kaggle Link](https://www.kaggle.com/datasets/abdallahalidev/plantvillage-dataset) (License: CC BY-NC-SA 4.0)
9.  **New Plant Diseases / Plant Pathology (预留)**: Kaggle 竞赛数据集。

### A.2 关键合并与处理日志

-   **2025-09-25**:
    -   **Crop Diseases 合并**: 使用 `scripts/merge_crop_diseases.py` 将本地 `Crop Diseases/` 数据集按病害类别合并到 `datasets/diseases/`，并重命名为 `<目标类>__cd__<uuid>.<ext>`。共拷贝 13,324 张图片。
    -   **统一命名**: 对 `datasets/diseases`, `datasets/crops`, `datasets/pests` 目录下的存量文件执行 `scripts/bulk_rename_by_class.py`，分别添加 `__pd__`, `__ac__`, `__ap__` 来源标签。
    -   **140 Crops 合并**: 使用 `scripts/merge_140_crops.py` 将 `140-most-popular-crops-image-dataset` 合并入 `datasets/crops`，新增 117 个类目录，复制 38,546 张图片。
    -   **源文件清理**: 完成合并后，删除了 `140-most-popular-crops-image-dataset/` 和 `Crop Diseases/` 原始目录以节省空间。

-   **2025-09-26**:
    -   **PlantDoc 合并**: 从 GitHub 下载 `PlantDoc-Dataset`，使用 `scripts/bulk_rename_by_class.py` 添加 `__pd__` 标签后，按类名拷贝 2,572 张图片到 `datasets/diseases/`。
    -   **PlantVillage 合并**: 从 Kaggle 下载 `abdallahalidev/plantvillage-dataset`，选用 `color/` 版本，规范化类名后，使用 `scripts/bulk_rename_by_class.py` 添加 `__kd__` 标签，并用 `scripts/merge_kaggle_disease.py` 合并 46,072 张图片到 `datasets/diseases/`。
    -   **命名校准**: 发现并处理了 `Soyabean leaf` vs `Soybean leaf` 等拼写不一致问题。通过 MD5 去重后，将唯一图片迁移到统一的类名下，并移除了空目录。

---

## 附录 B：中英文类目总表 (Ontology)

这是项目的核心本体，定义了所有目录和类别的中英文标准名称。

-   **根目录**:
    -   `datasets`: 数据集根目录
    -   `datasets/crops`: 农作物 (Crops)
    -   `datasets/pests`: 害虫 (Pests)
    -   `datasets/diseases`: 病害 (Diseases)

-   **Diseases 目录**:
    -   `Apple Scab Leaf`: 苹果黑星病
    -   `Apple leaf`: 苹果叶
    -   `Apple rust leaf`: 苹果锈病叶
    -   `Bell_pepper leaf`: 甜椒叶
    -   `Bell_pepper leaf spot`: 甜椒叶斑病
    -   `Blueberry leaf`: 蓝莓叶
    -   `Cherry leaf`: 樱桃叶
    -   `Corn Gray leaf spot`: 玉米灰斑病
    -   `Corn leaf`: 玉米叶
    -   `Corn leaf blight`: 玉米叶枯病
    -   `Corn rust leaf`: 玉米锈病叶
    -   `Peach leaf`: 桃叶
    -   `Potato leaf`: 马铃薯叶
    -   `Potato leaf early blight`: 马铃薯早疫病
    -   `Potato leaf late blight`: 马铃薯晚疫病
    -   `Raspberry leaf`: 覆盆子叶
    -   `Rice brown spot`: 稻褐斑病
    -   `Rice leaf`: 稻叶
    -   `Rice leaf blast`: 稻叶稻瘟病
    -   `Rice neck blast`: 稻穗颈稻瘟病
    -   `Soyabean leaf`: 大豆叶
    -   `Squash Powdery mildew leaf`: 南瓜白粉病叶
    -   `Strawberry leaf`: 草莓叶
    -   `Sugarcane bacterial blight`: 甘蔗细菌性叶枯病
    -   `Sugarcane leaf`: 甘蔗叶
    -   `Sugarcane red rot`: 甘蔗红腐病
    -   `Tomato Early blight leaf`: 番茄早疫病叶
    -   `Tomato Septoria leaf spot`: 番茄叶斑病（Septoria）
    -   `Tomato leaf`: 番茄叶
    -   `Tomato leaf bacterial spot`: 番茄细菌性斑点病
    -   `Tomato leaf late blight`: 番茄晚疫病叶
    -   `Tomato leaf mosaic virus`: 番茄花叶病毒
    -   `Tomato leaf yellow virus`: 番茄黄化病毒叶
    -   `Tomato mold leaf`: 番茄霉病叶
    -   `Tomato two spotted spider mites leaf`: 番茄二斑叶螨危害叶
    -   `Wheat brown rust`: 小麦褐锈病
    -   `Wheat leaf`: 小麦叶
    -   `Wheat yellow rust`: 小麦黄锈病
    -   `grape leaf`: 葡萄叶
    -   `grape leaf black rot`: 葡萄黑腐病

-   **Crops 目录**:
    -   `Cherry`: 樱桃
    -   `Coffee-plant`: 咖啡树
    -   `Cucumber`: 黄瓜
    -   `Fox_nut(Makhana)`: 芡实（鸡头米）
    -   `Lemon`: 柠檬
    -   `Olive-tree`: 橄榄树
    -   `Pearl_millet(bajra)`: 珍珠粟（Bajra）
    -   `Tobacco-plant`: 烟草
    -   `almond`: 杏仁（扁桃）
    -   `banana`: 香蕉
    -   `cardamom`: 小豆蔻
    -   `chilli`: 辣椒
    -   `clove`: 丁香
    -   `coconut`: 椰子
    -   `cotton`: 棉花
    -   `gram`: 鹰嘴豆（Gram）
    -   `jowar`: 高粱（Jowar）
    -   `jute`: 黄麻
    -   `maize`: 玉米
    -   `mustard-oil`: 芥籽（油用）
    -   `papaya`: 木瓜
    -   `pineapple`: 菠萝
    -   `rice`: 稻（大米）
    -   `soyabean`: 大豆（脚本同时识别 `soybean` 变体）
    -   `sugarcane`: 甘蔗
    -   `sunflower`: 向日葵
    -   `tea`: 茶树
    -   `tomato`: 番茄
    -   `vigna-radiati(Mung)`: 绿豆（豇豆属）
    -   `wheat`: 小麦

-   **Pests 目录**:
    -   `ants`: 蚂蚁
    -   `bees`: 蜜蜂
    -   `beetle`: 甲虫
    -   `caterpillar`: 毛虫（鳞翅目幼虫）
    -   `earthworms`: 蚯蚓
    -   `earwig`: 蠼螋
    -   `grasshopper`: 蝗虫
    -   `moth`: 蛾
    -   `slug`: 鼻涕虫
    -   `snail`: 蜗牛
    -   `wasp`: 黄蜂
    -   `weevil`: 象鼻虫
