"""
Evaluate the LeafScan model (ai-model/models/best_int8.tflite, 15 classes) on a folder of
LABELED images, using exactly the same preprocessing / decision code as the web app.

Expected folder layout (folder name = true label):
    <data_dir>/Tomato___Early_blight/*.jpg
    <data_dir>/Tomato___Late_blight/*.jpg
    <data_dir>/Tomato___healthy/*.jpg
Folder names are matched to the app's class names (e.g. "Tomato___healthy" -> "Healthy Leaf").

Usage:
    python ai-model/evaluate_model.py [data_dir] [--threshold 0.25]
    python ai-model/download_eval_samples.py plantdoc   # field photos (recommended test set)

What it prints
--------------
1. For every true folder: how many images were predicted as each class, or "uncertain"
   (top score below the confidence threshold, i.e. the app would say "No clear disease found").
2. Recall per true class, plus the two numbers that matter most to a farmer:
   * healthy leaves wrongly called blight   (false alarm)
   * blight leaves called healthy           (missed disease)

CAVEAT: PlantDoc is a small web-scraped set. Treat the numbers as indicative, not as a proof
of real-world accuracy.
"""
import argparse
import os
import sys
from collections import Counter

os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'web-app', 'backend'))

from PIL import Image  # noqa: E402

UNCERTAIN = 'uncertain'
FOLDER_TO_LABEL = {
    'tomato___early_blight': 'Early Blight',
    'tomato___late_blight': 'Late Blight',
    'tomato___healthy': 'Healthy Leaf',
}
BLIGHT = ('Early Blight', 'Late Blight')


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
    folders = sorted(d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d)))
    items = []
    for folder in folders:
        for name in sorted(os.listdir(os.path.join(data_dir, folder))):
            if name.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                items.append((os.path.join(data_dir, folder, name), folder))
    return folders, items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('data_dir', nargs='?', default=os.path.join(HERE, 'eval_data_field'))
    ap.add_argument('--threshold', type=float, default=None,
                    help='confidence threshold (default: the app setting)')
    args = ap.parse_args()

    import app as backend
    model = backend.ensure_model_loaded()

    folders, items = load_images(args.data_dir)
    if not items:
        sys.exit(f'No images found in {args.data_dir}')

    predictions = {f: Counter() for f in folders}
    for path, folder in items:
        img = Image.open(path)
        scores = backend.score_classes(model.predict(backend.preprocess_image(img)))
        decision = backend.interpret_scores(scores, args.threshold)
        predictions[folder][UNCERTAIN if decision['uncertain'] else decision['label']] += 1

    threshold = backend.CONFIDENCE_THRESHOLD if args.threshold is None else args.threshold
    print(f'Model: {os.path.basename(backend.MODEL_PATH)}   threshold: {threshold}')
    print(f'Images: { {f: sum(c.values()) for f, c in predictions.items()} }\n')

    recall = {}
    for folder in folders:
        true_label = label_for_folder(folder, backend.CLASS_NAMES)
        counts = predictions[folder]
        total = sum(counts.values())
        print(f'[{folder}]  true label = {true_label}  (n={total})')
        for label, n in counts.most_common():
            marker = '  <-- correct' if label == true_label else ''
            print(f'    {label:<26}{n:>4}  ({n / total:.0%}){marker}')
        recall[true_label] = counts[true_label] / total
        print()

    print('Summary')
    for label, r in recall.items():
        print(f'  recall {label:<14}{r:.1%}')

    healthy = next((f for f in folders if label_for_folder(f, backend.CLASS_NAMES) == 'Healthy Leaf'), None)
    if healthy:
        c = predictions[healthy]
        total = sum(c.values())
        wrong = sum(c[b] for b in BLIGHT)
        print(f'  healthy leaves called blight (false alarm): {wrong}/{total} = {wrong / total:.1%}')
        print(f'  healthy leaves with no clear answer       : {c[UNCERTAIN]}/{total} = {c[UNCERTAIN] / total:.1%}')
    for folder in folders:
        if label_for_folder(folder, backend.CLASS_NAMES) in BLIGHT:
            c = predictions[folder]
            total = sum(c.values())
            print(f'  {folder} called healthy (missed disease): {c["Healthy Leaf"]}/{total} = {c["Healthy Leaf"] / total:.1%}')


if __name__ == '__main__':
    main()
