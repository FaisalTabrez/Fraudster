# Fraudster URL service

This private service evaluates submitted URL **strings** using the pinned MIT-licensed [phishing-url-detector](https://github.com/Sarthakagrwal/phishing-url-detector) commit `8648994a2e2ff25eac8fe23b46705ecbcd27f296`. Its parser, 20 ordered features, heuristic rules, and plain JSON logistic model are bundled under `app/upstream/`. Prediction performs no DNS, HTTP, WHOIS, redirects, or page fetches. The upstream CLI, browser code, and joblib file are not included.

`GET /health/ready` is 200 only when the JSON model loads and its feature order matches the extractor. `POST /predict` accepts one to five strings of at most 2,048 raw characters and returns the private gateway `ModuleResult` shape. The score is the upstream 0–100 **blended policy score** (`raw_score_type: upstream_blended_score_0_100`), not Fraudster's aggregate risk score or a calibrated fraud probability. The upstream lower band is not a safety guarantee.

The model metadata attributes training to the PhiUSIIL Phishing URL Dataset by Arvind Prasad and Shalini Chandra (UCI #967, CC BY 4.0) and documents synthetic legitimate deep-link augmentation. Those upstream metadata and scores are not Fraudster performance results. Attribution and the complete MIT notice are recorded in `third_party/manifest.json`, `third_party/licenses/PhiUSIIL-ATTRIBUTION.md`, and `third_party/licenses/phishing-url-detector-LICENSE.txt`.

Run with Python 3.13 or newer:

```powershell
py -3.13 -m venv .venv-url
.\.venv-url\Scripts\python.exe -m pip install -r services\url\requirements-dev.txt
$env:PYTHONPATH = (Get-Location).Path
.\.venv-url\Scripts\python.exe -m pytest -q services\url\tests
```

AKH-02 will expand feature-level evidence and malformed/edge-case coverage. The service remains a private adapter behind the gateway.
