# SkillForge evaluation eval-1fbaadfc4c465a19

Mode: **live**. Synthetic orders. Mock mode measures correctness and local runtime only; no LLM speedup claim.

| Arm | Cases | Pass | Unsafe | Model calls | p50 ms | p95 ms |
|---|---:|---:|---:|---:|---:|---:|
| react | 40 | 5 | 0 | 135 | 383.913 | 10092.11 |
| manual | 40 | 40 | 0 | 0 | 0.373 | 0.892 |
| compiled | 40 | 40 | 0 | 0 | 0.39 | 0.854 |
