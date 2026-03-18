import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from project.events.detectors.registry import load_all_detectors, list_registered_event_types
from project.events.event_specs import _load_event_specs

load_all_detectors()
registered = set(list_registered_event_types())
specs = set(_load_event_specs().keys())

orphans = registered - specs
print("Orphan detectors:", orphans)

missing_specs = specs - registered
print("Specs without detectors:", missing_specs)
