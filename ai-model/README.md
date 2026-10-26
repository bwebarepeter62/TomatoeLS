# Tomato Leaf Scan — AI Model Documentation

## Overview
This directory contains the computer vision model assets, architectural specifications, and tensor guidelines utilized by Tomato Leaf Scan for automated foliar disease detection.

- **Model File:** `ai-model/models/best_int8.tflite`
- **File Size on Disk:** 26,525,590 bytes (~26.5 MB)
- **Architecture:** Ultralytics YOLOv8 (Single-Stage Object Detector)
- **Deployment Format:** TensorFlow Lite (INT8 Quantized Weights with Float32 Dequantized I/O)
- **Target Hardware:** Standard Commodity CPU (using LiteRT / XNNPACK Delegate)

---

## Verifiable Model Specifications

| Parameter | Specification | Description |
|---|---|---|
| **Input Shape** | `[1, 3, 640, 640]` | Batch=1, Channels=3 (RGB), Height=640, Width=640 (NCHW) |
| **Input Data Type** | `numpy.float32` | Requires pixel normalization to $[0.0, 1.0]$ |
| **Output Shape** | `[1, 19, 8400]` | Batch=1, 19 Channels, 8,400 Multi-Scale Candidate Anchors |
| **Channel Breakdown** | `4 + 15 = 19` | 4 bounding box values `[cx, cy, w, h]` + 15 class probabilities |
| **Total Anchors** | 8,400 | Sum of multi-scale grid cells: $80^2 (6400) + 40^2 (1600) + 20^2 (400)$ |
| **Confidence Threshold** | $\ge 0.25$ (25%) | Minimum class score required to retain a candidate anchor |
| **NMS IoU Threshold** | $0.45$ (45%) | Overlap threshold to collapse duplicate detections |

---

## Detectable Foliar Conditions (15 Classes)

The model's 15 output channels map to the following condition classes:

| Index | Raw Model Label | Clean Display Label | Pathology Group |
|:---:|---|---|:---:|
| 0 | `Aphids` | Aphids | Pest |
| 1 | `Early Blight` | Early Blight (*Alternaria solani*) | Fungal |
| 2 | `Healthy Leaf-` | Healthy Leaf | None |
| 3 | `Leaf Curl` | Leaf Curl | Viral |
| 4 | `Leafhoppers and Jassids` | Leafhoppers and Jassids | Pest |
| 5 | `Molds` | Leaf Mold (*Passalora fulva*) | Fungal |
| 6 | `Mosaic Virus` | Tomato Mosaic Virus (ToMV) | Viral |
| 7 | `Septoria` | Septoria Leaf Spot | Fungal |
| 8 | `bactarial canker` | Bacterial Canker (*Clavibacter*) | Bacterial |
| 9 | `bacterial spot` | Bacterial Spot (*Xanthomonas*) | Bacterial |
| 10 | `flea beetle` | Flea Beetle | Pest |
| 11 | `late_blight` | Late Blight (*Phytophthora infestans*) | Fungal |
| 12 | `leafminer` | Leafminer (*Liriomyza*) | Pest |
| 13 | `powedry_mildew` | Powdery Mildew | Fungal |
| 14 | `yellow curl virus` | Yellow Leaf Curl Virus (TYLCV) | Viral |

---

## Inference Execution Pipeline

```text
[Input Image: JPG / PNG]
       │
       ▼
[Pillow]: Convert to RGB and resize to 640x640 Bilinear
       │
       ▼
[NumPy]: Normalize array (arr / 255.0) and transpose to NCHW [1, 3, 640, 640]
       │
       ▼
[TFLite Interpreter]: interpreter.invoke()
       │
       ▼
[Raw Output]: [1, 19, 8400] tensor
       │
       ▼
[parse_output()]: Slices 8400 anchors, filters confidence >= 0.25, decodes [cx,cy,w,h]
       │
       ▼
[Non-Maximum Suppression]: Collapses overlapping boxes (IoU > 0.45)
       │
       ▼
[Agronomic Knowledge Base]: Maps top class to DAMAGE_DB treatment guidance
```

---

## Model Provenance & Academic Integrity Notes

1. **Inference Only:** The current application repository executes model **inference only**. It loads pre-compiled weights from `best_int8.tflite`.
2. **Absence of Training Code in Repo:** Raw training scripts, loss curves, and original training datasets are not included in this repository.
3. **Training Data Origin:** The 15 classes and naming quirks (`bactarial canker`, `powedry_mildew`, `Healthy Leaf-`) indicate that the model was trained externally on an expanded dataset (likely derived from the public PlantVillage benchmark augmented with field pest categories).
4. **Accuracy Claims:** Empirical field accuracy across diverse real-world lighting and field environments must be verified through local testing rather than asserted as an unverified percentage.
