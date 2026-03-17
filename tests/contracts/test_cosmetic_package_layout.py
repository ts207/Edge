from project.execution.backtest.engine import run_engine
from project.execution.runtime.dsl_interpreter import DslInterpreterV1
from project.infra.io import ensure_dir, read_parquet, write_parquet
from project.infra.orchestration.run_all import main as run_all_main
import project.strategy.dsl as strategy_dsl
import project.strategy.runtime as strategy_runtime
import project.strategy.templates as strategy_templates
from project.strategy.compiler.blueprint_compiler import main as compile_strategy_blueprints_main
from project.strategy.models.blueprint import Blueprint
from project.strategy.models.executable_strategy_spec import ExecutableStrategySpec


def test_cosmetic_strategy_namespace_is_importable():
    assert Blueprint is not None
    assert ExecutableStrategySpec is not None
    assert callable(compile_strategy_blueprints_main)
    assert strategy_dsl.Blueprint is not None
    assert callable(strategy_runtime.get_strategy)
    assert strategy_templates.StrategySpec is not None


def test_cosmetic_execution_namespace_is_importable():
    assert DslInterpreterV1 is not None
    assert callable(run_engine)


def test_cosmetic_infra_namespace_is_importable():
    assert callable(ensure_dir)
    assert callable(read_parquet)
    assert callable(write_parquet)
    assert callable(run_all_main)
