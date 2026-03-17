from __future__ import annotations

import sys
import project.specs.manifest

# Directly map the alias module to the canonical implementation.
sys.modules["project.apps.pipeline.manifest"] = project.specs.manifest
