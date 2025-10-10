# 农业多模态视觉数据集

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/status-active-green.svg" alt="Project Status">
  <a href="docs/documentation.md">
    <img src="https://img.shields.io/badge/docs-knowledge%20base-brightgreen.svg" alt="Documentation">
  </a>
</p>

## 项目概述

本项目构建了一个**高质量、大规模、多模态**的农业视觉知识库，为视觉语言模型（VLM）训练提供结构化数据支持。区别于传统图像分类数据集，每个样本均包含：

- **图像**: 经过质量筛选和去重的高分辨率农业图像
- **多模态标注**: 中英双语描述（Caption）+ 问答对（VQA）
- **结构化标签**: 标准化的作物、病害、害虫分类体系
- **完整溯源**: 通过文件名追溯数据来源

📖 **完整文档**: [`docs/documentation.md`](docs/documentation.md) | **API指南**: [`API_VERIFICATION_SUMMARY.md`](API_VERIFICATION_SUMMARY.md) | **抓取报告**: [`SCRAPING_SUMMARY.md`](SCRAPING_SUMMARY.md)

---

## 核心特性

### 1. 统一的本体标准（Ontology）
- ✅ 跨数据源的标准化分类体系
- ✅ 中英双语映射和学名支持
- ✅ 详见知识库附录完整类目表

### 2. 严格的质量控制
- ✅ 多维度去重（感知哈希 + 平均哈希）
- ✅ 模糊检测（Laplacian + Tenengrad算法）
- ✅ 尺寸过滤（最小224×224像素）
- ✅ 可选的LLM语义验证

### 3. 完整的数据溯源
- ✅ 标准化文件命名：`<类别>__<来源>__<uuid>.<ext>`
- ✅ 每张图片可追溯到原始数据源

### 4. 自动化处理流程
- ✅ 一键式数据合并、清洗、标注
- ✅ 并发LLM增强（可选）
- ✅ 人工审核Web界面

---

## 快速开始

### 1. 环境配置

```bash
# 安装依赖
pip install -r requirements.txt

# 配置LLM API（可选，用于语义验证）
cat > .env << EOF
VLM_API_KEY=sk-your-api-key-here
VLM_API_BASE=https://xmdbd.online/v1
VLM_MODEL=gemini-2.5-flash
VLM_WORKERS=8
EOF

# 载入环境变量
export $(grep -v '^#' .env | xargs)
```

### 2. 数据集结构

```
datasets/
├── crops/         # 作物图像（140+类别）
├── pests/         # 害虫图像（13+类别）
└── diseases/      # 病害图像（50+类别）
```

**文件命名规范**: `<类别>__<来源>__<uuid>.<ext>`
- `<类别>`: 标准化英文类别名（小写，空格用下划线替代）
- `<来源>`: 数据源标识（如 `pd`=PlantDoc, `web`=网络爬虫）
- `<uuid>`: 唯一标识符

**示例**: `corn_rust_leaf__pd__a3f2e1b9.jpg`

---

## 标准化处理流程

### 阶段 1: 数据采集与合并

#### 1.1 本地数据集合并

将已有数据集合并到标准目录结构：

```bash
# 合并 Crop Diseases 数据集
python3 scripts/merge_crop_diseases.py

# 合并 140 Crops 数据集
python3 scripts/merge_140_crops.py

# 合并 Kaggle 病害数据集
python3 scripts/merge_kaggle_disease.py
```

#### 1.2 网络爬虫采集

**推荐数据源** (按优先级):
1. **GBIF/iNaturalist**: 专业生物学数据库（主力）
2. **Unsplash API**: 高质量通用图片（补充）
3. **Wikimedia Commons**: 开放图片库（备用）

```bash
# 使用 GBIF/iNaturalist 爬虫
cd web_scraper
../.venv/bin/scrapy crawl agri_sites \
    -a keywords_file=keywords_pest_species.txt \
    -a max_api_results=150

# 使用 Unsplash API 补充
export UNSPLASH_API_KEY="your-api-key"
../.venv/bin/scrapy crawl unsplash_api \
    -a keywords_file=keywords_missing_priority.txt \
    -a max_pages=5 -a per_page=30
```

> 📋 详细的API配置和使用指南请参阅 [`API_VERIFICATION_SUMMARY.md`](API_VERIFICATION_SUMMARY.md)

### 阶段 2: 数据标准化

#### 2.1 文件名标准化

对不规范的文件名进行统一重命名（可安全重复运行）：

```bash
python3 scripts/bulk_rename_by_class.py \
    --root datasets/diseases \
    --tag pd
```

#### 2.2 统计当前数据量

```bash
python3 scripts/count_images_by_class.py \
    --roots datasets/diseases datasets/crops datasets/pests
```

### 阶段 3: 质量控制

#### 3.1 去重与质量过滤

**首次运行建议使用 `--action move`** 以便检查被移除的文件：

```bash
python3 scripts/deduplicate_images.py \
    --roots datasets/diseases datasets/crops datasets/pests \
    --min-width 224 --min-height 224 \
    --blur-method both \
    --blur-threshold 60 \
    --tenengrad-threshold 700 \
    --ham-threshold 3 \
    --near-scope class \
    --action move
```

**参数说明**:
- `--min-width/height`: 最小尺寸要求
- `--blur-method`: 模糊检测算法（`laplacian`|`tenengrad`|`both`）
- `--blur-threshold`: Laplacian方差阈值（<60视为模糊）
- `--tenengrad-threshold`: Tenengrad梯度阈值（<700视为模糊）
- `--ham-threshold`: 汉明距离阈值（<=3视为重复）
- `--near-scope`: 去重范围（`all`|`category`|`class`）
- `--action`: 处理方式（`move`|`delete`|`dry-run`）

检查 `.trash/` 目录后，确认无误可永久删除：

```bash
rm -rf datasets/*/.trash
```

#### 3.2 人工审核（Web界面）

针对爬虫数据进行快速人工审核：

```bash
# 启动审核服务器
python3 scripts/pest_review_server.py \
    --root web_scraper/scraped_images

# 在浏览器中打开
open docs/pest_manual_review.html
```

审核完成后导出JSON文件，然后导入到正式数据集：

```bash
python3 scripts/import_reviewed_pests.py \
    --review-json path/to/review.json \
    --tag web
```

#### 3.3 LLM语义验证（可选，推荐）

使用多模态大模型进行语义一致性验证和描述增强：

```bash
# 干跑模式（仅日志）
python3 llm_tools/verify_and_describe.py \
    --root datasets/diseases \
    --action dry-run \
    --workers 8 \
    --insecure

# 实际运行（生成 .json 描述文件）
python3 llm_tools/verify_and_describe.py \
    --root datasets/diseases \
    --model gemini-2.5-flash \
    --workers 8 \
    --insecure
```

**注意**: 
- 不匹配的图片会被移至 `.rejected_by_llm/` 目录
- 通过验证的图片旁生成同名 `.json` 描述文件
- 当前服务端证书未完善时需加 `--insecure` 参数
- 详细配置请参阅 [`llm_tools/README.md`](llm_tools/README.md)

### 阶段 4: 生成数据索引

生成包含多模态标注的JSONL格式索引文件：

```bash
python3 scripts/build_jsonl.py \
    --roots datasets/diseases datasets/crops datasets/pests \
    --out data.jsonl \
    --train 0.8 --val 0.1 --test 0.1 \
    --seed 42
```

---

## 数据索引格式

生成的 `data.jsonl` 文件每行为一个JSON对象，包含以下字段：

```json
{
  "image": "datasets/diseases/corn_rust_leaf__pd__a3f2e1b9.jpg",
  "task": "caption",
  "text": "这是一张玉米锈病叶片的照片。This is a photo of corn rust leaf.",
  "split": "train",
  "labels": {
    "category": "diseases",
    "crop": "corn",
    "disease": "rust",
    "source": "pd",
    "class": "corn rust leaf"
  }
}
```

**任务类型**:
- `caption`: 图像描述任务（中英双语）
- `vqa`: 视觉问答任务（包含 `answer` 字段）

**数据集划分**:
- `train`: 训练集（默认80%）
- `val`: 验证集（默认10%）
- `test`: 测试集（默认10%）

示例文件: [`data.sample.jsonl`](data.sample.jsonl)

---

## 脚本工具参考

### 数据合并
| 脚本 | 功能 | 用法 |
|------|------|------|
| `merge_crop_diseases.py` | 合并Crop Diseases数据集 | `python3 scripts/merge_crop_diseases.py` |
| `merge_140_crops.py` | 合并140 Crops数据集 | `python3 scripts/merge_140_crops.py` |
| `merge_kaggle_disease.py` | 合并Kaggle病害数据集 | `python3 scripts/merge_kaggle_disease.py` |

### 数据处理
| 脚本 | 功能 | 用法 |
|------|------|------|
| `bulk_rename_by_class.py` | 批量规范化文件名 | `--root <目录> --tag <来源>` |
| `deduplicate_images.py` | 去重与质量过滤 | `--roots <目录列表> --action <动作>` |
| `count_images_by_class.py` | 统计各类别图片数量 | `--roots <目录列表>` |

### 审核工具
| 脚本 | 功能 | 用法 |
|------|------|------|
| `pest_review_server.py` | 启动审核服务器 | `--root <目录> [--port 8765]` |
| `generate_pest_review_manifest.py` | 生成审核清单 | `--root <目录> --out <输出>` |
| `import_reviewed_pests.py` | 导入审核通过的数据 | `--review-json <文件> --tag <来源>` |

### 索引生成
| 脚本 | 功能 | 用法 |
|------|------|------|
| `build_jsonl.py` | 生成JSONL索引 | `--roots <目录列表> --out <输出>` |

### LLM增强
| 脚本 | 功能 | 用法 |
|------|------|------|
| `verify_and_describe.py` | LLM语义验证与描述增强 | `--root <目录> --workers <并发数>` |

> 📖 所有脚本均支持 `--help` 参数查看详细用法

---

## 项目结构

```
dataset_web/
├── datasets/                 # 数据集主目录
│   ├── crops/               # 作物图像
│   ├── pests/               # 害虫图像
│   └── diseases/            # 病害图像
├── scripts/                 # 数据处理脚本
│   ├── merge_*.py          # 数据合并脚本
│   ├── deduplicate_images.py
│   ├── bulk_rename_by_class.py
│   ├── build_jsonl.py
│   └── ...
├── llm_tools/              # LLM增强工具
│   ├── verify_and_describe.py
│   └── README.md
├── web_scraper/            # 网络爬虫
│   ├── spiders/           # Scrapy爬虫
│   └── scraped_images/    # 爬取的图片
├── docs/                   # 项目文档
│   ├── documentation.md   # 核心知识库
│   └── pest_manual_review.html
├── mappings/              # 类别映射表
├── data.jsonl            # 完整数据索引
├── data.sample.jsonl     # 示例数据
└── requirements.txt      # Python依赖
```

---

## 数据源说明

### 已集成数据源
- **PlantDoc** (`pd`): 植物病害专业数据集
- **Kaggle Datasets** (`kaggle`): 多个Kaggle农业数据集
- **140 Crops** (`140crops`): 作物分类数据集
- **GBIF/iNaturalist** (`web`): 网络爬虫采集
- **Unsplash** (`web`): 高质量图片补充

### 数据质量统计（截至2025-10-08）
详见 [`DATASET_STATUS_20251008.md`](DATASET_STATUS_20251008.md)

---

## 常见问题

### Q1: 如何添加新的数据源？

1. 将数据复制到临时目录
2. 使用 `bulk_rename_by_class.py` 规范化文件名（指定新的 `--tag`）
3. 运行 `deduplicate_images.py` 去重
4. 可选：运行 LLM 语义验证
5. 运行 `build_jsonl.py` 更新索引

### Q2: 如何处理LLM拒绝的图片？

LLM拒绝的图片会被移至 `.rejected_by_llm/` 目录，建议：
1. 人工复审该目录
2. 确认误判的图片移回原位
3. 确认正确拒绝的图片可永久删除

### Q3: 如何自定义Caption模板？

编辑 `scripts/build_jsonl.py` 中的 `make_caption_samples()` 和 `make_vqa_samples()` 函数。

如果存在 `.json` 元数据文件（由LLM生成），会优先使用其中的描述。

### Q4: 爬虫采集的图片质量如何保证？

建议采用以下流程：
1. 使用专业数据源（GBIF/iNaturalist）而非通用搜索引擎
2. 运行 `deduplicate_images.py` 进行质量过滤
3. 使用Web界面进行人工抽查审核
4. 可选：运行LLM语义验证

### Q5: 如何配置并发数和超时？

LLM工具支持以下环境变量：
```bash
export VLM_WORKERS=8          # 并发线程数
export VLM_TIMEOUT=120        # API超时（秒）
export VLM_VERIFY_SSL=false   # 禁用SSL验证
```

---

## 许可证

本项目采用 [MIT License](LICENSE)。

**注意**: 请确保遵守各数据源的原始许可证条款。本项目仅用于学术研究目的。

---

## 相关文档

- 📖 [完整项目文档](docs/documentation.md) - 设计理念、本体定义、处理历史
- 🔧 [API验证报告](API_VERIFICATION_SUMMARY.md) - 数据源API可用性分析
- 📊 [抓取工作总结](SCRAPING_SUMMARY.md) - 网络爬虫采集成果报告
- 🤖 [LLM工具指南](llm_tools/README.md) - 语义验证与描述增强详解
- 📈 [数据集状态](DATASET_STATUS_20251008.md) - 当前数据量统计

---

**最后更新**: 2025-10-10 | **维护者**: ECCV Dataset Team
