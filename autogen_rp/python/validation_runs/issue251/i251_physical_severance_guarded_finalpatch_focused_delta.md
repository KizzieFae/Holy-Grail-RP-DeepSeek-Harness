# Guard/threshold delta — simplified Arm C focused

Generated: 2026-05-26T02:05:46.819390+00:00
Doctrine variant: `simplified_structural_finalpatch_v1`

## Aggregate (guard cohort only)

| Source | guard FP | guard n |
|--------|----------|---------|
| **Simplified Arm C (this run)** | 4 | 15 |
| Arm B (same cases/samples) | 8 | 15 |
| Old Arm C cinematic (same cases/samples) | 11 | 15 |

## Per-case

### NE-900T5
- Simplified: **0/3** FP | Arm B: **3/3** | Old Arm C: **3/3**
  - sample 0: dec=None kinds=[] S1=False L3=False L2_fp=False (B_fp=True C_fp=True)
  - sample 1: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=True C_fp=True)
  - sample 2: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=True C_fp=True)

### NE-901T5
- Simplified: **0/3** FP | Arm B: **1/3** | Old Arm C: **2/3**
  - sample 0: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=True C_fp=False)
  - sample 1: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=False C_fp=True)
  - sample 2: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=False C_fp=True)

### NE-GM4
- Simplified: **2/3** FP | Arm B: **2/3** | Old Arm C: **2/3**
  - sample 0: dec=covered_change kinds=['off_focal'] S1=False L3=False L2_fp=True (B_fp=True C_fp=True)
  - sample 1: dec=covered_change kinds=['off_focal'] S1=False L3=False L2_fp=True (B_fp=True C_fp=False)
  - sample 2: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=False C_fp=True)

### NE-P02
- Simplified: **2/3** FP | Arm B: **2/3** | Old Arm C: **3/3**
  - sample 0: dec=covered_change kinds=['off_focal'] S1=False L3=False L2_fp=True (B_fp=False C_fp=True)
  - sample 1: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=True C_fp=True)
  - sample 2: dec=covered_change kinds=['off_focal'] S1=False L3=False L2_fp=True (B_fp=True C_fp=True)

### NE-P04
- Simplified: **0/3** FP | Arm B: **0/3** | Old Arm C: **1/3**
  - sample 0: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=False C_fp=True)
  - sample 1: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=False C_fp=False)
  - sample 2: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=False C_fp=False)

