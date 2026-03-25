from __future__ import annotations

from project.research.helpers.writer import (
    apply_portfolio_cap,
    apply_retail_constraints,
    sort_blueprints_for_write,
    write_blueprint_artifacts,
)


class blueprint_writer:
    apply_retail_constraints = staticmethod(apply_retail_constraints)
    sort_blueprints_for_write = staticmethod(sort_blueprints_for_write)
    apply_portfolio_cap = staticmethod(apply_portfolio_cap)
    write_blueprint_artifacts = staticmethod(write_blueprint_artifacts)
    write_blueprints = staticmethod(write_blueprint_artifacts)
