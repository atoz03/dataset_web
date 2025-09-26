# 数据整合与预处理过程记录（Process Log）

本文档记录在本仓库中对多源农业图像数据的整合、命名规范统一、脚本编写及预处理的关键过程，便于复现与审计。

**时间线（2025-09-25）**
- 初始结构确认：`datasets/{crops,pests,diseases}` 已存在；另有本地原始 `Crop Diseases/` 数据集待合并。
- 合并“Crop Diseases”到 `datasets/diseases`，并建立类别映射与统一重命名规范。
- 为已有 `datasets/diseases` 中历史文件统一重命名（添加来源标签 pd）。
- 将命名规范应用到 `datasets/crops`（ac）与 `datasets/pests`（ap）。
- 扩展图片去重清理脚本（感知哈希 + 模糊检测 + 尺寸过滤）。
- 编写 JSONL 构建脚本，生成双语 caption/VQA 数据索引。

- 合并 140-most-popular-crops-image-dataset 到 `datasets/crops`（方案B，细粒度映射）。
  - 来源：`140-most-popular-crops-image-dataset/Raw/Raw`；忽略三套 224×224 预处理副本。
- 脚本：`scripts/merge_140_crops.py`；命名：`<class>__ac__<uuid>.<ext>`。
  - 辣椒家族并入 `chilli`；`Black pepper` 保留独立类。
  - 与现有类对齐（节选）：Maize (Corn)→maize、Rice (Paddy)→rice、Wheat→wheat、Tomatoes→tomato、Bananas→banana、Coconuts→coconut、Coffee (green)→Coffee-plant、Olives→Olive-tree、Soybeans→soyabean、Pineapples→pineapple、Papayas→papaya、Sunflowers→sunflower、Sorghum→jowar、Cucumbers and gherkins→Cucumber、Tobacco plant→Tobacco-plant、Sugar cane→sugarcane、Mung bean→vigna-radiati(Mung)。
  - 新增并保留（示例）：Lemons and limes、Groundnuts (Peanuts)、Mustard seeds、Mustard greens、Cabbages and other brassicas、Pumpkins, squash and gourds、Oil palm fruit、Rubber (natural)、Hen eggs (shell weight) 等。
  - 统计：类别 140、新增类目录 117、复制图片 38,546、非图片 0。
  - 产物：`mappings/140_crops_map.json`（映射表）、`mappings/140_crops_report.json`（统计）。

— 源数据清理（2025-09-25）
- 已在完成合并与产物落盘后，删除以下源目录以节省空间：
  - `140-most-popular-crops-image-dataset/`
  - `Crop Diseases/`
注：后续若需回溯，可依赖 `mappings/140_crops_map.json` 与 `origin.md`/`origin2.md` 的记录；所有合并均为拷贝入 `datasets/`，不影响现有数据。

---

**一、目录与命名规范**
- 统一文件名格式：`<类别名>__<来源标签>__<uuid>.<ext>`（扩展名小写）
  - 标签含义：`cd`=Crop Diseases，`pd`=PlantDoc/其他病害，`ac`=crops，`ap`=pests。
- 采取“拷贝合并”策略（不移动源数据），保持可回滚性。

---

**二、合并 Crop Diseases 到 datasets/diseases**
- 脚本：`scripts/merge_crop_diseases.py`
- 行为：按映射将 `Crop Diseases/<类>` 拷贝到 `datasets/diseases/<目标类>`，命名为 `<目标类>__cd__<uuid>.<ext>`。
- 结果：共拷贝 13324 张图片，0 非图片跳过。
- 主要类别映射（节选）：
  - Corn___Common_Rust → `datasets/diseases/Corn rust leaf`
  - Corn___Gray_Leaf_Spot → `datasets/diseases/Corn Gray leaf spot`
  - Corn___Northern_Leaf_Blight → `datasets/diseases/Corn leaf blight`
  - Corn___Healthy → `datasets/diseases/Corn leaf`
  - Potato___Early_Blight → `datasets/diseases/Potato leaf early blight`
  - Potato___Late_Blight → `datasets/diseases/Potato leaf late blight`
  - Potato___Healthy → `datasets/diseases/Potato leaf`
  - Rice___Brown_Spot → `datasets/diseases/Rice brown spot`
  - Rice___Leaf_Blast → `datasets/diseases/Rice leaf blast`
  - Rice___Neck_Blast → `datasets/diseases/Rice neck blast`
  - Rice___Healthy → `datasets/diseases/Rice leaf`
  - Sugarcane_Bacterial Blight → `datasets/diseases/Sugarcane bacterial blight`
  - Sugarcane_Red Rot → `datasets/diseases/Sugarcane red rot`
  - Sugarcane_Healthy → `datasets/diseases/Sugarcane leaf`
  - Wheat___Brown_Rust → `datasets/diseases/Wheat brown rust`
  - Wheat___Yellow_Rust → `datasets/diseases/Wheat yellow rust`
  - Wheat___Healthy → `datasets/diseases/Wheat leaf`

复现命令：
- `python3 scripts/merge_crop_diseases.py`

---

**三、批量重命名（统一来源标签）**
- 脚本：`scripts/bulk_rename_by_class.py`
- 规则：对指定根目录内的图片，就地改名为 `<类别名>__<标签>__<uuid>.<ext>`；已含 `__cd__/__pd__/__ac__/__ap__` 的文件默认跳过。
- 实际执行与结果：
  - diseases（补齐历史文件为 `__pd__`）：
    - 命令：`python3 scripts/bulk_rename_by_class.py --root datasets/diseases --tag pd`
    - 结果：处理 15899，重命名 2575，跳过 13324
  - crops（统一为 `__ac__`）：
    - 命令：`python3 scripts/bulk_rename_by_class.py --root datasets/crops --tag ac`
    - 结果：处理 1823，重命名 1816，跳过 7
  - pests（统一为 `__ap__`）：
    - 命令：`python3 scripts/bulk_rename_by_class.py --root datasets/pests --tag ap`
    - 结果：处理 5494，重命名 5494，跳过 0

---

**四、图片清理脚本扩展（去重/模糊/尺寸）**
- 文件：`scripts/deduplicate_images.py`
- 新增能力：
  - 感知哈希去重：pHash（无 numpy 自动退化到 aHash）；支持 `--ham-threshold` 控制近重复阈值。
  - 模糊检测：Laplacian 方差；低于 `--blur-threshold` 视为模糊。
  - 尺寸过滤：`--min-width/--min-height`。
  - 安全清理：默认移动到每个 root 下 `.trash/`（按 small/blur/dupe 分类）；也可 `--action delete` 硬删除。
- 示例：
  - 安全清理：`python3 scripts/deduplicate_images.py --roots datasets/diseases datasets/crops datasets/pests --min-width 224 --min-height 224 --blur-threshold 60 --ham-threshold 0 --action move`
  - 近重复：`python3 scripts/deduplicate_images.py --roots datasets/diseases --ham-threshold 5`
- 依赖：Pillow（必需），numpy（可选，推荐）。

---

**五、生成双语 JSONL（caption/VQA）**
- 文件：`scripts/build_jsonl.py`
- 功能：
  - 扫描 `datasets/{diseases,crops,pests}`，按类分层随机划分 `train/val/test`（默认 8/1/1）。
  - 每张图生成中英 caption；并生成 VQA 问答（作物/病害/是否健康/害虫）。
  - 自动解析 `labels`：`root, class, crop/disease/pest, healthy, source`（从文件名标签或根目录推断）。
- 字段：`image, task, text, answer(仅vqa), lang, labels{...}, split`。
- 示例：
  - `python3 scripts/build_jsonl.py --roots datasets/diseases datasets/crops datasets/pests --out data.jsonl --train 0.8 --val 0.1 --test 0.1 --seed 42`

---

**六、文档与对照表**
- 在 `origin.md` 中补充了“目录中英文对照（完整）”与数据源条目 5、6 的规范化记录；新增“统一命名应用到 crops 与 pests”的步骤说明。
- 本过程记录保存在 `origin2.md`（本文）。

---

**七、注意事项与建议**
- 阈值选择：建议先以 `--action move` 运行清理，检查 `.trash/` 下命中情况后再决定是否 `delete` 或调节 `blur/ham` 阈值。
- 病害中文名：为避免误译，JSONL 中病害名保留英文原词，可在训练时再映射展示层翻译。
- 后续可选：
  - 将 JSONL 拆分导出为 `train.jsonl/val.jsonl/test.jsonl`；
  - 打包为 WebDataset 分片以提升分布式训练吞吐；
  - 扩展更完整的作物/病害中文词表并加入数据校验脚本。

---

**八、后续工作流程（待数据齐备时执行）**

- 环境与准备
  - 安装依赖：`pip install pillow numpy`（如需 WebDataset：`pip install webdataset`）。
  - 预留空间：确保 `.trash/`、`data/` 目录有足够磁盘空间。
  - 采用“先移动再删除”的策略，所有清理先以 `--action move` 验证。

- 命名与归档（新增数据源接入）
- 新病害源合并：按 `scripts/merge_crop_diseases.py:1` 中 `CLASS_MAP` 的格式扩展映射；未映射类脚本会告警。
  - 命名标签分配：
    - 病害：`cd`（本地Crop Diseases）、`pd`（PlantDoc/其他病害）；必要时为新来源预留新标签（如 `kd` for Kaggle disease）。
    - 作物：`ac`；害虫：`ap`。
- 统一重命名：对新接入目录执行 `scripts/bulk_rename_by_class.py --root <path> --tag <label>`。

- 数据清洗（三步）
- 尺寸/模糊：`python3 scripts/deduplicate_images.py --roots datasets/diseases datasets/crops datasets/pests --min-width 224 --min-height 224 --blur-threshold 60 --action move`
  - 近重复（可选）：`--ham-threshold 5` 在同一类目录内清近似重复。
  - 复核 `.trash/` 命中，确认后改为 `--action delete` 或保留 `.trash/` 以防回滚。

- 质量与统计检查
  - 类别计数（按来源分组）并导出：
    - 建议新增统计脚本（待办）：输出每个类 `total/by_source(train/val/test)` 的计数到 CSV。
  - 尺寸与纵横比分布：抽样绘制直方图，确认极端样本是否需要剔除或特殊处理（待办脚本）。
  - 随机可视化抽检：每类抽 10 张图（待办脚本），快速发现脏标签/非叶片/非目标主体。

- 数据划分与索引
- 基础索引：`python3 scripts/build_jsonl.py --roots datasets/diseases datasets/crops datasets/pests --out data/data.jsonl --train 0.8 --val 0.1 --test 0.1 --seed 42`
  - 跨来源测试（建议）：为某一来源（如 `pd`）保留专用 test 划分（待办：在 build_jsonl.py 增加 `--holdout-source` 选项或单独脚本筛选 data.jsonl 生成 `data/test_cross_source.jsonl`）。
  - 按 split 拆分（待办）：将 JSONL 拆成 `data/train.jsonl`、`data/val.jsonl`、`data/test.jsonl`，或维持单一 JSONL + 读取时过滤。

- 存储与打包（可选）
  - WebDataset 分片（待办脚本）：按 1–5k 样本/分片将 `data.jsonl` 中的样本打包为 `.tar`，并保存索引（`.idx`）。
  - 完整性校验：为每个分片生成 `sha256` 清单，保存到 `data/manifest.sha256`。

- 法务与溯源
  - 为每个来源补充许可与引用：在 `origin.md:1` 下补充 License/Citation 字段（待办）。
  - 索引标注来源：已在 JSONL 的 `labels.source` 字段保留，可用于训练时合规审计与溯源。

- 文档与版本化
  - 在 `origin.md:1` 与 `origin2.md:1` 记录每次数据改动、阈值、命令与统计摘要。
  - 数据版本号建议：`dataset_vYYYYMMDD_revN`；将 `data.jsonl`、统计 CSV、manifest 一并入库。
  - 关键脚本参数（阈值、种子）变化需注明原因与影响评估。

- 质量门禁（可选）
  - 预提交检查：新增一个轻量 CI 步骤（待办），对新增图片运行最小阈值检测与命名规范校验。
  - 类别白名单：禁止出现未在目录中英文对照表登记的类名（待办脚本）。

- 运行顺序建议（一次性流水线）
  - 合并/命名：merge -> bulk_rename（新数据）
  - 清理：deduplicate_images（move）-> 复核 -> deduplicate_images（delete 可选）
  - 统计：类计数/尺寸分布/抽检（待办）
  - 索引：build_jsonl -> 拆分/跨来源衍生（待办）
  - 打包：WebDataset（可选，待办）-> manifest（待办）
  - 归档：更新 origin.md / origin2.md，写入版本号与指标

- 待办清单（TODOs）
  - [ ] 统计脚本：按类与来源输出 count CSV
  - [ ] 尺寸/纵横比分布与抽样可视化脚本
  - [ ] build_jsonl 增加 `--holdout-source` 或产出跨来源测试集的辅助脚本
  - [ ] JSONL 拆分脚本（train/val/test 独立文件）
  - [ ] WebDataset 打包脚本与校验清单生成
  - [ ] 命名规范/类名白名单校验器
  - [ ] License/Citation 汇总补全
  - [ ] EXIF 方向与 sRGB 颜色空间标准化（可加到清理脚本）

---

附录：新增合并记录（2025-09-26 PlantDoc）

- 数据源：PlantDoc-Dataset（GitHub master）。
- 下载与准备：
  - `sources/PlantDoc-Dataset-master.zip`（约 939MB），解压至 `sources/PlantDoc-Dataset-master/`。
  - 重命名：
    - `python3 scripts/bulk_rename_by_class.py --root sources/PlantDoc-Dataset-master/train --tag pd --force`
    - `python3 scripts/bulk_rename_by_class.py --root sources/PlantDoc-Dataset-master/test --tag pd --force`
- 合并动作：按类名 identity 映射，复制到 `datasets/diseases/<类名>/`。
- 统计：
  - 总计复制：2,572 张图片；类目数：28。
  - 主要类及计数（节选）：
    - Apple leaf 91、Apple Scab Leaf 93、Apple rust leaf 88
    - Corn leaf blight 191、Corn rust leaf 116、Corn Gray leaf spot 68
    - Potato leaf early blight 116、Potato leaf late blight 105
    - Tomato Early blight leaf 88、Tomato Septoria leaf spot 151、Tomato leaf 63
  - 产物：`mappings/plantdoc_report.json`（JSON 报告，包含每类计数与使用目录列表）。
- 全局盘点：生成 `mappings/dataset_universal_map.json`，可用于查看三大根目录的类目总览与来源标签分布。

---

补记：命名合并校准（2025-09-26）

- 背景：PlantDoc 与 PlantVillage 同类拼写差异导致 `Soyabean leaf`/`Soybean leaf`、`Tomato two spotted spider mites leaf`/`Tomato two spotted spider mites` 双目录并存。
- 操作：
  - 使用 MD5 判重，将唯一本体拷贝至目标目录；避免覆盖时自动追加序号。
  - 重复样本移动至 `datasets/diseases/.trash/merged_duplicates_20250926_132209/`，保留复核。
  - 删除空目录，刷新统计。
- 结果：合并后 `Soybean leaf`=5,155、`Tomato two spotted spider mites`=1,678；源目录移除。

---

附录：待执行合并（PlantVillage / Plant Pathology via Kaggle）

- 目的：补充病害类别在自然/室内光条件下的多样性，增强跨来源泛化。
- 配置：
  - `pip install kaggle`；下载 API Token 至 `~/.kaggle/kaggle.json`（chmod 600）。
  - 使用 `scripts/fetch_kaggle_datasets.py --slug <owner/dataset> --unzip` 获取到 `sources/<dataset>/`。
- 候选数据集与备注：
  - `alicelabs/new-plant-diseases-dataset`（结构清晰，类别标准化好）
  - `muhammadardiputra/plantvillage-dataset`（PlantVillage 组织）
  - `plant-pathology-2020-fgvc7`（竞赛，CSV 参考标签转换后再合并）
- 合并操作：
  - 先重命名：`python3 scripts/bulk_rename_by_class.py --root sources/<dataset> --tag kd --force`
  - 再拷贝合并：`python3 scripts/merge_kaggle_disease.py --src sources/<dataset> --tag kd`
- 产物：自动生成 `mappings/<dataset>_merge_report.json`。
