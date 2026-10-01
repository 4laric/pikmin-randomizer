# Correcting a mistaken live lane registration

`Registry.correct_owner_identity(consent, apply=False)` verifies a narrowly scoped
clerical error. It does not recover, stop, adopt, or transfer execution. Unknown or
dead identities refuse; recovery remains a separate API requiring confirmed death.

The owner supplies a schema 1 JSON receipt as hashed evidence. Required fields:

- `correction_issue`: distinct positive assigned repair issue; `implementation_issue`: lane issue.
- `lane`: exact complete current registry row, including generation, revision,
  worker, task, process, source, claims, and evidence.
- `old_process`, `new_process`: exact host/PID/start identities, both positively alive.
- `actual_caller_chain`: owner observation containing the new identity. The API
  independently reads real ancestry; it accepts no caller-provided ancestry override.
- `owner_consent`: explicit authorization, `registration_error`: clerical-error
  explanation, and `registration_error_evidence`: separately hashed supporting file.
- `resources`, `queue`: empty lists, independently checked against the registry.
- `observed_worktrees`: one observation for each registered root/native checkout,
  with `repo`, absolute `path`, `head`, `dirty`, `dirty_sha256`,
  `tracked_diff_sha256`, and `files` containing relative `path`/`sha256` entries.

Schema 1 hashes raw `git diff --binary` stdout, requires an empty staged diff,
and records `git status --porcelain` with text newline normalization. All
untracked files must have raw byte hashes. Source status and bytes are checked
again during the registry transaction. Recorded source dirty state is preserved;
the separate observation can truthfully pin edits made since registration.

Both checkouts must be linked private worktrees under workspace output. The old
identity must be outside current ancestry and have no observed protected descendants.
An unavailable process snapshot refuses (currently Windows Toolhelp). Other lanes'
children of a common replacement desktop host do not prevent correction.

Any lane resource lease/request, active launch, pending session adoption, planning
claim, claimed action, terminal recovery, queued/open pool job or assignment for
the lane or its worker, active integration batch ownership or membership, current
candidate, or QA subscription
blocks correction. Delivery states and handoffs also block it. Historical completed
launches and archived agreements remain untouched.

Example preflight, followed only after independent review by the owner's apply:

```powershell
python -m workflow.owner_identity --root C:\path\workspace --consent C:\path\consent.json --sha256 EXACT_SHA256
python -m workflow.owner_identity --root C:\path\workspace --consent C:\path\consent.json --sha256 EXACT_SHA256 --apply
```

The default is read-only. Apply changes only lane process and revision, archives
exact consent and supporting evidence bytes, and appends an audit containing the
whole before/after row, observed sources, caller ancestry, issue, and timestamp.
Generation, task, worker, claims, sources, and evidence stay unchanged. Existing
coordination agreements become stale through their frozen process identities;
their archived contents remain intact. Replaying old consent refuses the changed
whole-lane identity. An aborted apply may leave only harmless hashed archives.

Issue 1163's first application requires independently reviewed code and a fresh
owner receipt; tests and preflight do not authorize editing the live registry.
