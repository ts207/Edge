# Operator command inventory

## Canonical CLI

```bash
python project/cli.py discover --help
python project/cli.py validate --help
python project/cli.py promote --help
python project/cli.py deploy --help
python project/cli.py ingest --help
python project/cli.py catalog --help
```

## Common wrappers

```bash
make discover
make validate
make promote
make export
make deploy-paper
make check-hygiene
```

## Important scripts

- `python -m project.scripts.run_certification_workflow`
- `python -m project.research.export_promoted_theses`
- `project/scripts/regenerate_artifacts.sh`
