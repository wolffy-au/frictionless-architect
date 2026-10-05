# pyright: reportCallIssue=false
"""Steps for gh_roadmap_import.feature: drive the importer's `main` with a stubbed `gh`."""

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import yaml
from behave import given, then, when  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests" / "unit" / "architecture" / "fixtures"


def load_importer():
    spec = importlib.util.spec_from_file_location("import_gh_roadmap", ROOT / "architecture/model/import_gh_roadmap.py")
    assert spec
    assert spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["import_gh_roadmap"] = module  # dataclasses resolve annotations through sys.modules
    spec.loader.exec_module(module)
    return module


def gh_stub(issues_text):
    def stub(args):
        joined = " ".join(args)
        if "graphql" in args:
            return issues_text
        name = "gh_milestones.json" if "milestones" in joined else "gh_releases.json"
        return (FIXTURES / name).read_text()

    return stub


def issues_json(closed_44=False):
    page = json.loads((FIXTURES / "gh_issues.json").read_text())
    if closed_44:
        node = next(n for n in page["data"]["repository"]["issues"]["nodes"] if n["number"] == 44)
        node.update(state="CLOSED", closedAt="2026-10-01T00:00:00Z")
    return json.dumps(page)


def snapshot(layer):
    return {p.name: p.read_bytes() for p in sorted(layer.iterdir())}


def run_import(context, stub):
    return context.importer.main(["--repo", "o/r"], run_gh=stub, layer_dir=context.layer)


@given("the roadmap has been imported")
def step_imported(context):
    context.importer = load_importer()
    context.layer = Path(tempfile.mkdtemp(prefix="gh-roadmap-")) / "gh-roadmap"
    assert run_import(context, gh_stub(issues_json())) == 0
    context.before = snapshot(context.layer)


@when("the roadmap is imported again with no change on GitHub")
def step_again(context):
    assert run_import(context, gh_stub(issues_json())) == 0


@when("issue 44 is closed on GitHub and the roadmap is imported again")
def step_close(context):
    assert run_import(context, gh_stub(issues_json(closed_44=True))) == 0


@when("GitHub is unreachable and the roadmap is imported again")
def step_unreachable(context):
    def unreachable(args):
        raise context.importer.GhError("`gh api repos/o/r/milestones` failed: could not resolve host")

    context.status = run_import(context, unreachable)


@then("no file of the roadmap layer differs")
def step_no_diff(context):
    assert snapshot(context.layer) == context.before


@then("only the state of issue 44 differs in the roadmap layer")
def step_only_44(context):
    after = snapshot(context.layer)
    assert after["relationships.yaml"] == context.before["relationships.yaml"]
    assert after["views.yaml"] == context.before["views.yaml"]
    old = yaml.safe_load(context.before["elements.yaml"])
    new = yaml.safe_load(after["elements.yaml"])
    changed = [(a["id"], a["props"]["gh-state"]) for a, b in zip(new, old, strict=True) if a != b]
    assert changed == [("wp-markdown-catalogue-converter-gh-44", "closed")], changed


@then("the import fails with exit status 2 naming the failing call")
def step_exit_two(context):
    assert context.status == 2
