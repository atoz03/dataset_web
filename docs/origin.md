# 数据集来源记录

本文档记录了项目中使用的各个农业相关图像数据集的来源和基本信息。

**目录中英文对照（完整）**

- `datasets` → 数据集根目录
- `datasets/crops` → 农作物（Crops）
- `datasets/pests` → 害虫（Pests）
- `datasets/diseases` → 病害（Diseases）
- `Crop Diseases` → 作物病害（本地原始数据文件夹）

- Diseases 目录：
  - Apple Scab Leaf → 苹果黑星病
  - Apple leaf → 苹果叶
  - Apple rust leaf → 苹果锈病叶
  - Bell_pepper leaf → 甜椒叶
  - Bell_pepper leaf spot → 甜椒叶斑病
  - Blueberry leaf → 蓝莓叶
  - Cherry leaf → 樱桃叶
  - Corn Gray leaf spot → 玉米灰斑病
  - Corn leaf → 玉米叶
  - Corn leaf blight → 玉米叶枯病
  - Corn rust leaf → 玉米锈病叶
  - Peach leaf → 桃叶
  - Potato leaf → 马铃薯叶
  - Potato leaf early blight → 马铃薯早疫病
  - Potato leaf late blight → 马铃薯晚疫病
  - Raspberry leaf → 覆盆子叶
  - Rice brown spot → 稻褐斑病
  - Rice leaf → 稻叶
  - Rice leaf blast → 稻叶稻瘟病
  - Rice neck blast → 稻穗颈稻瘟病
  - Soyabean leaf → 大豆叶
  - Squash Powdery mildew leaf → 南瓜白粉病叶
  - Strawberry leaf → 草莓叶
  - Sugarcane bacterial blight → 甘蔗细菌性叶枯病
  - Sugarcane leaf → 甘蔗叶
  - Sugarcane red rot → 甘蔗红腐病
  - Tomato Early blight leaf → 番茄早疫病叶
  - Tomato Septoria leaf spot → 番茄叶斑病（Septoria）
  - Tomato leaf → 番茄叶
  - Tomato leaf bacterial spot → 番茄细菌性斑点病
  - Tomato leaf late blight → 番茄晚疫病叶
  - Tomato leaf mosaic virus → 番茄花叶病毒
  - Tomato leaf yellow virus → 番茄黄化病毒叶
  - Tomato mold leaf → 番茄霉病叶
  - Tomato two spotted spider mites leaf → 番茄二斑叶螨危害叶
  - Wheat brown rust → 小麦褐锈病
  - Wheat leaf → 小麦叶
  - Wheat yellow rust → 小麦黄锈病
  - grape leaf → 葡萄叶
  - grape leaf black rot → 葡萄黑腐病

- Crops 目录：
  - Cherry → 樱桃
  - Coffee-plant → 咖啡树
  - Cucumber → 黄瓜
  - Fox_nut(Makhana) → 芡实（鸡头米）
  - Lemon → 柠檬
  - Olive-tree → 橄榄树
  - Pearl_millet(bajra) → 珍珠粟（Bajra）
  - Tobacco-plant → 烟草
  - almond → 杏仁（扁桃）
  - banana → 香蕉
  - cardamom → 小豆蔻
  - chilli → 辣椒
  - clove → 丁香
  - coconut → 椰子
  - cotton → 棉花
  - crop_images → 作物图像
  - gram → 鹰嘴豆（Gram）
  - jowar → 高粱（Jowar）
  - jute → 黄麻
  - kag2 → Kaggle 补充集（kag2）
  - maize → 玉米
  - mustard-oil → 芥籽（油用）
  - papaya → 木瓜
  - pineapple → 菠萝
  - rice → 稻（大米）
  - some_more_images → 额外图像补充
  - soyabean → 大豆
  - sugarcane → 甘蔗
  - sunflower → 向日葵
  - tea → 茶树
  - test_crop_image → 测试作物图像
  - tomato → 番茄
  - vigna-radiati(Mung) → 绿豆（豇豆属）
  - wheat → 小麦

- Pests 目录：
  - ants → 蚂蚁
  - bees → 蜜蜂
  - beetle → 甲虫
  - catterpillar → 毛虫（鳞翅目幼虫）
  - earthworms → 蚯蚓
  - earwig → 蠼螋
  - grasshopper → 蝗虫
  - moth → 蛾
  - slug → 鼻涕虫
  - snail → 蜗牛
  - wasp → 黄蜂
  - weevil → 象鼻虫

## 1. Agricultural-crops

*   **来源:** [Kaggle - Agricultural Crops Image Classification](https://www.kaggle.com/datasets/mdwaquarazam/agricultural-crops-image-classification)
*   **简介:** 该数据集包含多种农作物的图像，主要用于图像分类任务，例如识别不同类型的农作物。

## 2. agricultural-pests-image-dataset

*   **来源:** [Kaggle - Agricultural Pests Image Dataset](https.www.kaggle.com/datasets/vencerlanz09/agricultural-pests-image-dataset)
*   **简介:** 该数据集专注于农业害虫，提供了多种害虫的图像，可用于害虫识别和分类模型的训练。

## 3. Agriculture crop images

*   **来源:** [Kaggle - Agriculture crop images](https://www.kaggle.com/datasets/aman2000jaiswal/agriculture-crop-images/data?select=test_crop_image)
*   **简介:** 这是另一个农作物图像数据集，根据链接判断，它可能包含了用于测试模型的特定图像子集。

## 4. PlantDoc-Dataset

*   **来源:** [GitHub - PlantDoc-Dataset](https://github.com/pratikkayal/PlantDoc-Dataset/tree/master)
*   **简介:** 该数据集来自一个GitHub项目，专注于植物病害检测。它不仅包含图像，还可能附带相关的研究论文、代码或预处理脚本，用于识别植物叶片上的病害。

## 5. Agriculture Crops Dataset

*   **来源:** [Kaggle - Agriculture Crops Dataset](https://www.kaggle.com/datasets/osamajalilhassan/agriculture-crops-dataset)
*   **简介:** 多类别农作物图像集合，可用于通用作物识别与分类任务，补充 `datasets/crops` 中的样本多样性。

## 6. Top Agriculture Crop Disease

*   **来源:** [Kaggle - Top Agriculture Crop Disease](https://www.kaggle.com/datasets/kamal01/top-agriculture-crop-disease)
*   **简介:** 多种作物常见病害的图像数据集，覆盖锈病、斑点病、晚疫病等类别，用于病害识别任务；整合进入 `datasets/diseases` 统一管理。


## 7. 140-most-popular-crops-image-dataset

- 来源: https://www.kaggle.com/datasets/omrathod2003/140-most-popular-crops-image-dataset
- 使用范围: 仅使用 `Raw/Raw/<Class>/...` 原始图像；忽略 `RGB_224x224 / BGR_224x224 / GRAY_224x224` 以避免重复与信息损失。


- 合并目标: `datasets/crops`
- 命名规范: `<class>__ac__<uuid>.<ext>`（扩展名小写，`ac` 表示 crops 来源）。
- 执行脚本: `scripts/merge_140_crops.py`（拷贝合并，不移动源数据）。
- 溯源产物: `mappings/140_crops_map.json`（原类→目标类映射）、`mappings/140_crops_report.json`（统计汇总）。
- 源目录清理：已在完成合并后删除 `140-most-popular-crops-image-dataset/` 与 `Crop Diseases/` 以节省空间。

## 8. PlantVillage Dataset (Color Split)

* 来源: Kaggle - PlantVillage Dataset (`abdallahalidev/plantvillage-dataset`, License: CC BY-NC-SA 4.0)
* 使用范围: 仅使用 `plantvillage dataset/color/`（彩色版本）；忽略 `grayscale/` 与 `segmented/`。
* 合并目标: `datasets/diseases`
* 命名规范: `<class>__kd__<uuid>.<ext>`（`kd` 表示 Kaggle disease 来源）。
* 预处理与合并脚本:
  - 规范化类名：将 `Crop___Disease` 映射为现有风格（示例：`Corn_(maize)___Northern_Leaf_Blight` → `Corn leaf blight`）。
  - 重命名：`python3 scripts/bulk_rename_by_class.py --root sources/plantvillage-dataset/normalized_color --tag kd --force`
  - 合并：`python3 scripts/merge_kaggle_disease.py --src sources/plantvillage-dataset/normalized_color --tag kd`
* 溯源产物: `mappings/normalized_color_merge_report.json`（每类计数与目录清单）。
* 统计: 46,072 张图片复制并合并；新增/复用类见报告。

## 9. New Plant Diseases / Plant Pathology（预留）

* 来源: Kaggle - New Plant Diseases Dataset、Plant Pathology 2020/2021（需根据结构适配）。
* 使用范围: 待选定具体版本与许可，按 `scripts/fetch_kaggle_datasets.py` 下载；如为竞赛数据需依据 CSV 转为类目录再合并。
* 合并目标: `datasets/diseases`
* 命名规范: `<class>__kd__<uuid>.<ext>`
* 预处理与合并脚本: `scripts/fetch_kaggle_datasets.py`、`scripts/merge_kaggle_disease.py`（或专用转换脚本）。
* 溯源产物: 将创建 `mappings/<dataset>_merge_report.json`。

合并与命名策略（方案B，和谐合并，细粒度匹配）
- 精细映射：对与现有目录语义一致者并入既有类（大小写按现有目录保持）；对歧义或集合类保留新类名；仅做 Unicode 重音消解与去除末尾 `plant`，不强行翻译或大规模改写。
- 辣椒家族：将 `Chili peppers and green peppers / Aji pepper / Habanero pepper` 等并入既有 `chilli`；`Black pepper`（胡椒）保留为独立新类。
- 已与现有类对齐（节选）：
  - Maize (Corn) → `maize`
  - Rice (Paddy) → `rice`
  - Wheat → `wheat`
  - Tomatoes → `tomato`
  - Bananas → `banana`
  - Coconuts → `coconut`
  - Coffee (green) → `Coffee-plant`
  - Olives → `Olive-tree`
  - Soybeans → `soyabean`
  - Pineapples → `pineapple`
  - Papayas → `papaya`
  - Sunflowers → `sunflower`
  - Sorghum → `jowar`
  - Cucumbers and gherkins → `Cucumber`
  - Tobacco plant → `Tobacco-plant`
  - Sugar cane → `sugarcane`
  - Mung bean → `vigna-radiati(Mung)`
- 新增并保留（示例）：`Lemons and limes`、`Groundnuts (Peanuts)`、`Mustard seeds`、`Mustard greens`、`Cabbages and other brassicas`、`Pumpkins, squash and gourds`、`Oil palm fruit`、`Rubber (natural)`、`Hen eggs (shell weight)` 等。

执行与统计（2025-09-25）
- 命令：`python3 scripts/merge_140_crops.py --src 140-most-popular-crops-image-dataset/Raw/Raw --dst datasets/crops`
- 类别数：140；新增类目录：117；复制图片：38,546；非图片：0。
- 去重与清理：建议安装 Pillow 后运行（安全模式移动到 `.trash/`）
  - `python3 scripts/deduplicate_images.py --roots datasets/crops --min-width 224 --min-height 224 --blur-threshold 60 --ham-threshold 0 --action move`


## 数据集整合记录

**2025-09-25:**

为了便于管理和使用，所有原始数据集已被整合到一个统一的 `datasets` 文件夹下，并按内容进行了分类。

**新的目录结构:**

```
datasets/
├── crops/      # 农作物图像 (合并自多个来源)
├── pests/      # 农业害虫图像 (来自 agricultural-pests-image-dataset)
└── diseases/   # 植物病害图像 (来自 PlantDoc-Dataset-master)
```

**操作步骤:**

1.  创建 `datasets` 主目录及其子目录 `crops`, `pests`, `diseases`。
2.  将 `Agricultural-crops` 和 `Agriculture crop images` 文件夹的内容移动到 `datasets/crops/`。
3.  将 `agricultural-pests-image-dataset` 的内容移动到 `datasets/pests/`。
4.  将 `PlantDoc-Dataset-master` 的内容移动到 `datasets/diseases/`。
5.  删除原有的空文件夹。
6.  **2025-09-25 (精细化合并):**
    *   将一个补充的 `Agricultural-crops` 数据集中的各个作物图片，合并到 `datasets/crops/` 目录下对应的作物文件夹中。
    *   为了避免文件名冲突，所有被合并的图片都通过在原文件名前添加 `_ac2` 后缀的方式进行了重命名。
    *   此次合并丰富了现有作物的数据量，但未新增作物类别。

**2025-09-25 (Crop Diseases 合并):**

- 将本地 `Crop Diseases` 数据集按病害类别合并到 `datasets/diseases/`。
- 类别映射与新增目录：
  - Corn___Common_Rust -> `datasets/diseases/Corn rust leaf`
  - Corn___Gray_Leaf_Spot -> `datasets/diseases/Corn Gray leaf spot`
  - Corn___Northern_Leaf_Blight -> `datasets/diseases/Corn leaf blight`
  - Corn___Healthy -> `datasets/diseases/Corn leaf` (新增)
  - Potato___Early_Blight -> `datasets/diseases/Potato leaf early blight`
  - Potato___Late_Blight -> `datasets/diseases/Potato leaf late blight`
  - Potato___Healthy -> `datasets/diseases/Potato leaf` (新增)
  - Rice___Brown_Spot -> `datasets/diseases/Rice brown spot` (新增)
  - Rice___Leaf_Blast -> `datasets/diseases/Rice leaf blast` (新增)
  - Rice___Neck_Blast -> `datasets/diseases/Rice neck blast` (新增)
  - Rice___Healthy -> `datasets/diseases/Rice leaf` (新增)
  - Sugarcane_Bacterial Blight -> `datasets/diseases/Sugarcane bacterial blight` (新增)
  - Sugarcane_Red Rot -> `datasets/diseases/Sugarcane red rot` (新增)
  - Sugarcane_Healthy -> `datasets/diseases/Sugarcane leaf` (新增)

**2025-09-26 (PlantDoc 合并):**

- 来源: GitHub - PlantDoc-Dataset（master 分支压缩包）
  - 下载并解压到 `sources/PlantDoc-Dataset-master/`，包含 `train/` 与 `test/` 两部分。
  - 统一命名：对两部分执行 `scripts/bulk_rename_by_class.py --root ... --tag pd --force`，将文件重命名为 `<类名>__pd__<uuid>.<ext>`。
- 合并策略：按原类名一一对应拷贝到 `datasets/diseases/<类名>/`（identity 映射）。
  - 拷贝为“复制”而非“移动”，保留源数据以便溯源。
  - 若目标类目录不存在则新建；若同名文件存在则自动追加序号避免覆盖（理论上不会发生，因已加 uuid）。
- 执行命令：内置小脚本完成；统计产物见下。
- 结果统计：
  - 合并图片总数：2,572 张（train+test）。
  - 涉及 28 个类（如 Apple leaf / Corn leaf blight / Tomato leaf 等）。
  - 产物：`mappings/plantdoc_report.json`（每类计数、使用/新建目录、总数汇总）。

附：已生成全局清单 `mappings/dataset_universal_map.json`，汇总 `datasets/{crops,diseases,pests}` 各类目图片计数与来源标签占比（用于抽样与长尾补齐）。

**（待执行）PlantVillage/Plant Pathology（Kaggle）合并计划：**

- 工具配置：
  - 安装 kaggle CLI：`pip install kaggle`；放置 `~/.kaggle/kaggle.json`（从 Kaggle 账户页下载 API Token），权限 `chmod 600`。
  - 脚本：`scripts/fetch_kaggle_datasets.py`（下载+解压），`scripts/merge_kaggle_disease.py`（按类合并）。
- 推荐数据源（可二选一或多选）：
  - `alicelabs/new-plant-diseases-dataset`（PlantVillage 衍生整理版）
  - `muhammadardiputra/plantvillage-dataset`（原版组织）
  - `competitions/plant-pathology-2020-fgvc7`（竞赛数据，结构略异）
- 示例流程：
  1) 下载：`python3 scripts/fetch_kaggle_datasets.py --slug abdallahalidev/plantvillage-dataset --unzip`
  2) 重命名：`python3 scripts/bulk_rename_by_class.py --root sources/new-plant-diseases-dataset --tag kd --force`
  3) 合并：`python3 scripts/merge_kaggle_disease.py --src sources/new-plant-diseases-dataset --tag kd`
  4) 去重建议：`python3 scripts/deduplicate_images.py --roots datasets/diseases --min-width 224 --min-height 224 --blur-threshold 60 --action move`
  5) 更新索引：`python3 scripts/build_jsonl.py --roots datasets/diseases datasets/crops datasets/pests --out data.jsonl`

**2025-09-26（已执行）PlantVillage（color split）合并：**

- 源：`abdallahalidev/plantvillage-dataset`，解压后选用 `plantvillage dataset/color/` 作为主源；结构为 `Crop___Disease/` 类目录。
- 规范化：将 `Crop___Disease` 解析并映射到既有疾病命名，例如：
  - `Corn_(maize)___Northern_Leaf_Blight` → `Corn leaf blight`
  - `Pepper,_bell___Bacterial_spot` → `Bell_pepper leaf bacterial spot`
  - `Tomato___Tomato_Yellow_Leaf_Curl_Virus` → `Tomato leaf yellow virus`
- 过程：
  - 生成标准化目录：`sources/plantvillage-dataset/normalized_color/`（类名已统一为我们现有风格）。
  - 重命名为 `<类>__kd__<uuid>.<ext>`：`python3 scripts/bulk_rename_by_class.py --root sources/plantvillage-dataset/normalized_color --tag kd --force`
  - 合并：`python3 scripts/merge_kaggle_disease.py --src sources/plantvillage-dataset/normalized_color --tag kd`
- 结果：
  - 复制图片：46,072 张；产生报告：`mappings/normalized_color_merge_report.json`。
  - 复用目录（示例）：`Tomato Septoria leaf spot`、`Tomato leaf`、`Potato leaf early blight` 等。
  - 新增目录（示例）：`Apple Apple scab`、`Orange huanglongbing (citrus greening)`、`Soybean leaf` 等。

**2025-09-26（命名合并校准）：**

- 发现 `Soyabean leaf`（PlantDoc 拼写）与 `Soybean leaf`（PlantVillage 拼写）并列存在，以及 `Tomato two spotted spider mites leaf` 与 `Tomato two spotted spider mites` 重复。
- 处理方式：计算 MD5 去重后，将前者目录的唯一图片安全迁移至后者；重复样本移动到 `datasets/diseases/.trash/merged_duplicates_20250926_132209/` 备查。
- 结果：
  - `Soybean leaf` 现含 5,155 张图片；`Soyabean leaf` 目录已移除。
  - `Tomato two spotted spider mites` 现含 1,678 张图片；`Tomato two spotted spider mites leaf` 目录已移除。
- 备注：跳过的重复图片保留在 `.trash/merged_duplicates_*/`，后续清洗可统一删除或归档。
  - Wheat___Brown_Rust -> `datasets/diseases/Wheat brown rust` (新增)
  - Wheat___Yellow_Rust -> `datasets/diseases/Wheat yellow rust` (新增)
  - Wheat___Healthy -> `datasets/diseases/Wheat leaf` (新增)

- 重命名规范：拷贝到目标目录的文件统一重命名为
  `<目标类别>__cd__<uuid>.<ext>`（`__cd__` 表示来自 Crop Diseases，扩展名小写保留），避免与现有文件冲突并保持可追溯性。
  统一格式：<类别名><来源标签><uuid>.<ext>（扩展名小写）
    cd：Crop Diseases 来源（已在合并时使用）
    pd：PlantDoc/其他病害来源（已用于标准化 diseases 旧文件）
    ac：crops 来源（本次已应用）
    ap：pests 来源（本次已应用）

- 具体执行脚本：`scripts/merge_crop_diseases.py`（保留原始数据，仅拷贝到 datasets）

**统一重命名规范（适用于 diseases 类别目录）**

- 新文件名：`<类别名>__<来源标签>__<uuid>.<ext>`，扩展名统一为小写。
- 来源标签：`cd` 表示来自本地 `Crop Diseases`，`pd` 表示来自 PlantDoc 或其他病害来源。
- 合并脚本已按规范对 `Crop Diseases` 源进行重命名；对于 `datasets/diseases` 下尚未按规范命名的旧文件，可使用 `bulk_rename_by_class.py` 执行就地重命名。

**2025-09-25（统一命名应用到 crops 与 pests）**

- 对 `datasets/crops` 执行就地重命名，命名格式：`<类别名>__ac__<uuid>.<ext>`。
  - 命令：`python3 scripts/bulk_rename_by_class.py --root datasets/crops --tag ac`
- 对 `datasets/pests` 执行就地重命名，命名格式：`<类别名>__ap__<uuid>.<ext>`。
  - 命令：`python3 scripts/bulk_rename_by_class.py --root datasets/pests --tag ap`
- 说明：脚本会跳过已包含 `__cd__`/`__pd__`/`__ac__`/`__ap__` 的文件，避免重复改名；非图片文件自动跳过。
