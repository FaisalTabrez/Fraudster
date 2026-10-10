# Third party notices

The URL adapter includes source and plain JSON model parameters from the pinned MIT-licensed phishing-url-detector commit. Its complete notice is in `phishing-url-detector-LICENSE.txt`. The model's training-data attribution is in `PhiUSIIL-ATTRIBUTION.md`. Exact copied paths and local changes are recorded in `third_party/manifest.json`. Other upstream assets require their own notice and manifest update before copying.

The text adapter retains `SmishX-LICENSE.txt` for its reviewed upstream guidance.

The OCR/QR dependency notices are retained here: PaddleOCR 2.9.1 and PaddlePaddle CPU 2.6.2 (Apache-2.0), imgaug 0.4.0 (MIT), ZXing browser 0.2.1 (MIT), and ZXing library 0.23.0 (Apache-2.0). No OCR/QR upstream implementation or model weights are redistributed in Git. The optional installer temporarily repackages PaddleOCR/imgaug with headless-only dependency metadata; implementation bytes are unchanged. See `third_party/manifest.json` for exact notice paths, release commits, package hashes, model archive sources/hashes, and local metadata changes. Before copying other upstream source or model assets, record their notices and exact paths in that manifest.
