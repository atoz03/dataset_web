# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

请读取核心知识库文件 documentation.md

---

## 项目概述

这是一个**农业多模态视觉数据集整合项目**,旨在构建高质量、大规模的农业知识库,用于训练视觉语言模型(VLM)。项目不仅提供图像分类数据,还生成丰富的多模态标注(中英双语Caption、VQA问答对、结构化标签)。

**核心特性:**

- 220+ 类别,215K+ 张图片(作物、病害、害虫)
- 中英双语图像描述和问答对生成
- 完整的数据溯源(标准化命名规范)
- LLM驱动的语义验证和质量控制
- Web界面人工审核工具

---

## 项目架构

### 目录结构

```
dataset_web/
├── datasets/              # 主数据集目录
│   ├── crops/            # 作物图像 (140+ 类别)
│   ├── pests/            # 害虫图像 (30+ 类别)
│   └── diseases/         # 病害图像 (50+ 类别)
│
├── scripts/              # 核心数据处理脚本
│   ├── merge_*.py       # 数据合并工具
│   ├── deduplicate_images.py     # 智能去重与质量过滤
│   ├── bulk_rename_by_class.py  # 文件名标准化
│   ├── build_jsonl.py            # 生成JSONL数据索引
│   ├── count_images_by_class.py # 统计工具
│   └── pest_review_server.py    # Web审核服务器
│
├── llm_tools/            # LLM增强工具
│   ├── verify_and_describe.py   # 语义验证与描述生成
│   ├── gemini_client.py          # Gemini API客户端
│   ├── openai_client.py          # OpenAI兼容API客户端
│   └── multi_api_client.py       # 多API负载均衡
│
├── web_scraper/          # 网络爬虫
│   ├── scraper/spiders/
│   │   ├── agriculture_sites_spider.py  # GBIF/iNaturalist爬虫
│   │   └── unsplash_api_spider.py       # Unsplash API爬虫
│   └── scraped_images/   # 爬取图片暂存
│
├── docs/                 # 文档
│   ├── documentation.md  # 核心知识库(详细流程和规范)
│   └── pest_manual_review.html  # 离线审核界面
│
├── mappings/             # 类别映射表
│   ├── crop_mappings.json
│   ├── disease_mappings.json
│   └── pest_mappings.json
│
├── data.jsonl            # 完整数据索引
└── requirements.txt      # Python依赖
```

### 核心数据规范

#### 文件命名规范

所有文件必须遵循: `<类别名>__<来源标签>__<uuid>.<ext>`

**来源标签:**

- `__cd__`: Crop Diseases数据集
- `__pd__`: PlantDoc数据集
- `__kd__`: Kaggle数据集
- `__ac__`: 农作物(crops)数据集
- `__ap__`: 害虫(pests)数据集
- `__web__`: 网络爬取

**示例:** `corn_rust_leaf__pd__a3f2e1b9.jpg`

#### JSONL数据格式

```json
{
  "image": "datasets/diseases/corn_rust_leaf__pd__a3f2e1b9.jpg",
  "task": "caption",
  "text": "这是一张玉米锈病叶片的照片。This is a photo of corn rust leaf.",
  "lang": "zh",
  "split": "train",
  "labels": {
    "root": "diseases",
    "class": "corn rust leaf",
    "crop": "corn",
    "disease": "rust",
    "healthy": false,
    "source": "pd"
  }
}
```

---

## 常用命令

### 环境设置

```bash
# 安装依赖
pip install -r requirements.txt

# 配置LLM API (用于语义验证)
cat > .env.llm << EOF
VLM_API_KEY=sk-your-api-key-here
VLM_API_BASE=https://xmdbd.online/v1
VLM_MODEL=gemini-2.5-flash
VLM_WORKERS=6
EOF
```

### 数据处理流程

#### 1. 统计当前数据集

```bash
python3 scripts/count_images_by_class.py \
    --roots datasets/diseases datasets/crops datasets/pests
```

#### 2. 文件名标准化

```bash
# 为新数据添加来源标签
python3 scripts/bulk_rename_by_class.py \
    --root datasets/diseases \
    --tag pd
```

#### 3. 数据清洗与去重

```bash
# 基础清洗(尺寸、模糊、重复检测)
python3 scripts/deduplicate_images.py \
    --roots datasets/diseases datasets/crops datasets/pests \
    --min-width 224 --min-height 224 \
    --blur-threshold 60 \
    --ham-threshold 3 \
    --action move

# 使用双阈值模糊检测(更保守,减少误判)
python3 scripts/deduplicate_images.py \
    --roots web_scraper/scraped_images \
    --blur-method both \
    --blur-threshold 60 \
    --tenengrad-threshold 700 \
    --ham-threshold 3 \
    --near-scope class \
    --action move

# 从回收站挽救被误判的图片
python3 scripts/deduplicate_images.py \
    --roots web_scraper/scraped_images \
    --blur-method both \
    --blur-threshold 60 \
    --tenengrad-threshold 700 \
    --rescue-blur \
    --skip-clean
```

**重要参数说明:**

- `--action move`: 安全移动到 `.trash/`目录(推荐)
- `--action delete`: 永久删除(危险!)
- `--blur-method`: `laplacian`(默认) | `tenengrad` | `both`(需同时低于阈值)
- `--ham-threshold`: 汉明距离阈值(0=精确匹配, 3=允许轻微差异)
- `--near-scope`: `class`(按类去重) | `all`(全局去重)

#### 4. LLM语义验证(可选但推荐)

```bash
# 干跑模式(仅日志,不修改文件)
python3 llm_tools/verify_and_describe.py \
    --root datasets/diseases \
    --action dry-run \
    --workers 8

# 实际运行(验证+生成描述)
python3 llm_tools/verify_and_describe.py \
    --root datasets/diseases \
    --workers 6 \
    --insecure

# 处理单个类别
python3 llm_tools/verify_and_describe.py \
    --root "datasets/diseases/Apple Scab Leaf" \
    --workers 4
```

**说明:**

- 不匹配的图片移至 `.rejected_by_llm/`
- 通过验证的图片生成同名 `.json`元数据文件
- 推荐使用6个并发workers(平衡速度和成功率)

#### 5. 生成JSONL数据索引

```bash
python3 scripts/build_jsonl.py \
    --roots datasets/diseases datasets/crops datasets/pests \
    --out data.jsonl \
    --train 0.8 --val 0.1 --test 0.1 \
    --seed 42

# 包含Plant Pathology竞赛数据
python3 scripts/build_jsonl.py \
    --roots datasets/diseases datasets/crops datasets/pests \
    --include-pp2020 \
    --pp2020-root sources/plant-pathology-2020-fgvc7 \
    --include-pp2021 \
    --pp2021-root sources/plant-pathology-2021-fgvc8 \
    --out data.jsonl
```

#### 6. 生成统计报告

```bash
# 生成完整的CSV统计报告
python3 scripts/generate_stats.py \
    --jsonl data.jsonl data_holdout_web.jsonl \
    --out-dir stats_reports

# 输出文件:
#   stats_reports/counts_by_class.csv      (按类别统计)
#   stats_reports/counts_by_source.csv     (按来源统计)
#   stats_reports/counts_by_split.csv      (按划分统计)
#   stats_reports/class_source_pivot.csv   (类别×来源交叉表)

# 仅查看终端摘要(不生成CSV)
python3 scripts/generate_stats.py \
    --jsonl data.jsonl \
    --summary-only
```

**说明:**

- 所有CSV文件使用UTF-8 with BOM编码,Excel可直接打开
- 自动去重统计唯一图片数(通过`image`字段)
- 包含生成时间戳和来源JSONL文件名
- 透视表显示每个类别在各来源的图片分布

### 网络爬虫

#### 运行爬虫(在web_scraper目录下)

```bash
cd web_scraper

# GBIF/iNaturalist爬虫(主力数据源)
scrapy crawl agri_sites \
    -a keywords_file=keywords_pest_species.txt \
    -a max_api_results=150

# Unsplash API爬虫(补充数据源)
export UNSPLASH_API_KEY="your-api-key"
scrapy crawl unsplash_api \
    -a keywords_file=keywords_missing_priority.txt \
    -a max_pages=5 \
    -a per_page=30
```

#### 人工审核流程

```bash
# 1. 生成审核清单
python3 scripts/generate_pest_review_manifest.py \
    --root web_scraper/scraped_images \
    --out web_scraper/pest_review_manifest.js

# 2. 启动本地服务器
python3 -m http.server 8000
# 浏览器访问: http://localhost:8000/docs/pest_manual_review.html

# 3. (可选)启动智能审核后端
VLM_API_KEY=your_api_key_here python3 scripts/pest_review_server.py \
    --port 5178 \
    --root web_scraper/scraped_images \
    --allow-root datasets/pests \
    --workers 4

# 4. 导入审核通过的图片
python3 scripts/import_reviewed_pests.py \
    --review-json path/to/pest_review_YYYY-mm-dd.json \
    --tag web
```

### Git提交规范

```bash
# 项目使用conventional commits格式
# 格式: <type>(<scope>): <description>
#
# type: feat|fix|docs|style|refactor|test|chore
# scope: 可选,如 llm|scraper|scripts
# description: 简短描述,重点说明"为什么"而非"做了什么"

# 示例
git commit -m "feat(llm): add multi-API load balancing for better reliability"
git commit -m "fix(dedup): reduce false positives in blur detection"
git commit -m "docs: update data processing workflow in documentation.md"
```

---

## 关键技术决策

### 数据质量控制策略

1. **多层次去重:**

   - 精确哈希去重(MD5)
   - 感知哈希去重(pHash/aHash, 汉明距离≤3)
   - 按类别或全局范围可配置
2. **模糊检测算法:**

   - Laplacian方差: 快速,适合大部分场景
   - Tenengrad(Sobel梯度): 更鲁棒,减少误判
   - 双阈值模式: 需同时低于两个阈值才判定为模糊(最保守)
3. **LLM验证架构:**

   - 双API负载均衡(Gemini主力 + OpenAI备用)
   - 智能重试机制(指数退避,最多5次)
   - 并发控制(推荐6 workers)

### 文件命名与溯源

所有文件必须包含来源标签(`__xx__`),确保可追溯性:

- 便于跨来源分析和测试
- 支持按来源过滤和统计
- 方便回溯数据质量问题

### JSONL vs 传统标注

采用JSONL格式而非目录结构的原因:

- 支持多模态标注(Caption + VQA)
- 灵活的元数据存储(labels字段)
- 便于流式处理和分片
- 支持多语言标注

---

## 开发注意事项

### 修改数据处理脚本时

1. **始终使用 `--action move`测试**: 先移到 `.trash/`,检查后再永久删除
2. **检查映射文件**: 新增类别时更新 `mappings/*.json`
3. **验证命名规范**: 确保生成的文件名符合 `<类>__<源>__<uuid>.<ext>`
4. **更新文档**: 重要变更需同步更新 `docs/documentation.md`

### 添加新数据源时

1. 在 `scripts/`下创建 `merge_*.py`脚本
2. 定义类别映射关系(统一到本体)
3. 添加适当的来源标签
4. 运行完整清洗流程
5. 更新 `docs/documentation.md`的"附录A"

### LLM工具开发

1. 所有API调用需支持重试机制
2. 记录详细日志(成功/失败/原因)
3. 支持dry-run模式用于测试
4. 处理SSL证书问题(`--insecure`选项)
5. 实现并发控制避免速率限制

### 爬虫开发

1. 严格遵守 `robots.txt`
2. 设置合理的下载延迟
3. 记录元数据(来源URL、许可证、作者)
4. 使用官方API优先于网页解析
5. 实现断点续传和去重

---

## 测试策略

### 数据处理脚本测试

```bash
# 在小样本上测试
python3 scripts/deduplicate_images.py \
    --roots datasets/diseases/Apple\ Scab\ Leaf \
    --action move \
    --dry-run

# 验证JSONL输出
head -10 data.jsonl | jq
python3 -c "import json; [json.loads(line) for line in open('data.jsonl')]"
```

### LLM工具测试

```bash
# 干跑模式
python3 llm_tools/verify_and_describe.py \
    --root "datasets/diseases/Apple Scab Leaf" \
    --action dry-run \
    --workers 2

# 检查生成的JSON
find datasets/diseases -name "*.json" | head -5 | xargs cat
```

---

## 故障排查

### 常见问题

**问题: LLM验证429错误过多**

```bash
# 解决: 降低并发数
python3 llm_tools/verify_and_describe.py --workers 4  # 从8降到4
```

**问题: 模糊检测误判过多**

```bash
# 解决: 使用双阈值模式
python3 scripts/deduplicate_images.py \
    --blur-method both \
    --blur-threshold 60 \
    --tenengrad-threshold 700
```

**问题: 审核页面看不到图片**

```bash
# 解决: 使用本地服务器而非直接打开HTML
python3 -m http.server 8000
# 访问 http://localhost:8000/docs/pest_manual_review.html
```

**问题: 爬虫被robots.txt阻止**

```bash
# 解决: 使用官方API而非网页抓取
# 参考 web_scraper/scraper/spiders/agriculture_sites_spider.py
```

---

## 性能优化建议

1. **大数据集处理**: 分批处理,避免一次性加载所有图片到内存
2. **并发控制**: LLM验证推荐6 workers,爬虫遵守速率限制
3. **磁盘IO**: 使用SSD,避免频繁读写小文件
4. **内存优化**: 使用流式处理JSONL,不要全部load到内存

---

## 参考文档

- **核心知识库**: `docs/documentation.md` - 完整的设计理念、流程和规范
- **LLM工具**: `llm_tools/README.md` - LLM验证工具详细说明
- **爬虫**: `web_scraper/README.md` - 网络爬虫使用指南
- **API验证**: `API_VERIFICATION_SUMMARY.md` - 数据源API可用性分析
- **抓取报告**: `SCRAPING_SUMMARY.md` - 历史抓取记录

---

## 编码规范(来自原CLAUDE.md)

### 八荣八耻

- 以瞎猜接口为耻,以认真查询为荣
- 以模糊执行为耻,以寻求确认为荣
- 以臆想业务为耻,以人类确认为荣
- 以创造接口为耻,以复用现有为荣
- 以一遍通过为耻,以回头校验为荣
- 以破坏架构为耻,以遵循规范为荣
- 以假装理解为耻,以诚实无知为荣
- 以盲目修改为耻,以谨慎重构为荣

### 核心原则

1. **认真查询而非瞎猜** - 仔细检查现有代码和接口,避免臆测
2. **寻求确认而非模糊执行** - 不确定时明确询问用户
3. **人类确认而非臆想业务** - 业务逻辑需要用户确认
4. **复用现有而非创造接口** - 优先使用项目中已有的实现和模式
5. **回头校验而非一遍通过** - 完成后验证代码是否正确工作
6. **遵循规范而非破坏架构** - 保持项目的架构和编码风格一致性
7. **诚实无知而非假装理解** - 不懂时坦诚说明,不要装懂
8. **谨慎重构而非盲目修改** - 修改前充分理解上下文和影响范围

### 奥卡姆剃刀原则

**核心思想**: "如无必要,勿增实体"
