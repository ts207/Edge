# Best practices and failure modes

This document is the operating rulebook for bounded work.

## Best practices

### Bound one mechanism slice at a time

A good proposal narrows at least four dimensions:

- trigger scope
- template scope
- time window
- context or regime scope

If all four are broad, the proposal is probably too loose.

### Prefer explicit baselines for confirmation work

If the run is meant to confirm or challenge an earlier result, encode that relationship and use compare-oriented review afterward.

### Separate discovery from export and packaging intent

Discovery asks whether a claim exists.
Export asks whether one specific run should become runtime input.
Packaging asks whether the claim deserves broader bootstrap/governance treatment as a reusable thesis object.

Do not move into packaging because a run “felt good.” Export first when the need is runtime input from one run; package only when the evidence and operating need justify broader thesis governance work.

### Read manifests before summaries

The manifest tells you whether the run is interpretable at all. Summary markdown does not.

### Use generated docs as inventory, not as truth by themselves

Generated docs are helpful because they compact state. They are dangerous when used without understanding the code and artifact contracts beneath them.

## Failure modes

### Broad search surface disguised as a bounded proposal

Symptoms:

- huge estimated hypothesis count
- many templates, events, horizons, and contexts combined at once
- results that are hard to explain mechanistically

Fix:

- reduce events
- reduce template count
- reduce horizon range
- make context filters explicit

### Mechanical success mistaken for research success

Symptoms:

- run exits cleanly
- artifacts exist
- no strong candidate or promotion survival exists

Fix:

- separate artifact correctness from signal quality
- use diagnose and regime-report before drawing conclusions

### Statistical survival mistaken for packaging readiness

Symptoms:

- a strong candidate row exists
- user assumes it should be live-consumable immediately

Fix:

- inspect promotion outputs
- export a thesis batch for the specific run if runtime input is the goal
- inspect bootstrap artifacts only when broader packaging work is intended
- inspect packaged thesis store state

### Promotion class mistaken for deployment permission

Symptoms:

- `seed_promoted` interpreted as live-ready
- `paper_promoted` interpreted as production-enabled

Fix:

- answer "can this trade?" from `deployment_state`
- treat `promotion_class` as supporting evidence metadata, not runtime permission

### Compatibility wrapper treated as canonical implementation

Symptoms:

- work starts from wrappers rather than service modules
- policy logic gets duplicated in thin shims

Fix:

- route understanding through `project.research.services` and `project.cli`
- use `docs/generated/system_map.md` to verify current canonical surfaces

### Generated-doc drift mistaken for code drift

Symptoms:

- docs/generated is stale
- user infers the implementation is stale

Fix:

- verify generation scripts and actual artifact roots
- regenerate before concluding the system is broken

## Writing and maintenance rules

- One concept should have one canonical owner doc.
- Subsystem READMEs should orient, not duplicate the whole system docs.
- Do not create planning docs when the relevant canonical doc can be updated directly.
- Do not make the docs depend on absent generated files without saying they are generated.

## Practical discipline checklist

Before running:

- Is the proposal narrow?
- Is the data window intentional?
- Are contexts explicit?
- Is the objective clear?

After planning:

- Is the estimated hypothesis count still bounded?
- Are required detectors/features/states understood?
- Does the run-all override bundle make sense?

After running:

- Did the manifest reconcile?
- Are phase2 artifacts present?
- Did promotion fail mechanically or statistically?
- Is the next action repair, confirm, kill, export, or package?
