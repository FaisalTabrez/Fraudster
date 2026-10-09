# PhiUSIIL dataset attribution

The bundled `services/url/app/upstream/model_meta.json` contains parameters of a model trained upstream using the **PhiUSIIL Phishing URL (Website)** dataset by Arvind Prasad and Shalini Chandra (2024), UCI Machine Learning Repository, [dataset #967](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset), DOI [10.1016/j.cose.2023.103545](https://doi.org/10.1016/j.cose.2023.103545).

The dataset is licensed under [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/). The upstream phishing-url-detector project trained a StandardScaler and logistic regression on URL strings from the dataset, augmented the legitimate class with synthetic deep links, and exported the parameters to plain JSON. Fraudster copies that pinned JSON file without retraining or modifying its parameter values. The dataset itself is not bundled. Upstream reported metrics are not Fraudster performance measurements.
