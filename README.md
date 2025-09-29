# 农业多模态视觉数据集项目

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/status-active-green.svg" alt="Project Status">
  <a href="docs/documentation.md">
    <img src="https://img.shields.io/badge/docs-knowledge%20base-brightgreen.svg" alt="Documentation">
  </a>
</p>

本项目旨在构建一个高质量、大规模、多模态的农业视觉知识库，而不仅仅是一个简单的图像分类数据集。我们致力于将每一张图片转化为包含丰富上下文信息的“**图像-文本对 + 标签**”样本，以支持更高级的视觉语言模型训练。

完整的项目设计、数据本体、处理历史和未来规划，请参阅我们的核心知识库：[`docs/documentation.md`](docs/documentation.md)。

---

## 核心理念

为保证数据集的质量和一致性，所有工作都遵循以下核心原则：

1.  **统一的多模态标注**: 每张图片都配有中英双语的描述（Caption）和问答对（VQA），以支持多模态训练。
2.  **统一的本体 (Ontology)**: 所有“作物”、“病害”等标签都经过规范化，确保跨数据源的一致性。详细类目表见知识库附录。
3.  **数据质量优先**: 通过严格的去重、模糊检测和尺寸过滤，剔除低质量样本。
4.  **完全可追溯**: 通过文件名中的来源标签，每一张图片都能追溯到其原始出处。

---

## 环境准备

首先，请安装项目所需的 Python 依赖包：

```bash
pip install -r requirements.txt
```

---

## 数据集架构

项目采用统一的分类目录结构，所有图像数据均存放在 `datasets/` 目录下：

```
datasets/
├── crops/      # 农作物图像
├── pests/      # 农业害虫图像
└── diseases/   # 植物病害图像
```

### 文件命名规范

所有数据集中的文件均遵循统一的命名格式（全部小写），以便于解析和溯源：

`<类别名>__<来源标签>__<uuid>.<ext>`

-   **`<类别名>`**: 标准化的英文类别名，例如 `corn rust leaf`。
-   **`<来源标签>`**: 数据来源标识，例如 `__pd__` 代表 PlantDoc。
-   **`<uuid>`**: 唯一的ID。

---

## 标准化工作流

我们推荐遵循以下标准化流程来处理和整合数据：

### 第 1 步：合并新数据源

采用“拷贝而非移动”的策略，使用 `scripts/merge_*.py` 脚本将新的数据源合并到 `datasets/` 目录中。

-   [`scripts/merge_crop_diseases.py`](scripts/merge_crop_diseases.py): 合并本地 `Crop Diseases` 数据集。
-   [`scripts/merge_140_crops.py`](scripts/merge_140_crops.py): 合并 `140-most-popular-crops` 数据集。
-   [`scripts/merge_kaggle_disease.py`](scripts/merge_kaggle_disease.py): 合并从 Kaggle 下载的病害数据集。

### 第 2 步：标准化文件名

对新合入的、文件名不规范的数据进行统一重命名。此脚本可安全重复运行。

```bash
python3 scripts/bulk_rename_by_class.py --root <目标目录> --tag <来源标签>
```
*示例*:
```bash
python3 scripts/bulk_rename_by_class.py --root datasets/diseases --tag pd
```

### 第 3 步：数据清洗

移除低质量（尺寸过小、模糊）和重复的图像。强烈建议首次运行时使用 `--action move` 进行安全操作，检查 `.trash/` 目录后再决定是否永久删除。

```bash
python3 scripts/deduplicate_images.py \
    --roots datasets/diseases datasets/crops datasets/pests \
    --min-width 224 --min-height 224 \
    --blur-threshold 60 \
    --action move
```

### 第 4 步：生成数据索引 (JSONL)

为清洗干净的数据集生成包含多模态标注的 `JSONL` 索引文件。该脚本会自动生成 Caption 和 VQA 样本，并划分训练/验证/测试集。

```bash
python3 scripts/build_jsonl.py \
    --roots datasets/diseases datasets/crops datasets/pests \
    --out data.sample.jsonl \
    --train 0.8 --val 0.1 --test 0.1 \
    --seed 42
```

---

## 数据索引 (`JSONL` 格式)

所有图像的元数据和文本标注都存储在 `JSONL` 文件中，每一行代表一个样本。其核心字段包括：

-   `image`: 图像的相对路径。
-   `task`: 任务类型 (`caption` 或 `vqa`)。
-   `text`: 任务文本（图像描述或问题）。
-   `answer`: `vqa` 任务的答案。
-   `split`: 数据集划分 (`train`, `val`, `test`)。
-   `labels`: 包含类别、作物、病害、来源等详细信息的对象。

一个 [`data.sample.jsonl`](data.sample.jsonl) 文件已包含在仓库中，可供查阅。

---

## 许可证

本项目采用 MIT 许可证。详情请参阅 [`LICENSE`](LICENSE) 文件。