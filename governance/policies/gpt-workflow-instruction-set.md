We need to update the governance instruction set to v1.5.0.

This is a continuation of Issue #145 governance alignment.

Do not create a new issue.

Do not modify #144 or #146.

Only extend #145 scope for instruction-set parity.

Task:

Create a v1.5.0 revision of the Holy Grail Workflow System instruction set.

Source:

Current v1.4.1 instruction set (attached in chat)

Required changes:

1. Add Workflow Weight Rule
   - light
   - standard
   - full
   - default standard
   - escalation to full via `workflow-weights.md`

2. Add Bootstrap Profile Rule
   - map workflow weight to authoritative bootstrap profile

3. Modify Consensus Loop Rule
   - weight-aware consensus depth

4. Modify Stateless Resume Rule
   Retrieval priority:

   execution snapshot
   execution anchor
   issue body
   latest comment
   project fields

5. Modify Prompt Provision Rule
   Prompts must declare workflow weight when issue work is involved.

6. Modify Activation Synchronization Rule
   Validate workflow weight at work start.

7. Modify Phase Transition Rule
   Require execution snapshot updates.

8. Modify Session Boundary Rule
   Require execution anchor state in progress summaries.

Constraints:

- preserve all Prompt Mode rules
- preserve Cross-AI Communication Rule
- preserve atomic prompt requirements
- preserve chat guidance requirements
- preserve GitHub mutation discipline
- preserve issue authority model

Return:

1. v1.5.0 full instruction set
2. change summary from v1.4.1
3. confirmation of alignment with active governance model

Do not implement further governance changes beyond the instruction-set update.