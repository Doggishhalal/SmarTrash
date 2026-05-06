# SmarTrash YOLOX-L Training Guide

This project stays on YOLOX for a clean Apache-2.0 license path.

## 1) Prepare your dataset (YOLO format)
Expected layout:

```
<DATASET_DIR>/
  images/
    train/
    val/
  labels/
    train/
    val/
  data.yaml
```

Example `data.yaml`:

```
path: <DATASET_DIR>
train: images/train
val: images/val
names:
  0: plastic_bottle
  1: paper
  2: banana_peel
```

## 2) Configure auto retrain
Edit [backend/training_config.json](training_config.json):

- `dataset_dir`: absolute path to your dataset
- `train_command`: command list to start YOLOX training

Example (PowerShell style) training command list:

```
[
  "python",
  "YOLOX-main/tools/train.py",
  "-f",
  "YOLOX-main/exps/default/yolox_l.py",
  "-d",
  "1",
  "-b",
  "16",
  "-o",
  "--fp16",
  "-c",
  "C:\\models\\yolox_l.pth",
  "--cache",
  "--data",
  "<DATASET_DIR>\\data.yaml"
]
```

## 3) Model path
The app and API prefer `C:\\models\\yolox_l.pth`.
You can override with `YOLOX_CKPT`.

## 4) Self-optimization schedule
`interval_days` controls how often auto-retrain runs.
If `train_command` or `dataset_dir` are missing, retrain is skipped safely.

## Notes
- YOLOX-L is the default model for best accuracy.
- The system logs auto-retrain runs in the learning DB.
