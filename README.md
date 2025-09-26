# 数据集网络项目 (清晰布局)

这是一个用于管理和处理图像数据集的项目，特别适用于农作物病虫害等分类任务。项目提供了一系列脚本来帮助用户进行数据集的合并、重命名、清洗和索引等操作。

## 项目结构

- `scripts/`: 存放数据集处理的实用工具脚本，例如合并、重命名、清洗和索引。
- `docs/`: 包含数据来源、处理日志和操作说明等相关文档。
- `datasets/`: 存放合并后的图像数据，按作物、害虫或病害等类别进行组织。
- `mappings/`: 包含源类别到目标类别的映射文件以及合并报告。

## 快速开始

1.  **重命名文件夹**:
    ```bash
    python3 scripts/bulk_rename_by_class.py --root datasets/diseases --tag pd
    ```

2.  **清洗图像** (安全移动模式):
    ```bash
    python3 scripts/deduplicate_images.py --roots datasets/crops datasets/diseases datasets/pests --min-width 224 --min-height 224 --blur-threshold 60 --action move
    ```

3.  **构建 JSONL 索引文件**:
    ```bash
    python3 scripts/build_jsonl.py --roots datasets/diseases datasets/crops datasets/pests --out data.jsonl --train 0.8 --val 0.1 --test 0.1 --seed 42
    ```

## 脚本说明

- `bulk_rename_by_class.py`: 根据类别批量重命名文件。
    - `--root`: 数据集根目录。
    - `--tag`: 添加到文件名的标签。
- `deduplicate_images.py`: 清洗图像，去除重复、低质量（尺寸过小、模糊）的图片。
    - `--roots`: 一个或多个数据集的根目录。
    - `--min-width`, `--min-height`: 图像的最小宽度和高度。
    - `--blur-threshold`: 模糊度阈值，低于此值的图像将被视为模糊。
    - `--action`: 操作类型，`move` 表示移动到 `.trash` 文件夹，`delete` 表示直接删除。
- `build_jsonl.py`: 为数据集构建 JSONL 格式的索引文件，方便后续训练。
    - `--roots`: 一个或多个数据集的根目录。
    - `--out`: 输出的 JSONL 文件名。
    - `--train`, `--val`, `--test`: 训练集、验证集和测试集的划分比例。
    - `--seed`: 随机种子，用于保证划分结果的可复现性。

## 注意事项

- 所有合并操作都只是复制文件，不会修改原始数据。文件名中会通过 `__cd__`, `__pd__`, `__ac__`, `__ap__` 等标识符来保留其来源信息。
- 更多关于数据来源和处理过程的详细信息，请参阅 `docs/origin.md` 和 `docs/origin2.md`。
