After that, the repo becomes simpler at the **input boundary**, but not yet simpler end-to-end.

The next phases should be:

## 1. Make run output the only thesis source

Right after the single-hypothesis front door works, remove the ambiguity at the back end.

Target path:

**proposal → run → promotion → thesis export → runtime**

So next:

* make `export_promoted_theses --run_id <run_id>` the only canonical thesis-batch creation path
* stop treating packaging/bootstrap outputs as equivalent thesis sources
* document that every runtime thesis batch must come from a specific run

This is the next highest-value step because it removes the “seed vs promoted vs packaged” confusion.

---

## 2. Make runtime require explicit thesis input

Right now the repo appears to tolerate implicit/default thesis resolution.

After the proposal cleanup, fix runtime loading:

Priority order:

1. `strategy_runtime.thesis_path`
2. `strategy_runtime.thesis_run_id`
3. otherwise fail clearly

Remove silent fallback behavior like:

* “latest thesis”
* default seed batch
* hidden bootstrap state

This forces one explicit lineage from run to runtime.

---

## 3. Separate promotion from live permission

This is the biggest conceptual cleanup after proposal simplification.

Make the state model explicit:

### Promotion status

Did research approve this result?

### Deployment state

What is runtime allowed to do with it?

Keep deployment states as the real permission layer:

* `monitor_only`
* `paper_only`
* `live_enabled`

Then document and enforce:

* promotion does **not** imply live eligibility
* export produces runtime-readable theses
* deployment state controls paper/live behavior

That removes most of the remaining confusion.

---

## 4. Remove seed from the operational path

Only after steps 1–3.

Then:

* stop pointing `data/live/theses/index.json` at seed
* remove seed from configs
* remove seed from runtime defaults
* demote seed scripts to deprecated/internal
* rename any necessary test fixtures so they are clearly fixtures, not canonical flow

Do not do this before explicit runtime thesis loading is in place.

---

## 5. Collapse docs around one operator story

Once the code path is real, rewrite the docs to one story only:

1. write one hypothesis
2. run bounded evaluation
3. inspect evidence
4. promote candidates
5. export thesis batch
6. point runtime at that batch
7. paper or live depending on deployment state

At that point, terms like:

* trigger space
* seed thesis
* latest thesis store
* packaging lane

should be either hidden or marked advanced/deprecated.

---

## 6. Simplify the runtime/thesis vocabulary

After the code and flow are clean, rename things.

Best likely rename set:

* **proposal** = test request
* **candidate** = evaluated result
* **thesis** = runtime strategy object
* **thesis batch** = runtime JSON file
* **deployment state** = actual permission

And remove operator-facing reliance on:

* `seed_promoted`
* `paper_promoted`
* `production_promoted`

Those can remain internal if needed, but users should mostly see deployment state.

---

## 7. Add promotion-to-runtime automation

Only after the lineage is explicit.

Then build the clean bridge:

* completed run
* promotion artifacts exist
* export thesis batch
* optionally register it as current runtime batch
* optionally mark selected theses `paper_only` or `live_enabled`

This turns the repo from “research system with runtime extras” into an actual operating pipeline.

---

## 8. Only then touch deeper engine simplification

After the boundaries are clean, you can decide whether phase-2 search and trigger-space abstractions still deserve to exist.

Possible later simplifications:

* reduce template proliferation
* reduce trigger type exposure
* limit default mode to `event`
* flatten proposal-to-experiment translation
* remove unused packaging surfaces

But this is later. Doing it earlier risks breaking behavior without reducing confusion much.

---

# Recommended order

Use this exact order:

### Phase A

Single-hypothesis proposal front door

### Phase B

Run-exported thesis batch as only canonical thesis source

### Phase C

Explicit runtime thesis input, no silent seed/latest fallback

### Phase D

Promotion vs deployment-state separation and enforcement

### Phase E

Remove seed from defaults and docs

### Phase F

Docs/vocabulary cleanup

### Phase G

Automation from promotion to runtime registration

That is the clean path.

---

# What changes for the user after Phase A only

After just the coding-agent task:

* writing proposals becomes simpler
* running research becomes clearer
* backend confusion still remains
* runtime and thesis-source confusion still exists

So Phase A fixes the **front door**, not the full system.

---

# The next strongest move

After implementing the single-hypothesis proposal loader, the best next task is:

**make exported run-derived thesis batches the only canonical runtime input, and remove default seed/latest thesis resolution.**
