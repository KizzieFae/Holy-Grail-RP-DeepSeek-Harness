# Guard/threshold delta — simplified Arm C focused

Generated: 2026-05-26T00:37:52.212135+00:00
Doctrine variant: `simplified_structural_v1`

## Aggregate (guard cohort only)

| Source | guard FP | guard n |
|--------|----------|---------|
| **Simplified Arm C (this run)** | 4 | 33 |
| Arm B (same cases/samples) | 15 | 33 |
| Old Arm C cinematic (same cases/samples) | 17 | 33 |

## Per-case

### NE-900T5
- Simplified: **0/3** FP | Arm B: **3/3** | Old Arm C: **3/3**
  - sample 0: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=True C_fp=True)
  - sample 1: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=True C_fp=True)
  - sample 2: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=True C_fp=True)

### NE-900T9
- Simplified: **0/3** FP | Arm B: **0/3** | Old Arm C: **1/3**
  - sample 0: dec=None kinds=[] S1=False L3=False L2_fp=False (B_fp=False C_fp=False)
  - sample 1: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=False C_fp=True)
  - sample 2: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=False C_fp=False)

### NE-901T5
- Simplified: **0/3** FP | Arm B: **1/3** | Old Arm C: **2/3**
  - sample 0: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=True C_fp=False)
  - sample 1: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=False C_fp=True)
  - sample 2: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=False C_fp=True)

### NE-910R10
- Simplified: **1/3** FP | Arm B: **3/3** | Old Arm C: **1/3**
  - sample 0: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=True C_fp=False)
  - sample 1: dec=covered_change kinds=['off_focal'] S1=False L3=False L2_fp=True (B_fp=True C_fp=False)
  - sample 2: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=True C_fp=True)

### NE-910R11
- Simplified: **0/3** FP | Arm B: **1/3** | Old Arm C: **0/3**
  - sample 0: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=False C_fp=False)
  - sample 1: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=True C_fp=False)
  - sample 2: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=False C_fp=False)

### NE-910R12
- Simplified: **0/3** FP | Arm B: **2/3** | Old Arm C: **2/3**
  - sample 0: dec=None kinds=[] S1=False L3=False L2_fp=False (B_fp=True C_fp=False)
  - sample 1: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=False C_fp=True)
  - sample 2: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=True C_fp=True)

### NE-910R9
- Simplified: **0/3** FP | Arm B: **0/3** | Old Arm C: **2/3**
  - sample 0: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=False C_fp=False)
  - sample 1: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=False C_fp=True)
  - sample 2: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=False C_fp=True)

### NE-CTRL-GM2
- Simplified: **0/3** FP | Arm B: **1/3** | Old Arm C: **0/3**
  - sample 0: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=False C_fp=False)
  - sample 1: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=False C_fp=False)
  - sample 2: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=True C_fp=False)

### NE-GM4
- Simplified: **2/3** FP | Arm B: **2/3** | Old Arm C: **2/3**
  - sample 0: dec=covered_change kinds=['off_focal'] S1=False L3=False L2_fp=True (B_fp=True C_fp=True)
  - sample 1: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=True C_fp=False)
  - sample 2: dec=covered_change kinds=['off_focal'] S1=False L3=False L2_fp=True (B_fp=False C_fp=True)

### NE-P02
- Simplified: **0/3** FP | Arm B: **2/3** | Old Arm C: **3/3**
  - sample 0: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=False C_fp=True)
  - sample 1: dec=None kinds=[] S1=False L3=False L2_fp=False (B_fp=True C_fp=True)
  - sample 2: dec=None kinds=[] S1=False L3=False L2_fp=False (B_fp=True C_fp=True)

### NE-P04
- Simplified: **1/3** FP | Arm B: **0/3** | Old Arm C: **1/3**
  - sample 0: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=False C_fp=True)
  - sample 1: dec=covered_change kinds=['off_focal'] S1=False L3=False L2_fp=True (B_fp=False C_fp=False)
  - sample 2: dec=no_covered_change kinds=[] S1=True L3=True L2_fp=False (B_fp=False C_fp=False)

