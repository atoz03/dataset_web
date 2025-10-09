# 图片抓取总结报告 - 2025年12月9日

## 📊 抓取成果

### 执行策略
- **主力**: GBIF/iNaturalist (agri_sites爬虫) - 专业生物学数据库
- **补充**: Unsplash API - 高质量通用图片
- **已删除**: Bing相关爬虫（API已废弃）

### 数据量
- **新增图片**: 17,341+ 张（还在增加中）
- **数据位置**: `web_scraper/scraped_images/`

## 🎯 类别补充结果

### 害虫 (Pests)
- ✅ 所有13个原有类别达到500+张
- ✅ 新增20+个细分物种（蚜虫、螨虫、粉虱、蓟马等）

### 作物 (Crops) - 9个缺失类别全部达标
| 类别 | 原有 → 当前 |
|------|------------|
| sunflower | 24 → 568+ |
| cotton | 32 → 446+ |
| gram | 25 → 520+ |
| lemon | 28 → 342+ |
| tobacco | 33 → 325+ |
| pearl millet | 39 → 310+ |
| fox nut | 23 → 305+ |
| cardamom | 22 → 261+ |
| mustard | 28 → 150+ |

### 病害 (Diseases) - 7个缺失类别全部达标
| 类别 | 原有 → 当前 |
|------|------------|
| Bell pepper leaf spot | 53 → 691+ |
| Cherry leaf | 46 → 531+ |
| Tomato mold leaf | 70 → 568+ |
| grape leaf black rot | 72 → 300+ |
| Bell pepper leaf | 67 → 193+ |
| Sugarcane leaf | 36 → 150+ |
| Tomato Early blight | 74 → 150+ |

## 📋 下一步操作

### 1. 去重清洗
```bash
.venv/bin/python scripts/deduplicate_images.py \
    --roots web_scraper/scraped_images \
    --min-width 224 --min-height 224 \
    --blur-method both --blur-threshold 60 \
    --tenengrad-threshold 700 --ham-threshold 3 \
    --near-scope class --action move
```

### 2. 生成审核清单
```bash
.venv/bin/python scripts/generate_pest_review_manifest.py \
    --root web_scraper/scraped_images \
    --out web_scraper/pest_review_manifest.js
```

### 3. 人工审核
- 打开 `docs/pest_manual_review.html`
- 逐类别审核，标记通过/剔除
- 导出审核结果JSON

### 4. 导入数据集
```bash
.venv/bin/python scripts/import_reviewed_pests.py \
    --review-json path/to/review.json \
    --tag web
```

### 5. 重建索引
```bash
.venv/bin/python scripts/build_jsonl.py \
    --roots datasets/diseases datasets/crops datasets/pests \
    --out data.jsonl --train 0.8 --val 0.1 --test 0.1 --seed 42
```

## 📚 相关文档
- **主文档**: `docs/documentation.md` (已更新处理日志)
- **API说明**: `API_VERIFICATION_SUMMARY.md` (当前使用的数据源)
- **新增文件**: 
  - `keywords_pest_species.txt` - 综合害虫关键词
  - `keywords_new_pests.txt` - 新害虫学名
  - `keywords_missing_priority.txt` - 高优先级缺失类别

## 💡 关键注意事项

1. **细分害虫类别**: 建议合并到主类别（如多种蚂蚁→ants），保持类别数量可控
2. **学名关键词**: keywords_new_pests.txt使用科学分类，需要映射处理
3. **质量控制**: 人工审核时重点检查通用关键词可能引入的不相关图片

---
**最后更新**: 2025-12-09 | **数据来源**: GBIF/iNaturalist + Unsplash
