"""Path constants for the Promptfoo spike and repo-root import bootstrap."""
import os
import sys

LIB_DIR = os.path.dirname(os.path.abspath(__file__))
SPIKE_DIR = os.path.dirname(LIB_DIR)
EXPERIMENTS_DIR = os.path.dirname(SPIKE_DIR)
REPO_ROOT = os.path.dirname(EXPERIMENTS_DIR)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

WORKSPACE_ROOT = os.environ.get(
    "AGK_PF_WORKSPACE_ROOT", "/tmp/kilo/agk-pf-workspaces")
GENERATED_DIR = os.path.join(SPIKE_DIR, "generated")
RESULTS_DIR = os.path.join(SPIKE_DIR, ".results")

RUNTIME_TREATMENT_PATHS = (".kilo/skills",)

CONFUSION_SETS = {
    "review-family": os.path.join(
        REPO_ROOT, "evaluations", "confusion-sets", "review-family.json"),
}
HOLDOUTS = {
    "review-discrim-1": os.path.join(
        REPO_ROOT, "evaluations", "holdout", "review-discrim-1.json"),
}
SKILL_EVALS = {
    skill: os.path.join(REPO_ROOT, "skills", skill, "evals", "evals.json")
    for skill in ("code-review", "security-review", "architecture-review")
}


def from_repo_root(*parts):
    return os.path.join(REPO_ROOT, *parts)
