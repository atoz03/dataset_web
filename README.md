<div align="center">

# 🌾 农业多模态视觉数据集整合

<p align="center">
  <strong>高质量 · 大规模 · 多模态</strong><br>
  为视觉语言模型训练而生的农业知识库
</p>

<p align="center">
  <a href="#-特性亮点">特性</a> •
  <a href="#-快速开始">快速开始</a> •
  <a href="#-数据流水线">流水线</a> •
  <a href="#-文档">文档</a> •
  <a href="#-贡献">贡献</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
  <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/multilingual-中文%20%7C%20English-green.svg" alt="Multilingual">
</p>

<br>

</div>

---

## 📦 数据发布与获取（重要说明）

- 本仓库目前提供数据处理脚本、文档与格式示例，不包含完整图像数据集，暂未提供公开下载地址。
- [`data.sample.jsonl`](data.sample.jsonl) 只包含**合成示例记录**，其中的图片路径仅用于展示字段结构，不对应仓库内的真实图片，也不能直接用于训练。
- 如需处理自己的数据，请按 [项目文档](docs/documentation.md) 准备图片目录与配置。未来若发布公开数据，将在这里补充实际下载链接。

## 🎯 项目愿景

> 从单一的图像分类到丰富的多模态理解

传统农业数据集仅提供 **图像 + 标签**，而本项目构建的是一个完整的**知识库**：

```
传统数据集:  🖼️ Image → 🏷️ Label
本项目:     🖼️ Image → 📝 Caption → 💬 VQA → 🏷️ Structured Labels → 🔍 Traceability
```

<table>
<tr>
<td width="50%">

### 🎨 多模态标注
- 中英双语图像描述
- 视觉问答对（VQA）
- 结构化标签体系

</td>
<td width="50%">

### 🎓 学术级质量
- 多维度去重算法
- 模糊检测与过滤
- LLM语义验证

</td>
</tr>
<tr>
<td width="50%">

### 🌐 完整溯源
- 标准化命名规范
- 数据源可追溯
- 版权清晰合规

</td>
<td width="50%">

### 🤖 AI驱动
- 自动化处理流程
- 并发LLM增强
- Web审核界面

</td>
</tr>
</table>

---

## ✨ 特性亮点

<div align="center">

| 🏗️ 统一本体 | 🔍 质量控制 | 🚀 自动化 | 📊 可视化 |
|:---:|:---:|:---:|:---:|
| 跨数据源<br>标准化体系 | 感知哈希<br>模糊检测 | 一键式<br>处理流程 | Web界面<br>人工审核 |
| 中英双语<br>学名映射 | 尺寸过滤<br>LLM验证 | 并发处理<br>高效能 | 实时统计<br>进度追踪 |

</div>

---

## 📊 数据集概览

<div align="center">

### 📈 数据规模与发布范围

</div>

历史规模统计见 [项目时间线](docs/timeline.md)。不同阶段清洗与去重口径可能不同；当前仓库没有公开完整图片数据及对应的可验证清单，因此不再将历史规模展示为当前可获取数据量。

<div align="center">

### 🗂️ 数据源

</div>

<table align="center">
<tr>
<th>数据源</th>
<th>类型</th>
<th>特点</th>
<th>标识</th>
</tr>
<tr>
<td>🏛️ <b>PlantDoc</b></td>
<td>专业数据集</td>
<td>植物病害，高质量标注</td>
<td><code>pd</code></td>
</tr>
<tr>
<td>🏆 <b>Kaggle</b></td>
<td>竞赛数据集</td>
<td>多源聚合，品类丰富</td>
<td><code>kaggle</code></td>
</tr>
<tr>
<td>🌍 <b>GBIF/iNaturalist</b></td>
<td>生物学数据库</td>
<td>学名准确，专业级</td>
<td><code>web</code></td>
</tr>
<tr>
<td>📷 <b>Unsplash</b></td>
<td>高质量图片</td>
<td>美学优秀，通用场景</td>
<td><code>web</code></td>
</tr>
</table>

---

## 🚀 快速开始

<details open>
<summary><b>📦 1. 安装依赖</b></summary>

```bash
# 克隆项目
git clone https://github.com/atoz03/dataset_web.git
cd dataset_web

# 安装依赖
pip install -r requirements.txt
```

</details>

<details open>
<summary><b>⚙️ 2. 配置环境（可选）</b></summary>

```bash
# 创建配置文件（用于LLM增强功能）
cat > .env << EOF
VLM_API_KEY=sk-your-api-key-here
VLM_API_BASE=https://your-provider.example/v1  # 请替换为实际 API 端点
VLM_MODEL=gemini-2.5-flash
VLM_WORKERS=8
EOF

# 载入环境变量
export $(grep -v '^#' .env | xargs)
```

</details>

<details open>
<summary><b>🎬 3. 运行演示</b></summary>

```bash
# 统计当前数据集
python3 scripts/03_cleaning/count_images_by_class.py \
    --roots datasets/diseases datasets/crops datasets/pests

# 查看合成格式示例（不包含真实图片）
head -n 5 data.sample.jsonl | jq -c .
```

</details>

---

## 🔄 数据流水线

<div align="center">

```mermaid
graph LR
    A[📥 数据采集] --> B[🏷️ 标准化]
    B --> C[🔍 质量控制]
    C --> D[🤖 LLM增强]
    D --> E[✅ 人工审核]
    E --> F[📊 生成索引]
    
    style A fill:#e1f5ff
    style B fill:#fff4e1
    style C fill:#ffe1e1
    style D fill:#f0e1ff
    style E fill:#e1ffe1
    style F fill:#ffe1f0
```

</div>

### 🎯 阶段 1: 数据采集

<table>
<tr>
<td width="50%">

#### 📁 本地数据合并

```bash
# 合并已有数据集
python3 scripts/02_ingest_and_merge/merge_crop_diseases.py
python3 scripts/02_ingest_and_merge/merge_140_crops.py
python3 scripts/02_ingest_and_merge/merge_kaggle_disease.py
```

</td>
<td width="50%">

#### 🌐 网络爬虫采集

```bash
# GBIF/iNaturalist 爬虫
cd web_scraper
scrapy crawl agri_sites \
  -a keywords_file=keywords.txt \
  -a max_api_results=150
```

</td>
</tr>
</table>

### 🎯 阶段 2: 标准化处理

<details>
<summary><b>📝 文件名标准化</b></summary>

```bash
python3 scripts/03_cleaning/bulk_rename_by_class.py \
    --root datasets/diseases \
    --tag pd
```

**命名规范**: `<类别>__<来源>__<uuid>.<ext>`

**示例**: `corn_rust_leaf__pd__a3f2e1b9.jpg`

</details>

### 🎯 阶段 3: 质量控制

<details>
<summary><b>🔍 智能去重与过滤</b></summary>

```bash
python3 scripts/03_cleaning/deduplicate_images.py \
    --roots datasets/diseases datasets/crops datasets/pests \
    --min-width 224 --min-height 224 \
    --blur-method both \
    --blur-threshold 60 \
    --tenengrad-threshold 700 \
    --ham-threshold 3 \
    --near-scope class \
    --action move
```

<table>
<tr>
<th>检测算法</th>
<th>阈值</th>
<th>说明</th>
</tr>
<tr>
<td>🖼️ 感知哈希</td>
<td>≤3</td>
<td>基于视觉相似度的去重</td>
</tr>
<tr>
<td>📐 平均哈希</td>
<td>≤3</td>
<td>快速粗粒度去重</td>
</tr>
<tr>
<td>🌫️ Laplacian</td>
<td>&lt;60</td>
<td>检测模糊图像</td>
</tr>
<tr>
<td>🔬 Tenengrad</td>
<td>&lt;700</td>
<td>梯度方差模糊检测</td>
</tr>
<tr>
<td>📏 尺寸过滤</td>
<td>224×224</td>
<td>最小分辨率要求</td>
</tr>
</table>

</details>

<details>
<summary><b>👁️ 人工审核界面</b></summary>

```bash
# 启动Web审核服务器
python3 scripts/03_cleaning/pest_review_server.py \
    --root web_scraper/scraped_images

# 浏览器打开审核页面
open docs/pest_manual_review.html
```

**特性**:
- ✅ 可视化批量审核
- ✅ 按类别分组查看
- ✅ 快速标记通过/剔除
- ✅ 导出审核结果JSON

</details>

### 🎯 阶段 4: LLM增强（可选）

<details>
<summary><b>🤖 语义验证与描述增强</b></summary>

```bash
# 干跑模式（仅日志，不修改文件）
python3 llm_tools/verify_and_describe.py \
    --root datasets/diseases \
    --action dry-run \
    --workers 8

# 实际运行
python3 llm_tools/verify_and_describe.py \
    --root datasets/diseases \
    --model gemini-2.5-flash \
    --workers 8
```

**工作流程**:

```mermaid
graph TD
    A[📁 输入图片] --> B{🤖 LLM验证}
    B -->|✅ 匹配| C[生成描述.json]
    B -->|❌ 不匹配| D[移至.rejected_by_llm/]
    C --> E[📊 用于build_jsonl]
    D --> F[👁️ 人工复审]
```

</details>

### 🎯 阶段 5: 生成索引

<details>
<summary><b>📊 生成JSONL数据索引</b></summary>

```bash
python3 scripts/05_index_and_stats/build_jsonl.py \
    --roots datasets/diseases datasets/crops datasets/pests \
    --out data.jsonl \
    --train 0.8 --val 0.1 --test 0.1 \
    --seed 42
```

**输出格式**（合成示例记录，不包含实际图片文件）：

```json
{
  "image": "datasets/diseases/corn_rust_leaf__pd__example.jpg",
  "task": "caption",
  "text": "这是一张玉米锈病叶片的照片。",
  "lang": "zh",
  "labels": {
    "root": "diseases",
    "class": "Corn rust leaf",
    "crop": "Corn",
    "disease": "rust",
    "pest": null,
    "healthy": false,
    "source": "pd"
  },
  "split": "train"
}
```

</details>

---

## 🛠️ 工具箱

<div align="center">

### 核心脚本一览

</div>

<table>
<tr>
<th>类别</th>
<th>脚本</th>
<th>功能</th>
<th>关键参数</th>
</tr>
<tr>
<td rowspan="3">📦 <b>数据合并</b></td>
<td><code>merge_crop_diseases.py</code></td>
<td>合并Crop Diseases数据集</td>
<td>-</td>
</tr>
<tr>
<td><code>merge_140_crops.py</code></td>
<td>合并140 Crops数据集</td>
<td>-</td>
</tr>
<tr>
<td><code>merge_kaggle_disease.py</code></td>
<td>合并Kaggle病害数据集</td>
<td>-</td>
</tr>
<tr>
<td rowspan="3">🔧 <b>数据处理</b></td>
<td><code>bulk_rename_by_class.py</code></td>
<td>批量规范化文件名</td>
<td><code>--root --tag</code></td>
</tr>
<tr>
<td><code>deduplicate_images.py</code></td>
<td>智能去重与质量过滤</td>
<td><code>--roots --action</code></td>
</tr>
<tr>
<td><code>count_images_by_class.py</code></td>
<td>统计各类别数量</td>
<td><code>--roots</code></td>
</tr>
<tr>
<td rowspan="3">👁️ <b>审核工具</b></td>
<td><code>pest_review_server.py</code></td>
<td>启动Web审核服务器</td>
<td><code>--root --port</code></td>
</tr>
<tr>
<td><code>generate_pest_review_manifest.py</code></td>
<td>生成审核清单</td>
<td><code>--root --out</code></td>
</tr>
<tr>
<td><code>import_reviewed_pests.py</code></td>
<td>导入审核通过的数据</td>
<td><code>--review-json --tag</code></td>
</tr>
<tr>
<td rowspan="2">🤖 <b>AI增强</b></td>
<td><code>verify_and_describe.py</code></td>
<td>LLM语义验证与描述增强</td>
<td><code>--root --workers</code></td>
</tr>
<tr>
<td><code>build_jsonl.py</code></td>
<td>生成JSONL索引</td>
<td><code>--roots --out</code></td>
</tr>
</table>

> 💡 **提示**: 所有脚本均支持 `--help` 查看详细用法

---

## 📁 项目结构

```
dataset_web/
├── 📦 datasets/                  # 数据集主目录
│   ├── 🌱 crops/                # 作物图像（需自行准备）
│   ├── 🐛 pests/                # 害虫图像（需自行准备）
│   └── 🍂 diseases/             # 病害图像（需自行准备）
│
├── 🛠️ scripts/                  # 数据处理与流水线脚本（分阶段）
│   ├── 01_scraping/            # 图片抓取与爬虫编排
│   ├── 02_ingest_and_merge/    # 外部数据集下载与合并
│   ├── 03_cleaning/            # 命名标准化、去重与质量清洗
│   ├── 04_llm_enhancement/     # LLM 任务监控与队列管理
│   └── 05_index_and_stats/     # JSONL 索引生成与统计报告
│
├── 🤖 llm_tools/                # LLM增强工具
│   ├── verify_and_describe.py # 语义验证
│   └── README.md               # 详细文档
│
├── 🕷️ web_scraper/              # 网络爬虫
│   ├── spiders/                # Scrapy爬虫集合
│   │   ├── agri_sites.py      # GBIF/iNaturalist
│   │   └── unsplash_api.py    # Unsplash API
│   └── scraped_images/         # 爬取图片暂存
│
├── 📚 docs/                     # 项目文档
│   ├── documentation.md        # 核心知识库
│   └── pest_manual_review.html # 审核界面
│
├── 🗺️ mappings/                 # 类别映射表
│   ├── crop_mappings.json      # 作物映射
│   ├── disease_mappings.json   # 病害映射
│   └── pest_mappings.json      # 害虫映射
│
├── 📊 data.jsonl                # 本地生成索引（不随仓库提供）
├── 📋 data.sample.jsonl         # 合成 JSONL 格式示例
└── 📄 requirements.txt          # Python依赖
```

---

## 📖 文档

- [完整项目文档](docs/documentation.md) — 数据处理流程、设计与配置说明。
- [项目时间线](docs/timeline.md) — 历史里程碑与统计记录。
- [LLM 工具指南](llm_tools/README.md) — 图像语义验证与描述增强。

---

## ❓ 常见问题

<details>
<summary><b>Q1: 如何添加新的数据源？</b></summary>

1. 将数据复制到临时目录
2. 使用 `bulk_rename_by_class.py` 规范化（指定新 `--tag`）
3. 运行 `deduplicate_images.py` 去重
4. 可选：运行 LLM 语义验证
5. 运行 `build_jsonl.py` 更新索引

</details>

<details>
<summary><b>Q2: LLM拒绝的图片如何处理？</b></summary>

被拒绝的图片会移至 `.rejected_by_llm/` 目录：

1. **人工复审**: 检查是否误判
2. **恢复误判**: 将误判图片移回原位
3. **删除确认**: 确认正确拒绝的可删除

</details>

<details>
<summary><b>Q3: 如何自定义Caption模板？</b></summary>

编辑 `scripts/05_index_and_stats/build_jsonl.py`:

- `make_caption_samples()` - Caption生成逻辑
- `make_vqa_samples()` - VQA生成逻辑

如存在 `.json` 元数据（LLM生成），会优先使用。

</details>

<details>
<summary><b>Q4: 如何保证爬虫数据质量？</b></summary>

推荐流程：

1. ✅ 使用专业数据源（GBIF优于通用搜索）
2. ✅ 运行 `deduplicate_images.py` 质量过滤
3. ✅ Web界面人工抽查审核
4. ✅ 可选LLM语义验证

</details>

<details>
<summary><b>Q5: 如何调整并发和超时？</b></summary>

通过环境变量配置：

```bash
export VLM_WORKERS=8          # 并发线程数
export VLM_TIMEOUT=120        # API超时（秒）
```

或命令行参数：`--workers 8 --timeout 120`。默认保持 TLS 证书校验；自签名证书应先配置可信 CA，不要把 `--insecure` 当作常规参数。

</details>

---

## 🤝 贡献

我们欢迎任何形式的贡献！

<table>
<tr>
<td width="33%">

### 🐛 报告问题
发现bug？请提交 [Issue](../../issues)

</td>
<td width="33%">

### 💡 功能建议
有好想法？欢迎讨论 [Discussions](../../discussions)

</td>
<td width="33%">

### 🔧 代码贡献
Fork → 修改 → 提交 [Pull Request](../../pulls)

</td>
</tr>
</table>

### 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📜 许可证

本项目采用 [MIT License](LICENSE) 开源。

**⚠️ 重要提示**: 
- 请遵守各数据源的原始许可证条款
- 本项目仅用于学术研究目的
- 商业使用前请确认合规性

---

## 🌟 致谢

<table>
<tr>
<td width="50%">

### 数据来源

- [PlantDoc](https://github.com/pratikkayal/PlantDoc-Dataset) - 植物病害数据集
- [Kaggle](https://www.kaggle.com) - 多源农业数据集
- [GBIF](https://www.gbif.org) - 全球生物多样性信息
- [iNaturalist](https://www.inaturalist.org) - 自然观察平台
- [Unsplash](https://unsplash.com) - 高质量图片资源

</td>
<td width="50%">

### 技术栈

- [Python](https://www.python.org) - 核心开发语言
- [Scrapy](https://scrapy.org) - 网络爬虫框架
- [Pillow](https://python-pillow.org) - 图像处理
- [NumPy](https://numpy.org) - 数值计算
- [OpenAI API](https://openai.com/api) - LLM增强

</td>
</tr>
</table>

---

