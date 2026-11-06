"""GeoLens: ранжирование перспективности территорий (PoC)."""

from .folds import fold_report, make_block_folds
from .grid import label_clusters, parse_band_groups, stack_to_table, table_qa
from .metrics import (
    deposit_ranks_in_test_fold,
    random_budget,
    summarize_folds,
    tie_aware_topk,
)
from .models import LogisticModel, WoEModel
from .protocol import run_protocol
from .stability import leave_one_deposit_out, stability_summary
from .validation import run_spatial_cv, run_spatial_oof, save_outputs, split_fold
from .woe import (
    FOLD,
    TARGET,
    coverage_audit,
    explain_cell,
    fit_woe,
    load_model,
    save_model,
    score_woe,
    woe_contributions,
)

__all__ = [
    "FOLD", "TARGET", "LogisticModel", "WoEModel",
    "coverage_audit", "deposit_ranks_in_test_fold", "explain_cell", "fit_woe", "fold_report",
    "label_clusters", "leave_one_deposit_out", "load_model", "make_block_folds",
    "parse_band_groups", "random_budget", "run_protocol", "run_spatial_cv", "run_spatial_oof",
    "save_model", "save_outputs", "score_woe", "split_fold", "stability_summary",
    "stack_to_table", "summarize_folds", "table_qa", "tie_aware_topk", "woe_contributions",
]
