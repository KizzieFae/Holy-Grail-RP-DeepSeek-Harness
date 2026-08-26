# NI forensic acceptance fixture (#45 scenario-grade lineage)

Static retained evidence for Package B deterministic tests. Derived from the
`ni-forensic-acceptance` acceptance scenario shape (Fact F omission, Fact G
propagation, tag forensic_scope, S4 join).

Session id: `hg-session-ni-acc-1`

Use with:

```sh
python tools/investigation/trace_ni_forensics.py hg-session-ni-acc-1 session \
  --evidence-root tools/investigation/fixtures/ni_forensic_acceptance/execution_evidence \
  --tags-root tools/investigation/fixtures/ni_forensic_acceptance/audit_tags
```
