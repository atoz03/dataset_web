# 数据集状态报告 - 2025年10月8日

## 📊 当前数据集统计

### 总览
- **Crops（作物）**: 151个类别，共 **40,323** 张图片
- **Diseases（病害）**: 92个类别，共 **172,867** 张图片  
- **Pests（害虫）**: 13个类别，共 **5,380** 张图片
- **总计**: 256个类别，**218,570** 张图片

### 数据索引
- **data.jsonl**: 1,206,180行（包含中英双语Caption和VQA样本）
- 每张图片生成6条记录：2条Caption（中英文）+ 4条VQA（中英文）

## ⚠️ 需要补充的类别（<100张图片）

### Crops类别（9个）
1. cardamom - 22张
2. Fox_nut(Makhana) - 23张
3. sunflower - 24张
4. gram - 25张
5. Lemon - 28张
6. mustard-oil - 28张
7. cotton - 32张
8. Tobacco-plant - 33张
9. Pearl_millet(bajra) - 39张

### Diseases类别（7个）
1. Sugarcane leaf - 36张
2. Cherry leaf - 46张
3. Bell_pepper leaf spot - 53张
4. Bell_pepper leaf - 67张
5. Tomato mold leaf - 70张
6. grape leaf black rot - 72张
7. Tomato Early blight leaf - 74张

### Pests类别
✅ 所有类别均已超过100张，数据充足

## 🔧 已完成的工作

1. ✅ 全面分析现有数据集，识别缺失类别
2. ✅ 创建关键词文件：`web_scraper/keywords_missing_categories.txt`
3. ✅ 基于当前数据集重新生成 `data.jsonl`
4. ✅ 更新文档 `docs/documentation.md` 中的处理日志

## 📝 后续步骤建议

### 步骤1: 获取API密钥并爬取数据
```bash
# 选项A: 使用Bing API
export BING_SEARCH_API_KEY="your-api-key-here"
cd web_scraper
../.venv/bin/scrapy crawl bing_api -a keywords_file=keywords_missing_categories.txt -a max_results=150

# 选项B: 使用Unsplash API
export UNSPLASH_API_KEY="your-api-key-here"
cd web_scraper
../.venv/bin/scrapy crawl unsplash_api -a keywords_file=keywords_missing_categories.txt -a max_results=150
```

### 步骤2: 清洗和去重
```bash
.venv/bin/python scripts/deduplicate_images.py \
    --roots web_scraper/scraped_images \
    --min-width 224 --min-height 224 \
    --blur-method both \
    --blur-threshold 60 \
    --tenengrad-threshold 700 \
    --ham-threshold 3 \
    --near-scope class \
    --action move
```

### 步骤3: 生成审核清单
```bash
.venv/bin/python scripts/generate_pest_review_manifest.py \
    --root web_scraper/scraped_images \
    --out web_scraper/pest_review_manifest.js
```

### 步骤4: 人工审核
打开 `docs/pest_manual_review.html` 进行人工审核，标记通过/剔除的图片

### 步骤5: 导入审核通过的图片
```bash
.venv/bin/python scripts/import_reviewed_pests.py \
    --review-json path/to/review_YYYY-mm-dd.json \
    --tag web
```

### 步骤6: 重新生成数据索引
```bash
.venv/bin/python scripts/build_jsonl.py \
    --roots datasets/diseases datasets/crops datasets/pests \
    --out data.jsonl \
    --train 0.8 --val 0.1 --test 0.1 \
    --seed 42
```

## 📋 关键词文件内容

已创建 `web_scraper/keywords_missing_categories.txt`，包含：

**缺失的Crops类别关键词：**
- cardamom plant
- fox nut makhana plant
- sunflower plant
- gram chickpea plant
- lemon tree
- mustard oil plant
- cotton plant
- tobacco plant
- pearl millet bajra

**缺失的Diseases类别关键词：**
- sugarcane leaf disease
- cherry leaf disease
- bell pepper leaf spot disease
- bell pepper leaf disease
- tomato leaf mold disease
- grape leaf black rot disease
- tomato early blight leaf disease

## 🎯 目标

将所有类别的图片数量提升至100张以上，确保数据集的平衡性和训练效果。

---

## ✅ 更新：Unsplash API爬取完成 (2025-10-08)

### 爬取结果
使用Unsplash API成功获取了**3个类别共450张图片**：

| 类别 | 新增图片 | 原有图片 | 预计总数 | 达标状态 |
|------|---------|---------|---------|---------|
| Fox_nut(Makhana) | 150 | 23 | 173 | ✅ 已达标 |
| Pearl_millet(bajra) | 150 | 39 | 189 | ✅ 已达标 |
| grape leaf black rot | 150 | 72 | 222 | ✅ 已达标 |

### 仍需补充的类别（13个）
- **Crops类别**: cardamom(22), sunflower(24), gram(25), Lemon(28), mustard-oil(28), cotton(32), Tobacco-plant(33)
- **Diseases类别**: Sugarcane leaf(36), Cherry leaf(46), Bell_pepper leaf spot(53), Bell_pepper leaf(67), Tomato mold leaf(70), Tomato Early blight leaf(74)

### 经验教训
1. **Unsplash局限性**: 专注于通用摄影，农业专业术语图片较少
2. **API配额**: 每小时50次请求，需要合理规划使用
3. **建议**: 使用Bing API或其他专业农业数据源补充剩余类别

### 待办事项
1. ✅ 爬取图片已保存到 `web_scraper/scraped_images/`
2. ⏳ 需要人工审核（使用 `docs/pest_manual_review.html`）
3. ⏳ 需要清洗去重
4. ⏳ 导入审核通过的图片到主数据集
5. ⏳ 更新 `data.jsonl`

详细爬取报告请查看：`SCRAPING_RESULTS_20251008.md`
