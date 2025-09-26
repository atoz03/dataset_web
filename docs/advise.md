总体建议

明确任务统一格式：将图片转成“图像-文本对 + 标签”的多任务标注（分类/VQA/描述），避免只做纯分类。
建立统一本体（ontology）：规范“作物、病害、是否健康、来源、语言”字段，保证跨数据源一致性。
用标准文件名/路径信息作为弱标签：你已有 __cd__/__pd__/__ac__/__ap__ 和类目录名，可直接解析生成标签与文本。
数据组织与标注

文本对齐（Caption）：基于类目录生成中英双语模板描述，例如：
zh: “一张[作物]叶片，患有[病害名]。”；健康类：“一张健康的[作物]叶片。”
en: “A [crop] leaf showing [disease].”；健康：“A healthy [crop] leaf.”
VQA 指令化样本：为每张图合成问答对（中英双语），例如：
Q: “这张叶片得了什么病？”/“What disease is present?” → A: “玉米锈病/ Corn rust”
Q: “这片叶子是否健康？” → A: “是/否”
Q: “作物是什么？” → A: “玉米/ Corn”
多任务标签：存储 crop, disease, health, source（cd/pd/ac/ap）、language、split 等字段，便于混合训练。
数据清洗与预处理

去重与损坏检测：运行/扩展 scripts/deduplicate_images.py:1（建议加入感知哈希+尺寸阈值+模糊度(Laplacian)过滤）。
统一色彩与尺寸：转 sRGB；训练分辨率建议 ≥448（病斑细节更明显），必要时多尺度（448/576/672）。
质量筛选：剔除极低分辨率、严重压缩伪影、强反光遮挡样本。
数据划分与采样

分层划分：按类别与来源（cd/pd/ac/ap）进行 stratified train/val/test，防止源域泄漏；保留“跨来源测试集”做域外评估。
类别均衡：长尾类上采样或损失重加权（focal loss/调整类权重）；或在指令数据中增加难样本权重。
统一索引：导出 JSONL/CSV 索引（image_path, text, task, labels, source, split, lang）。
存储与加载格式

推荐 WebDataset（.tar 分片）或 JSONL + 本地路径：
WebDataset：高吞吐、易分布式；每类若过多可按 1–5k 样本/分片。
JSONL 示例字段：image, text, task, crop, disease, healthy, source, split, lang。
保留文件名中的来源标签和类名，解析为字段，便于溯源与调试。
模型与训练路线

视觉编码器：CLIP/SigLIP ViT-L/14, EVA-02, CoCa，分辨率≥448；农业小病斑建议更高输入或局部放大策略。
多模态架构：LLaVA/InternVL/Qwen-VL/BLIP-2/InstructBLIP 之一；先对齐（connector/Q-Former/投影头），再指令微调。
训练顺序（建议）：
视觉-文本对比/对齐（caption 模板弱监督 + 公开图文）；
指令微调（VQA、多任务问答、分类生成式回答）；
目标任务微调（病害/作物分类、健康判别、英文/中文双语）。
增强策略：轻度颜色抖动、随机裁剪、旋转；避免过重变换破坏病斑形态；可用MixUp/CutMix少量尝试但注意病斑语义。
评测与监控

指标：分类 Top-1/Top-5，VQA 字符串一致性/EM/F1；双语分别统计。
混淆矩阵：重点看相近病害（如早/晚疫、各类锈病）混淆。
迁移评估：跨来源（cd→pd / pd→cd）与跨作物泛化。
失效分析：对错误样本导出热图（Grad-CAM）确认关注区域是否覆盖病斑。
与你当前数据的快速可落地事项

解析并生成双语 JSONL 索引：
利用目录与中文对照表（已补全在 origin.md:1）生成 caption 与 VQA 样本。
从文件名解析来源标签（cd/pd/ac/ap），写入 source 字段。
按类别与来源分层划分 train/val/test（如 8/1/1），另建“跨来源测试集”。
选型与首版实验：
快速基线：CLIP ViT-B/16 或 SigLIP + 线性分类头，先做病害/健康/作物多头分类；
随后切换 LLaVA/InternVL 小尺寸骨干做多模态问答与分类生成，检验双语泛化。
如果你需要，我可以马上做的事

编写 scripts/build_jsonl.py：从 datasets/{diseases,crops,pests} 解析生成中英双语的 caption/VQA JSONL（含 source、split、labels）。
扩展 scripts/deduplicate_images.py:1：加入 phash + 模糊检测 + 尺寸过滤并批量清理。
输出 WebDataset 分片脚本：将 JSONL 索引的样本打包为 tar 分片以适配分布式训练。
提供 LLaVA/InternVL 训练用最小配置与数据管道模板（PyTorch + webdataset/JSONL 加载）。
告诉我你偏好的标注字段与 split 比例，我可以直接生成首版 JSONL 索引与打包脚本。
