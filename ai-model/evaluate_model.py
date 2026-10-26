"""
LeafScan Model Evaluation Script
================================
Evaluates the LeafScan Keras model (tomato_disease_model.h5, 3 classes:
Early Blight, Late Blight, Healthy Leaf) on labeled ground-truth datasets.

Supported datasets:
  - ai-model/eval_data/       : PlantVillage lab photos (single leaf on plain background)
  - ai-model/eval_data_field/ : PlantDoc real-world field photos (natural farm conditions)

Metrics produced:
  - Confusion Matrix
  - Overall Accuracy
  - Per-class Precision, Recall, and F1-score
  - Healthy-leaf false positive rate (false alarms)
  - Blight false negative rate (missed infections)
  - Audit of misclassified samples
  - Report saved to ai-model/eval_results/

Usage:
  python ai-model/evaluate_model.py [data_dir] [--threshold 0.50] [--output-dir DIR]
  python ai-model/evaluate_model.py all
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'web-app', 'backend'))

from PIL import Image  # noqa: E402
import numpy as np

UNCERTAIN = 'Uncertain / Low Confidence'
FOLDER_TO_LABEL = {
    'tomato___early_blight': 'Early Blight',
    'tomato___late_blight': 'Late Blight',
    'tomato___healthy': 'Healthy Leaf',
}
TARGET_CLASSES = ['Early Blight', 'Late Blight', 'Healthy Leaf']
BLIGHT_CLASSES = ('Early Blight', 'Late Blight')


def label_for_folder(folder, class_names):
    key = folder.lower()
    if key in FOLDER_TO_LABEL:
        return FOLDER_TO_LABEL[key]
    norm = key.replace('_', ' ')
    for name in class_names:
        if name.lower() == norm:
            return name
    return folder


def load_images(data_dir):
    if not os.path.isdir(data_dir):
        return [], []
    folders = sorted(d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d)))
    items = []
    for folder in folders:
        folder_path = os.path.join(data_dir, folder)
        for name in sorted(os.listdir(folder_path)):
            if name.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                items.append((os.path.join(folder_path, name), folder, name))
    return folders, items


def evaluate_dataset(backend, data_dir, threshold=None):
    folders, items = load_images(data_dir)
    if not items:
        print(f"No valid images found in {data_dir}")
        return None

    dataset_name = os.path.basename(os.path.normpath(data_dir))
    print(f"\n{'='*70}")
    print(f"EVALUATING DATASET: {dataset_name} ({len(items)} images)")
    print(f"{'='*70}")

    # Set threshold override if provided
    orig_threshold = backend.CONFIDENCE_THRESHOLD
    if threshold is not None:
        backend.CONFIDENCE_THRESHOLD = threshold

    try:
        y_true = []
        y_pred = []
        raw_results = []
        misclassified = []

        for path, folder, filename in items:
            true_label = label_for_folder(folder, backend.CLASS_NAMES)
            try:
                img = Image.open(path)
                res = backend.build_result_for_image(img)
            except Exception as exc:
                print(f"  [ERROR] Failed to process {filename}: {exc}")
                continue

            pred_label = res.get('label', UNCERTAIN)
            # Map "Healthy leaf - no disease detected." to standard label "Healthy Leaf"
            if 'healthy' in pred_label.lower():
                pred_label = 'Healthy Leaf'
            elif res.get('uncertain', False):
                pred_label = UNCERTAIN

            conf = res.get('confidence', 0.0)
            scores = {p['class']: p['confidence'] for p in res.get('predictions', [])}

            y_true.append(true_label)
            y_pred.append(pred_label)

            is_correct = (pred_label == true_label)
            raw_results.append({
                'filename': filename,
                'path': path,
                'true_label': true_label,
                'predicted_label': pred_label,
                'confidence': conf,
                'scores': scores,
                'is_correct': is_correct,
            })

            if not is_correct:
                misclassified.append({
                    'filename': filename,
                    'folder': folder,
                    'true_label': true_label,
                    'predicted_label': pred_label,
                    'confidence': conf,
                    'scores': scores,
                })
    finally:
        backend.CONFIDENCE_THRESHOLD = orig_threshold

    # Calculate metrics
    classes = TARGET_CLASSES + ([UNCERTAIN] if any(p == UNCERTAIN for p in y_pred) else [])
    
    # 1. Confusion Matrix
    # matrix[true_idx][pred_idx]
    cm = {t: {p: 0 for p in classes} for t in TARGET_CLASSES}
    for t, p in zip(y_true, y_pred):
        if t in cm and p in cm[t]:
            cm[t][p] += 1

    # 2. Per-class Precision, Recall, F1
    metrics = {}
    total_samples = len(y_true)
    correct_samples = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    overall_accuracy = correct_samples / total_samples if total_samples > 0 else 0.0

    for cls in TARGET_CLASSES:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == cls and p == cls)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != cls and p == cls)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == cls and p != cls)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        support = sum(1 for t in y_true if t == cls)

        metrics[cls] = {
            'precision': round(precision * 100, 2),
            'recall': round(recall * 100, 2),
            'f1_score': round(f1 * 100, 2),
            'support': support,
            'tp': tp,
            'fp': fp,
            'fn': fn,
        }

    # 3. Healthy False Positive Rate (False Alarm)
    healthy_total = sum(1 for t in y_true if t == 'Healthy Leaf')
    healthy_called_blight = sum(1 for t, p in zip(y_true, y_pred) if t == 'Healthy Leaf' and p in BLIGHT_CLASSES)
    healthy_fp_rate = (healthy_called_blight / healthy_total * 100) if healthy_total > 0 else 0.0

    # 4. Blight False Negative Rate (Missed Infection)
    blight_total = sum(1 for t in y_true if t in BLIGHT_CLASSES)
    blight_called_healthy = sum(1 for t, p in zip(y_true, y_pred) if t in BLIGHT_CLASSES and p == 'Healthy Leaf')
    blight_fn_rate = (blight_called_healthy / blight_total * 100) if blight_total > 0 else 0.0

    # Print Summary Table
    print(f"\nModel: {os.path.basename(backend.MODEL_PATH)}")
    print(f"Overall Accuracy: {overall_accuracy:.2%} ({correct_samples}/{total_samples})")
    print(f"\n{'Classification Report':^60}")
    print(f"{'-'*60}")
    print(f"{'Class':<18}{'Precision':>10}{'Recall':>10}{'F1-Score':>10}{'Support':>10}")
    print(f"{'-'*60}")
    for cls in TARGET_CLASSES:
        m = metrics[cls]
        print(f"{cls:<18}{m['precision']:>9.1f}%{m['recall']:>9.1f}%{m['f1_score']:>9.1f}%{m['support']:>10}")
    print(f"{'-'*60}")
    print(f"Healthy-leaf false alarm rate (called Blight): {healthy_called_blight}/{healthy_total} = {healthy_fp_rate:.1f}%")
    print(f"Blight missed infection rate (called Healthy): {blight_called_healthy}/{blight_total} = {blight_fn_rate:.1f}%")

    print(f"\n--- Confusion Matrix ---")
    headers = [f"{c[:10]:>12}" for c in classes]
    title_col = 'True / Pred'
    print(f"{title_col:<16}" + "".join(headers))
    for t in TARGET_CLASSES:
        row_str = f"{t:<16}"
        for c in classes:
            row_str += f"{cm[t][c]:>12}"
        print(row_str)

    report_data = {
        'dataset_name': dataset_name,
        'dataset_path': data_dir,
        'total_images': total_samples,
        'correct_images': correct_samples,
        'overall_accuracy': round(overall_accuracy * 100, 2),
        'metrics': metrics,
        'healthy_fp_rate': round(healthy_fp_rate, 2),
        'blight_fn_rate': round(blight_fn_rate, 2),
        'confusion_matrix': cm,
        'misclassified_count': len(misclassified),
        'misclassified_samples': misclassified[:20],  # sample first 20 for brevity
    }

    return report_data


def main():
    ap = argparse.ArgumentParser(description="Evaluate LeafScan AI Model on Ground Truth Datasets")
    ap.add_argument('dataset', nargs='?', default='all',
                    help="'all', 'lab' (eval_data), 'field' (eval_data_field), or custom directory path")
    ap.add_argument('--threshold', type=float, default=None,
                    help='Confidence threshold (default: app setting 0.50)')
    ap.add_argument('--output-dir', default=os.path.join(HERE, 'eval_results'),
                    help='Directory to save evaluation reports and metrics')
    args = ap.parse_args()

    import app as backend
    backend.ensure_model_loaded()

    datasets_to_run = []
    if args.dataset == 'all':
        datasets_to_run = [
            os.path.join(HERE, 'eval_data'),
            os.path.join(HERE, 'eval_data_field'),
        ]
    elif args.dataset == 'lab':
        datasets_to_run = [os.path.join(HERE, 'eval_data')]
    elif args.dataset == 'field':
        datasets_to_run = [os.path.join(HERE, 'eval_data_field')]
    else:
        datasets_to_run = [os.path.abspath(args.dataset)]

    os.makedirs(args.output_dir, exist_ok=True)
    all_reports = {}

    for d in datasets_to_run:
        if not os.path.exists(d):
            print(f"Skipping non-existent directory: {d}")
            continue
        report = evaluate_dataset(backend, d, threshold=args.threshold)
        if report:
            ds_name = report['dataset_name']
            all_reports[ds_name] = report
            
            # Save individual JSON report
            json_path = os.path.join(args.output_dir, f"evaluation_{ds_name}.json")
            with open(json_path, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"  [SAVED] Structured report saved to {json_path}")

    # Save consolidated summary markdown
    md_path = os.path.join(args.output_dir, "EVALUATION_REPORT.md")
    with open(md_path, 'w') as f:
        f.write("# LeafScan AI Model Evaluation Report\n\n")
        f.write(f"**Model Evaluated:** `{os.path.basename(backend.MODEL_PATH)}`\n")
        f.write(f"**Architecture:** MobileNetV2 with custom `TrueDivide` & `Subtract` layers\n")
        f.write(f"**Taxonomy:** 3 classes (`Early Blight`, `Late Blight`, `Healthy Leaf`)\n\n")
        
        for name, rep in all_reports.items():
            f.write(f"## Dataset: {name.upper()}\n\n")
            f.write(f"- **Path:** `{rep['dataset_path']}`\n")
            f.write(f"- **Total Images:** {rep['total_images']}\n")
            f.write(f"- **Overall Accuracy:** {rep['overall_accuracy']}%\n")
            f.write(f"- **Healthy False Alarm Rate:** {rep['healthy_fp_rate']}%\n")
            f.write(f"- **Blight Missed Rate:** {rep['blight_fn_rate']}%\n\n")
            
            f.write("### Per-Class Performance\n\n")
            f.write("| Class | Precision | Recall | F1-Score | Support |\n")
            f.write("|---|---|---|---|---|\n")
            for cls, m in rep['metrics'].items():
                f.write(f"| {cls} | {m['precision']}% | {m['recall']}% | {m['f1_score']}% | {m['support']} |\n")
            f.write("\n")

            f.write("### Confusion Matrix\n\n")
            cols = list(list(rep['confusion_matrix'].values())[0].keys())
            f.write("| True / Pred | " + " | ".join(cols) + " |\n")
            f.write("|" + "---|" * (len(cols) + 1) + "\n")
            for t_cls, row in rep['confusion_matrix'].items():
                f.write(f"| **{t_cls}** | " + " | ".join(str(row[c]) for c in cols) + " |\n")
            f.write("\n")

    print(f"\n[DONE] Consolidated markdown report generated at: {md_path}")


if __name__ == '__main__':
    main()

