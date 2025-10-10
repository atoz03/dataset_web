# Memory Summary (Datasets Web Project)

- Structure: `datasets/{crops,pests,diseases}` plus original `Crop Diseases/` source.
- Naming convention: `<class>__<tag>__<uuid>.<ext>` (lowercase ext).
  - Tags: `cd` (Crop Diseases), `pd` (PlantDoc/other disease), `ac` (crops), `ap` (pests).
- Merge mapping: Crop Diseases classes mapped into diseases (e.g., Corn___Common_Rust → Corn rust leaf; Potato___Early_Blight → Potato leaf early blight; Rice___Neck_Blast → Rice neck blast; Wheat___Healthy → Wheat leaf; Sugarcane_Healthy → Sugarcane leaf). Healthy classes mapped to `<Crop> leaf`.
- Scripts:
  - `merge_crop_diseases.py`: copy from `Crop Diseases/` into `datasets/diseases/` using mapping; rename to `<class>__cd__<uuid>.<ext>`; idempotent. Result: 13,324 images copied.
  - `bulk_rename_by_class.py`: normalize filenames in-place to the standard pattern; skips files already containing `__cd__/__pd__/__ac__/__ap__`; supports `--dry-run` and `--force`.
    - Applied to diseases (pd): processed 15,899, renamed 2,575, skipped 13,324.
    - Applied to crops (ac): processed 1,823, renamed 1,816, skipped 7.
    - Applied to pests (ap): processed 5,494, renamed 5,494, skipped 0.
  - `deduplicate_images.py`: enhanced with pHash/aHash dedupe, Laplacian blur filter, min size filter; supports `.trash` move or delete; configurable thresholds and near-duplicate Hamming distance.
  - `build_jsonl.py`: generates bilingual JSONL (caption + VQA) for images in diseases/crops/pests; stratified splits per class; labels include root/class/crop/disease/pest/healthy/source; defaults to 0.8/0.1/0.1.
- Documents:
  - `origin.md`: sources 1–6 recorded with links; added class mapping note; bilingual directory mapping; renaming policy; crops/pests renaming log.
  - `origin2.md`: process log + step-by-step workflow and TODOs for future work (stats scripts, split files, cross-source holdout, WebDataset packing, license/citation, validators, EXIF/sRGB normalization).
- Key practices: copy-not-move merges; keep provenance via tags; run cleanup with `--action move` first; record every change in origin.md/origin2.md; stratified splits by class and (optionally) source.
- Open TODOs (high priority):
  1) Stats per class and per source to CSV. 2) Size/aspect distributions and random visual QC. 3) JSONL split files and optional cross-source test set. 4) WebDataset pack + manifests. 5) License/Citation fields per source. 6) Naming/whitelist validator. 7) Optional EXIF orientation fix + sRGB conversion.

