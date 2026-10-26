# LeafScan AI Model Evaluation Report

**Model Evaluated:** `tomato_disease_model.h5`
**Architecture:** MobileNetV2 with custom `TrueDivide` & `Subtract` layers
**Taxonomy:** 3 classes (`Early Blight`, `Late Blight`, `Healthy Leaf`)

## Dataset: EVAL_DATA

- **Path:** `D:\projects\blight\Leafscan-main\ai-model\eval_data`
- **Total Images:** 180
- **Overall Accuracy:** 97.78%
- **Healthy False Alarm Rate:** 0.0%
- **Blight Missed Rate:** 0.0%

### Per-Class Performance

| Class | Precision | Recall | F1-Score | Support |
|---|---|---|---|---|
| Early Blight | 100.0% | 93.33% | 96.55% | 60 |
| Late Blight | 93.75% | 100.0% | 96.77% | 60 |
| Healthy Leaf | 100.0% | 100.0% | 100.0% | 60 |

### Confusion Matrix

| True / Pred | Early Blight | Late Blight | Healthy Leaf |
|---|---|---|---|
| **Early Blight** | 56 | 4 | 0 |
| **Late Blight** | 0 | 60 | 0 |
| **Healthy Leaf** | 0 | 0 | 60 |

## Dataset: EVAL_DATA_FIELD

- **Path:** `D:\projects\blight\Leafscan-main\ai-model\eval_data_field`
- **Total Images:** 233
- **Overall Accuracy:** 52.36%
- **Healthy False Alarm Rate:** 98.36%
- **Blight Missed Rate:** 0.58%

### Per-Class Performance

| Class | Precision | Recall | F1-Score | Support |
|---|---|---|---|---|
| Early Blight | 52.43% | 67.5% | 59.02% | 80 |
| Late Blight | 52.76% | 72.83% | 61.19% | 92 |
| Healthy Leaf | 50.0% | 1.64% | 3.17% | 61 |

### Confusion Matrix

| True / Pred | Early Blight | Late Blight | Healthy Leaf | Uncertain / Low Confidence |
|---|---|---|---|---|
| **Early Blight** | 54 | 25 | 0 | 1 |
| **Late Blight** | 24 | 67 | 1 | 0 |
| **Healthy Leaf** | 25 | 35 | 1 | 0 |

