# Guard false `off_focal` — Arm C vs Arm B

Generated: 2026-05-25T23:38:33.463598+00:00
Topology: `v1_next7_issue251_physical_severance_guarded_v1`

## Aggregate

- Arm C guard false positives: **24** / 66 guards
- Arm B baseline (full suite): **19** / 66
- Arm B FP-case subset under Arm C: **20** / 33

## Per-case (Arm B FP cases)

### NE-900T5
- Arm C FP: 3/3; fixed from Arm B: 0
  - sample 0: ArmB_FP=True dec=covered_change kinds=['off_focal'] S1=False
  - sample 1: ArmB_FP=True dec=covered_change kinds=['off_focal'] S1=False
  - sample 2: ArmB_FP=True dec=covered_change kinds=['off_focal'] S1=False

### NE-901T11
- Arm C FP: 2/3; fixed from Arm B: 1
  - sample 0: ArmB_FP=False dec=covered_change kinds=['off_focal'] S1=False
  - sample 1: ArmB_FP=False dec=covered_change kinds=['off_focal'] S1=False
  - sample 2: ArmB_FP=True dec=no_covered_change kinds=[] S1=True

### NE-901T5
- Arm C FP: 2/3; fixed from Arm B: 1
  - sample 0: ArmB_FP=True dec=None kinds=[] S1=False
  - sample 1: ArmB_FP=False dec=covered_change kinds=['off_focal'] S1=False
  - sample 2: ArmB_FP=False dec=covered_change kinds=['off_focal'] S1=False

### NE-910R10
- Arm C FP: 1/3; fixed from Arm B: 2
  - sample 0: ArmB_FP=True dec=no_covered_change kinds=[] S1=True
  - sample 1: ArmB_FP=True dec=no_covered_change kinds=[] S1=True
  - sample 2: ArmB_FP=True dec=covered_change kinds=['off_focal'] S1=False

### NE-910R11
- Arm C FP: 0/3; fixed from Arm B: 1
  - sample 0: ArmB_FP=False dec=no_covered_change kinds=[] S1=True
  - sample 1: ArmB_FP=True dec=no_covered_change kinds=[] S1=True
  - sample 2: ArmB_FP=False dec=covered_change kinds=['reentry'] S1=False

### NE-910R12
- Arm C FP: 2/3; fixed from Arm B: 1
  - sample 0: ArmB_FP=True dec=None kinds=[] S1=False
  - sample 1: ArmB_FP=False dec=covered_change kinds=['off_focal'] S1=False
  - sample 2: ArmB_FP=True dec=covered_change kinds=['off_focal'] S1=False

### NE-910R3T3
- Arm C FP: 3/3; fixed from Arm B: 0
  - sample 0: ArmB_FP=False dec=covered_change kinds=['off_focal'] S1=False
  - sample 1: ArmB_FP=True dec=covered_change kinds=['off_focal'] S1=False
  - sample 2: ArmB_FP=False dec=covered_change kinds=['off_focal'] S1=False

### NE-CTRL-GM2
- Arm C FP: 0/3; fixed from Arm B: 1
  - sample 0: ArmB_FP=False dec=no_covered_change kinds=[] S1=True
  - sample 1: ArmB_FP=False dec=None kinds=[] S1=False
  - sample 2: ArmB_FP=True dec=no_covered_change kinds=[] S1=True

### NE-GM4
- Arm C FP: 2/3; fixed from Arm B: 1
  - sample 0: ArmB_FP=True dec=covered_change kinds=['off_focal'] S1=False
  - sample 1: ArmB_FP=True dec=None kinds=[] S1=False
  - sample 2: ArmB_FP=False dec=covered_change kinds=['off_focal'] S1=False

### NE-P02
- Arm C FP: 3/3; fixed from Arm B: 0
  - sample 0: ArmB_FP=False dec=covered_change kinds=['off_focal'] S1=False
  - sample 1: ArmB_FP=True dec=covered_change kinds=['off_focal'] S1=False
  - sample 2: ArmB_FP=True dec=covered_change kinds=['off_focal'] S1=False

### NE-P05
- Arm C FP: 2/3; fixed from Arm B: 1
  - sample 0: ArmB_FP=True dec=covered_change kinds=['off_focal'] S1=False
  - sample 1: ArmB_FP=True dec=None kinds=[] S1=False
  - sample 2: ArmB_FP=False dec=covered_change kinds=['off_focal'] S1=False

