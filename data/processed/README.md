# Processed Datasets Directory

Store cleaned human dialogue sessions in standard JSON format:
```json
[
  {
    "id": "conv_001",
    "turns": [
      {"user": "...", "assistant": "..."},
      ...
    ]
  }
]
```
These normalized files are consumed by `scripts/build_human_baseline.py` to fit mean vectors and covariance matrices.
