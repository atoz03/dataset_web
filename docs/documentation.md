# 农业多模态视觉数据集知识库

本文档是项目核心知识库，旨在为数据集的构建、使用和未来发展提供一个清晰、连贯且全面的指南。它整合了项目的所有历史记录、处理流程、设计规范和战略规划。请在执行后更新此文档。

## 目录

- [1. 项目愿景与核心战略](#sec-1)
- [2. 数据集架构与核心规范](#sec-2)
  - [2.1 目录结构](#sec-2-1)
  - [2.2 文件命名规范](#sec-2-2)
  - [2.3 数据标注范式 (JSONL 格式)](#sec-2-3)
- [3. 数据处理工作流 (Playbook)](#sec-3)
  - [3.1 合并新数据源](#sec-3-1)
  - [3.2 标准化文件名](#sec-3-2)
  - [3.3 数据清洗](#sec-3-3)
  - [3.4 人工核验（网页）](#sec-3-4)
  - [3.5 LLM 语义验证与描述增强](#sec-3-5)
  - [3.6 生成数据索引 (JSONL)](#sec-3-6)
  - [3.7 数据采集策略](#sec-3-7)
- [4. 模型训练与评测路线图](#sec-4)
- [5. 未来规划与待办事项 (TODOs)](#sec-5)
- [附录 A：数据来源与合并历史](#app-a)
  - [A.1 数据源列表](#app-a-1)
  - [A.2 关键处理日志](#app-a-2)
- [附录 B：中英文类目总表 (Ontology)](#app-b)

---

`<a id="sec-1"></a>`

## 1. 项目愿景与核心战略

本项目的核心目标是构建一个高质量、大规模、多模态的农业视觉知识库，而不仅仅是一个简单的图像分类数据集。所有的数据处理和标注工作都应服务于这一最终愿景。其核心战略原则包括：

1. **统一的多模态标注范式**:

   * **目标**: 将每一张图片转化为包含丰富信息的“**图像-文本对 + 标签**”样本。
   * **实现**: 为每张图片生成中英双语的**图像描述 (Caption)**和**问答对 (VQA)**。
2. **建立统一的本体 (Ontology)**:

   * 所有数据源的“作物”、“病害”、“是否健康”等标签必须规范化，确保跨数据源的一致性。详细的中英文对照表见 **附录 B**。
3. **数据质量优先**:

   * 通过严格的去重、模糊检测和尺寸过滤，剔除低质量样本。
   * 色彩空间统一为 sRGB，训练分辨率建议不低于 448x448。
4. **可追溯性与可复现性**:

   * 所有数据处理步骤、脚本和参数都必须被记录。
   * 通过文件名中的来源标签，确保每一张图片都能追溯到其原始出处。

---

`<a id="sec-2"></a>`

## 2. 数据集架构与核心规范

所有贡献者和使用者都必须严格遵守以下架构和规范。

`<a id="sec-2-1"></a>`

### 2.1 目录结构

```
datasets/
├── crops/      # 农作物图像
├── pests/      # 农业害虫图像
└── diseases/   # 植物病害图像
```

`<a id="sec-2-2"></a>`

### 2.2 文件命名规范

所有数据集中的文件必须遵循以下格式，**文件名全部小写**：

`<类别名>__<来源标签>__<uuid>.<ext>`

- **<类别名>**: 文件所属的标准化类别名称（英文），例如 `corn rust leaf`。
- **<来源标签>**: 两个下划线包围的来源标识符，用于数据溯源。常见标签包括 `__cd__` (Crop Diseases), `__pd__` (PlantDoc), `__kd__` (Kaggle), `__ac__` (Crops), `__ap__` (Pests), `__web__` (网络爬虫)。
- **`<uuid>`**: 一个唯一的标识符，防止文件名冲突。
- **`<ext>`**: 小写的文件扩展名，例如 `jpg`。

`<a id="sec-2-3"></a>`

### 2.3 数据标注范式 (JSONL 格式)

所有图像的元数据和文本标注都存储在统一的 `data.jsonl` 文件中。每一行代表一个样本，包含 `image`, `task`, `text`, `answer`, `lang`, `split`, 和 `labels` 等字段。其中 `labels` 对象包含了从目录和文件名中解析出的详细信息，如根目录、类名、具体实体、是否健康、来源等。

---

`<a id="sec-3"></a>`

## 3. 数据处理工作流 (Playbook)

这是一个从零开始处理和整合新数据源的标准化流程。

`<a id="sec-3-1"></a>`

### 3.1 合并新数据源

- **策略**: 始终采用“**拷贝而非移动**”的策略，将新数据拷贝到 `datasets/` 目录中，以保留原始数据。
- **脚本**: 使用 `scripts/merge_*.py` 系列脚本，并在脚本中定义好新旧类别名的映射关系。

`<a id="sec-3-2"></a>`

### 3.2 标准化文件名

- **目的**: 对新合入的、文件名不规范的数据进行统一重命名。
- **脚本**: [`scripts/bulk_rename_by_class.py`](scripts/bulk_rename_by_class.py:1)
- **用法**: `python3 scripts/bulk_rename_by_class.py --root <target_dir> --tag <source_tag>`

`<a id="sec-3-3"></a>`

### 3.3 数据清洗

- **目的**: 移除低质量、重复或损坏的图像。
- **脚本**: [`scripts/deduplicate_images.py`](scripts/deduplicate_images.py:1)
- **核心功能**:
  - **尺寸过滤**: 剔除小于 `min-width` 和 `min-height` 的图像。
  - **模糊检测**: 推荐使用 `--blur-method both`，结合拉普拉斯方差和 Tenengrad 梯度能量，减少误判。
  - **重复检测**: 使用感知哈希 (pHash/aHash) 检测并剔除重复或高度相似的图像。
- **安全操作**: 强烈建议首次运行使用 `--action move`，将待删除文件移动到 `.trash/` 文件夹中供人工复核。

`<a id="sec-3-4"></a>`

### 3.4 人工核验（网页）（已弃用，可以后续做数据验证）

- **目的**: 在并入主数据集前进行人工快速抽查/核验，剔除无关或版权不明的图片。
- **工具**: [`docs/pest_manual_review.html`](docs/pest_manual_review.html:1) (前端) + [`scripts/pest_review_server.py`](scripts/pest_review_server.py:1) (后端)。
- **流程**:
  1. 使用 `scripts/generate_pest_review_manifest.py` 生成待审核图片清单。
  2. 启动 `pest_review_server.py` 后端服务，它会加载 VLM 模型进行智能分析。
  3. 在浏览器中打开 `pest_manual_review.html`，进行批量审核、分析和标记。
  4. 审核完成后，导出审核结果 JSON 文件。
  5. 使用 `scripts/import_reviewed_pests.py` 或 `scripts/import_llm_verified_scraped.py` 将通过审核的图片正式导入 `datasets/` 目录。

`<a id="sec-3-5"></a>`

### 3.5 LLM 语义验证与描述增强（已经用llm替代人工核验）

- **目的**: 利用多模态大模型（VLM）对图像进行最后一次智能审核，确保内容与标签匹配，并生成更丰富的描述。
- **脚本**: [`llm_tools/verify_and_describe.py`](llm_tools/verify_and_describe.py:1)
- **核心功能**:

  - **并发处理**: 利用多线程并发调用 VLM API，大幅提升处理速度。
  - **语义验证与质量过滤**: 自动隔离内容不符或质量低下的图片。
  - **描述增强**: 为通过验证的图片生成中英双语描述，并存为 `.json` 元数据文件。
  - **智能分类**: 将验证失败的图片根据模型判断的 `actual_class` 归类到 `.rejected_by_llm/` 目录，为数据挽救提供可能。

`<a id="sec-3-6"></a>`

### 3.6 生成数据索引 (JSONL)

- **目的**: 为清洗干净的数据集生成包含多模态标注的 `data.jsonl` 索引文件。
- **脚本**: [`scripts/build_jsonl.py`](scripts/build_jsonl.py:1)
- **核心功能**:
  - 扫描 `datasets/` 下的所有图像及其 `.json` 元数据。
  - 根据文件名和本体，自动生成中英双语的 **Caption** 和 **VQA** 样本。
  - 若存在 LLM 生成的 `.json` 文件，则优先使用其中更高质量的文本描述。
  - 按类别进行分层抽样，划分 `train`, `val`, `test` 集。
  - 支持 `--holdout-source <src>` 仅导出指定来源样本（如 `web`），用于跨来源测试集构建，并且已经生成了一个data_holdout_web.jsonl。

`<a id="sec-3-7"></a>`

### 3.7 数据采集策略

- **目的**: 为缺失或数据量不足的类别补充高质量图片。
- **主力数据源**: **GBIF / iNaturalist**。通过 `agri_sites` 爬虫 (`web_scraper/scraper/spiders/agriculture_sites_spider.py`) 访问，是专业生物学数据库，图片质量高且有科学分类，特别适合害虫、植物病害等专业类别。
- **补充数据源**: **Unsplash API**。通过 `unsplash_api` 爬虫 (`web_scraper/scraper/spiders/unsplash_api_spider.py`) 访问，图片艺术质量高，适合通用农业场景，但有速率限制 (50次/小时)。
- **备选方案**: **Pixabay API** 和 **Pexels API**。两者均为免费、高质量的图片库，API 限制宽松，是未来可考虑的优秀补充数据源。

---

`<a id="sec-4"></a>`

## 4. 模型训练与评测路线图（仅建议）

- **视觉编码器选型**: 推荐 `CLIP/SigLIP ViT-L/14`, `EVA-02`, `CoCa` 等。输入分辨率建议 **≥ 448x448**。
- **多模态架构选型**: 推荐 `LLaVA`, `InternVL`, `Qwen-VL`, `InstructBLIP` 等。
- **训练策略**: 建议采用三阶段训练范式：1) 视觉-文本对齐预训练 (Caption) → 2) 指令微调 (VQA) → 3) 下游任务微调。
- **评测指标**: 分类任务 (Top-1/Top-5 准确率)、VQA 任务 (EM/F1 分数)，并进行混淆矩阵、跨域泛化和失效分析。

---

`<a id="sec-5"></a>`

## 5. 未来规划与待办事项 (TODOs)

### 数据集优化建议 📊

#### 已完成任务 ✅

- ✅ **跨来源测试集 (web holdout, 2025-11-06)**: 生成 `data_holdout_web.jsonl`，仅含 `web` 来源样本（约 133,133 条），用于跨来源泛化评估。

#### 待完成任务

- `[ ]` **统计报告生成**: 按类别和来源输出CSV详细报告
- `[ ]` **数据质量审计**:
  - EXIF方向修正
  - sRGB颜色空间标准化
  - 命名规范校验器

### 模型训练准备 🚀

数据集已就绪,可直接用于:

1. 基线模型训练 (LLaVA/InternVL/Qwen-VL)
2. 多模态预训练实验
3. Caption生成任务 (99.8% LLM高质量描述)
4. 视觉问答任务 (VQA)
5. 数据集公开发布准备 (README, LICENSE, 统计报告)

---

`<a id="data-sources"></a>`

## 数据来源与合并历史（概览）

1. **Agricultural-crops**: [Kaggle Link](https://www.kaggle.com/datasets/mdwaquarazam/agricultural-crops-image-classification)
2. **agricultural-pests-image-dataset**: [Kaggle Link](https://www.kaggle.com/datasets/vencerlanz09/agricultural-pests-image-dataset)
3. **Agriculture crop images**: [Kaggle Link](https://www.kaggle.com/datasets/aman2000jaiswal/agriculture-crop-images/data?select=test_crop_image)
4. **PlantDoc-Dataset**: [GitHub Link](https://github.com/pratikkayal/PlantDoc-Dataset/tree/master)
5. **Agriculture Crops Dataset**: [Kaggle Link](https://www.kaggle.com/datasets/osamajalilhassan/agriculture-crops-dataset)
6. **Top Agriculture Crop Disease**: [Kaggle Link](https://www.kaggle.com/datasets/kamal01/top-agriculture-crop-disease)
7. **140-most-popular-crops-image-dataset**: [Kaggle Link](https://www.kaggle.com/datasets/omrathod2003/140-most-popular-crops-image-dataset)
8. **PlantVillage Dataset**: [Kaggle Link](https://www.kaggle.com/datasets/abdallahalidev/plantvillage-dataset) (License: CC BY-NC-SA 4.0)
9. **New Plant Diseases / Plant Pathology**: Kaggle 数据与竞赛数据集汇总。

> 时间线与关键处理日志已迁移至精简文档：`docs/timeline.md`。此处仅保留数据源概览以避免文档膨胀。

---

`<a id="app-b"></a>`

## 附录 B：中英文类目总表 (Ontology)

这是项目的核心本体，定义了所有目录和类别的中英文标准名称。

- **根目录**:

  - `datasets/crops`: 农作物 (Crops)
  - `datasets/pests`: 害虫 (Pests)
  - `datasets/diseases`: 病害 (Diseases)
- **Diseases 目录**:

  - `Apple Scab Leaf`: 苹果黑星病
  - `Apple leaf`: 苹果叶
  - `Apple rust leaf`: 苹果锈病叶
  - `Bell_pepper leaf`: 甜椒叶
  - `Bell_pepper leaf spot`: 甜椒叶斑病
  - `Blueberry leaf`: 蓝莓叶
  - `Cherry leaf`: 樱桃叶
  - `Corn Gray leaf spot`: 玉米灰斑病
  - `Corn leaf`: 玉米叶
  - `Corn leaf blight`: 玉米叶枯病
  - `Corn rust leaf`: 玉米锈病叶
  - `Peach leaf`: 桃叶
  - `Potato leaf`: 马铃薯叶
  - `Potato leaf early blight`: 马铃薯早疫病
  - `Potato leaf late blight`: 马铃薯晚疫病
  - `Raspberry leaf`: 覆盆子叶
  - `Rice brown spot`: 稻褐斑病
  - `Rice leaf`: 稻叶
  - `Rice leaf blast`: 稻叶稻瘟病
  - `Rice neck blast`: 稻穗颈稻瘟病
  - `Soyabean leaf`: 大豆叶
  - `Squash Powdery mildew leaf`: 南瓜白粉病叶
  - `Strawberry leaf`: 草莓叶
  - `Sugarcane bacterial blight`: 甘蔗细菌性叶枯病
  - `Sugarcane leaf`: 甘蔗叶
  - `Sugarcane red rot`: 甘蔗红腐病
  - `Tomato Early blight leaf`: 番茄早疫病叶
  - `Tomato Septoria leaf spot`: 番茄叶斑病（Septoria）
  - `Tomato leaf`: 番茄叶
  - `Tomato leaf bacterial spot`: 番茄细菌性斑点病
  - `Tomato leaf late blight`: 番茄晚疫病叶
  - `Tomato leaf mosaic virus`: 番茄花叶病毒
  - `Tomato leaf yellow virus`: 番茄黄化病毒叶
  - `Tomato mold leaf`: 番茄霉病叶
  - `Tomato two spotted spider mites leaf`: 番茄二斑叶螨危害叶
  - `Wheat brown rust`: 小麦褐锈病
  - `Wheat leaf`: 小麦叶
  - `Wheat yellow rust`: 小麦黄锈病
  - `grape leaf`: 葡萄叶
  - `grape leaf black rot`: 葡萄黑腐病
- **Crops 目录**:

  - `Cherry`: 樱桃
  - `Coffee-plant`: 咖啡树
  - `Cucumber`: 黄瓜
  - `Fox_nut(Makhana)`: 芡实（鸡头米）
  - `Lemon`: 柠檬
  - `Olive-tree`: 橄榄树
  - `Pearl_millet(bajra)`: 珍珠粟（Bajra）
  - `Tobacco-plant`: 烟草
  - `almond`: 杏仁（扁桃）
  - `banana`: 香蕉
  - `cardamom`: 小豆蔻
  - `chilli`: 辣椒
  - `clove`: 丁香
  - `coconut`: 椰子
  - `cotton`: 棉花
  - `gram`: 鹰嘴豆（Gram）
  - `jowar`: 高粱（Jowar）
  - `jute`: 黄麻
  - `maize`: 玉米
  - `mustard-oil`: 芥籽（油用）
  - `papaya`: 木瓜
  - `pineapple`: 菠萝
  - `rice`: 稻（大米）
  - `soyabean`: 大豆（脚本同时识别 `soybean` 变体）
  - `sugarcane`: 甘蔗
  - `sunflower`: 向日葵
  - `tea`: 茶树
  - `tomato`: 番茄
  - `vigna-radiati(Mung)`: 绿豆（豇豆属）
  - `wheat`: 小麦
- **Pests 目录**:

  - `ants`: 蚂蚁
  - `bees`: 蜜蜂
  - `beetle`: 甲虫
  - `caterpillar`: 毛虫（鳞翅目幼虫）
  - `earthworms`: 蚯蚓
  - `earwig`: 蠼螋
  - `grasshopper`: 蝗虫
  - `moth`: 蛾
  - `slug`: 鼻涕虫
  - `snail`: 蜗牛
  - `wasp`: 黄蜂
  - `weevil`: 象鼻虫
