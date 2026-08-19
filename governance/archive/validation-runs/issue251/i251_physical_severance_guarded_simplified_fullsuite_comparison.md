# Full-suite comparison — simplified structural Arm C

Generated: 2026-05-26T01:41:38.033962+00:00
Samples: 103 | Excluded: ['901-T9', 'P03']

## Aggregate metrics

| Metric | Simplified (full) | Arm B | Old Arm C | Focused simplified |
|--------|-----------------|-------|-----------|-------------------|
| Guard false `off_focal` | 10/66 (0.152) | 19/66 (0.288) | 24/66 (0.364) | 4/33 (0.121) |
| GM3 S1/L3 | 5/10 | 5/10 | 4/10 | 6/10 |
| Threshold exit S1 rate | 0.2 | 0.4 | 0.333 | — |
| Explicit exit S1 rate | 0.5 | 0.583 | 0.583 | — |
| Ambiguous (L2) | 0.204 | 0.243 | 0.262 | 0.145 |

## Key cases

### NE-900T5

- Samples: 3 | Simplified FP: 0
  - si0: dec=None kinds=[] S1=False exp=no_covered_change
    - B: dec=covered_change kinds=['off_focal']
    - oldC: dec=covered_change kinds=['off_focal']
    - focused: dec=no_covered_change kinds=[]
  - si1: dec=no_covered_change kinds=[] S1=True exp=no_covered_change
    - B: dec=covered_change kinds=['off_focal']
    - oldC: dec=covered_change kinds=['off_focal']
    - focused: dec=no_covered_change kinds=[]
  - si2: dec=no_covered_change kinds=[] S1=True exp=no_covered_change
    - B: dec=covered_change kinds=['off_focal']
    - oldC: dec=covered_change kinds=['off_focal']
    - focused: dec=no_covered_change kinds=[]

### NE-P02

- Samples: 3 | Simplified FP: 0
  - si0: dec=no_covered_change kinds=[] S1=True exp=no_covered_change
    - B: dec=no_covered_change kinds=[]
    - oldC: dec=covered_change kinds=['off_focal']
    - focused: dec=no_covered_change kinds=[]
  - si1: dec=None kinds=[] S1=False exp=no_covered_change
    - B: dec=covered_change kinds=['off_focal']
    - oldC: dec=covered_change kinds=['off_focal']
    - focused: dec=None kinds=[]
  - si2: dec=no_covered_change kinds=[] S1=True exp=no_covered_change
    - B: dec=covered_change kinds=['off_focal']
    - oldC: dec=covered_change kinds=['off_focal']
    - focused: dec=None kinds=[]

### NE-901T5

- Samples: 3 | Simplified FP: 0
  - si0: dec=None kinds=[] S1=False exp=no_covered_change
    - B: dec=covered_change kinds=['off_focal']
    - oldC: dec=None kinds=[]
    - focused: dec=no_covered_change kinds=[]
  - si1: dec=no_covered_change kinds=[] S1=True exp=no_covered_change
    - B: dec=None kinds=[]
    - oldC: dec=covered_change kinds=['off_focal']
    - focused: dec=no_covered_change kinds=[]
  - si2: dec=no_covered_change kinds=[] S1=True exp=no_covered_change
    - B: dec=no_covered_change kinds=[]
    - oldC: dec=covered_change kinds=['off_focal']
    - focused: dec=no_covered_change kinds=[]

### NE-GM4

- Samples: 3 | Simplified FP: 3
  - si0: dec=covered_change kinds=['off_focal'] S1=False exp=no_covered_change
    - B: dec=covered_change kinds=['off_focal']
    - oldC: dec=covered_change kinds=['off_focal']
    - focused: dec=covered_change kinds=['off_focal']
  - si1: dec=covered_change kinds=['off_focal'] S1=False exp=no_covered_change
    - B: dec=covered_change kinds=['off_focal']
    - oldC: dec=None kinds=[]
    - focused: dec=no_covered_change kinds=[]
  - si2: dec=covered_change kinds=['off_focal'] S1=False exp=no_covered_change
    - B: dec=None kinds=[]
    - oldC: dec=covered_change kinds=['off_focal']
    - focused: dec=covered_change kinds=['off_focal']

### EXIT-B-910R5T3

- Samples: 3 | Simplified FP: 0
  - si0: dec=None kinds=[] S1=False exp=off_focal
    - B: dec=no_covered_change kinds=[]
    - oldC: dec=None kinds=[]
    - focused: dec=no_covered_change kinds=[]
  - si1: dec=no_covered_change kinds=[] S1=False exp=off_focal
    - B: dec=None kinds=[]
    - oldC: dec=no_covered_change kinds=[]
    - focused: dec=None kinds=[]
  - si2: dec=no_covered_change kinds=[] S1=False exp=off_focal
    - B: dec=covered_change kinds=['off_focal']
    - oldC: dec=covered_change kinds=['off_focal']
    - focused: dec=no_covered_change kinds=[]

### EXIT-C-GM3

- Samples: 10 | Simplified FP: 5
  - si0: dec=covered_change kinds=['off_focal'] S1=True exp=off_focal
    - B: dec=covered_change kinds=['off_focal']
    - oldC: dec=covered_change kinds=['off_focal']
    - focused: dec=covered_change kinds=['off_focal']
  - si1: dec=None kinds=[] S1=False exp=off_focal
    - B: dec=no_covered_change kinds=[]
    - oldC: dec=no_covered_change kinds=[]
    - focused: dec=covered_change kinds=['off_focal']
  - si2: dec=no_covered_change kinds=[] S1=False exp=off_focal
    - B: dec=None kinds=[]
    - oldC: dec=covered_change kinds=['off_focal']
    - focused: dec=None kinds=[]
  - si3: dec=covered_change kinds=['off_focal'] S1=True exp=off_focal
    - B: dec=covered_change kinds=['off_focal']
    - oldC: dec=covered_change kinds=['off_focal']
    - focused: dec=covered_change kinds=['off_focal']
  - si4: dec=covered_change kinds=['off_focal'] S1=True exp=off_focal
    - B: dec=covered_change kinds=['off_focal']
    - oldC: dec=no_covered_change kinds=[]
    - focused: dec=covered_change kinds=['off_focal']
  - si5: dec=no_covered_change kinds=[] S1=False exp=off_focal
    - B: dec=None kinds=[]
    - oldC: dec=None kinds=[]
    - focused: dec=no_covered_change kinds=[]
  - si6: dec=covered_change kinds=['off_focal'] S1=True exp=off_focal
    - B: dec=covered_change kinds=['off_focal']
    - oldC: dec=None kinds=[]
    - focused: dec=no_covered_change kinds=[]
  - si7: dec=no_covered_change kinds=[] S1=False exp=off_focal
    - B: dec=None kinds=[]
    - oldC: dec=no_covered_change kinds=[]
    - focused: dec=covered_change kinds=['off_focal']
  - si8: dec=no_covered_change kinds=[] S1=False exp=off_focal
    - B: dec=None kinds=[]
    - oldC: dec=no_covered_change kinds=[]
    - focused: dec=covered_change kinds=['off_focal']
  - si9: dec=covered_change kinds=['off_focal'] S1=True exp=off_focal
    - B: dec=covered_change kinds=['off_focal']
    - oldC: dec=covered_change kinds=['off_focal']
    - focused: dec=no_covered_change kinds=[]
