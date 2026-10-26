"""
Download small LABELED public image sets so the model can be evaluated against ground truth.

Two sources (two different kinds of photo):
  plantvillage : lab photos (single leaf, plain background)  - https://github.com/spMohanty/PlantVillage-Dataset
  plantdoc     : real-world field photos (web-scraped, cluttered backgrounds)
                 - https://github.com/pratikkayal/PlantDoc-Dataset  ("test" and "train" splits)

Usage:
  python ai-model/download_eval_samples.py plantvillage [images_per_class]
  python ai-model/download_eval_samples.py plantdoc

Output (folder name = TRUE label, ready for ai-model/evaluate_model.py):
  ai-model/eval_data/        <- PlantVillage lab sample
  ai-model/eval_data_field/  <- PlantDoc field sample

Notes
-----
* PlantVillage images are picked at evenly spaced positions of the sorted file list (no cherry-picking).
* We do not know which images the original model was trained on, so the PlantVillage sample may
  overlap with its training set. The PlantDoc sample is a different kind of photo and is far less
  likely to overlap, which makes it a better test of real-world behaviour.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))

SOURCES = {
    'plantvillage': {
        'api': 'https://api.github.com/repos/spMohanty/PlantVillage-Dataset/contents/raw/color/{folder}',
        'folders': {  # remote folder -> local (true label) folder
            'Tomato___Early_blight': 'Tomato___Early_blight',
            'Tomato___Late_blight': 'Tomato___Late_blight',
            'Tomato___healthy': 'Tomato___healthy',
        },
        'out': os.path.join(HERE, 'eval_data'),
    },
    'plantdoc': {
        'api': [
            'https://api.github.com/repos/pratikkayal/PlantDoc-Dataset/contents/test/{folder}',
            'https://api.github.com/repos/pratikkayal/PlantDoc-Dataset/contents/train/{folder}',
        ],
        'folders': {
            'Tomato Early blight leaf': 'Tomato___Early_blight',
            'Tomato leaf late blight': 'Tomato___Late_blight',
            'Tomato leaf': 'Tomato___healthy',
        },
        'out': os.path.join(HERE, 'eval_data_field'),
    },
}


def _get(url):
    url = urllib.parse.quote(url, safe=':/?&=%')  # file names may contain spaces
    req = urllib.request.Request(url, headers={'User-Agent': 'leafscan-eval'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main(source, n_per_class=60):
    cfg = SOURCES[source]
    templates = cfg['api'] if isinstance(cfg['api'], list) else [cfg['api']]
    for remote, label in cfg['folders'].items():
        files = []
        for tpl in templates:
            listing = json.loads(_get(tpl.format(folder=urllib.parse.quote(remote))).decode())
            files += [e for e in listing if e['name'].lower().endswith(('.jpg', '.jpeg', '.png'))]
        files.sort(key=lambda e: e['name'])
        step = max(1, len(files) // n_per_class)
        chosen = files[::step][:n_per_class]
        dest = os.path.join(cfg['out'], label)
        os.makedirs(dest, exist_ok=True)
        print(f'{label}: {len(files)} in repo listing, downloading {len(chosen)}', flush=True)
        for i, e in enumerate(chosen):
            # numbered, sanitised name (some source names contain characters illegal on Windows)
            path = os.path.join(dest, f'{i:03d}.jpg')
            if os.path.exists(path):
                continue
            try:
                data = _get(e['download_url'])
            except Exception as exc:  # skip files that cannot be fetched
                print('  skipped', e['name'], exc, flush=True)
                continue
            with open(path, 'wb') as fh:
                fh.write(data)


if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else 'plantvillage'
    if src not in SOURCES:
        sys.exit(f'Unknown source {src!r}; choose from {list(SOURCES)}')
    main(src, int(sys.argv[2]) if len(sys.argv) > 2 else 60)
