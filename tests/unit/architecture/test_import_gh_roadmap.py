"""Unit tests for architecture/model/import_gh_roadmap.py (GH #95)."""

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

FIXTURES = Path(__file__).parent / "fixtures"
REPO = "o/r"


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text()


def issue_page(nodes: list[dict[str, Any]], next_cursor: str | None = None) -> str:
    page = {"pageInfo": {"hasNextPage": next_cursor is not None, "endCursor": next_cursor}, "nodes": nodes}
    return json.dumps({"data": {"repository": {"issues": page}}})


def make_stub(
    milestones: str | None = None,
    releases: str | None = None,
    issues: list[str] | None = None,
    calls: list[list[str]] | None = None,
) -> Callable[[list[str]], str]:
    """A `run_gh` stand-in answering from recorded payloads; issue pages are served in order."""
    pages = iter(issues if issues is not None else [fixture_text("gh_issues.json")])

    def stub(args: list[str]) -> str:
        if calls is not None:
            calls.append(args)
        joined = " ".join(args)
        if "graphql" in args:
            return next(pages)
        if "milestones" in joined:
            return milestones if milestones is not None else fixture_text("gh_milestones.json")
        if "releases" in joined:
            return releases if releases is not None else fixture_text("gh_releases.json")
        raise AssertionError(f"unexpected gh call: {args}")

    return stub


# --- slugs and ids -----------------------------------------------------------------


def test_slug_is_lower_cased_and_hyphenated(importer: ModuleType) -> None:
    assert importer.slugify("Policy to OSCAL: MVP!") == "policy-to-oscal-mvp"
    assert importer.slugify("v0.1.0") == "v0-1-0"


def test_work_package_slug_cuts_at_a_word_boundary(importer: ModuleType) -> None:
    slug = importer.work_package_slug("alpha beta gamma delta epsilon zeta eta theta iota kappa")
    assert slug == "alpha-beta-gamma-delta-epsilon-zeta-eta"
    assert len(slug) <= 40
    assert importer.work_package_slug("short title") == "short-title"


def test_work_package_slug_hard_cuts_a_single_long_word(importer: ModuleType) -> None:
    assert importer.work_package_slug("x" * 60) == "x" * 40


def test_id_builders(importer: ModuleType) -> None:
    assert importer.plateau_id("policy-to-oscal-mvp", 1) == "plat-policy-to-oscal-mvp-1"
    assert importer.release_id("v0.1.0") == "del-release-v0-1-0"
    assert importer.unreleased_id("policy-to-oscal-mvp", 1) == "del-policy-to-oscal-mvp-1-unreleased"
    assert importer.work_package_id("Markdown catalogue converter", 44) == "wp-markdown-catalogue-converter-gh-44"


# --- run_gh ------------------------------------------------------------------------


def test_run_gh_uses_an_argv_list_without_a_shell(importer: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.update(argv=argv, kwargs=kwargs)
        return subprocess.CompletedProcess(argv, 0, stdout="[]", stderr="")

    monkeypatch.setattr(importer.subprocess, "run", fake_run)
    assert importer.run_gh(["api", "x; rm -rf /"]) == "[]"
    assert seen["argv"] == ["gh", "api", "x; rm -rf /"]
    assert not seen["kwargs"].get("shell")


def test_run_gh_failure_names_the_call_and_the_fix(importer: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(argv: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="HTTP 401")

    monkeypatch.setattr(importer.subprocess, "run", fake_run)
    with pytest.raises(importer.GhError) as err:
        importer.run_gh(["api", "repos/o/r/milestones"])
    assert "gh api repos/o/r/milestones" in str(err.value)
    assert "gh auth login" in str(err.value)


def test_run_gh_missing_binary_is_a_gh_error(importer: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_: Any, **__: Any) -> None:
        raise FileNotFoundError("gh")

    monkeypatch.setattr(importer.subprocess, "run", fake_run)
    with pytest.raises(importer.GhError, match="install"):
        importer.run_gh(["api", "x"])


def test_main_returns_2_when_gh_fails(importer: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    def failing(args: list[str]) -> str:
        raise importer.GhError("gh api repos/o/r/milestones failed: boom. Run `gh auth login`.")

    assert importer.main(["--repo", REPO], run_gh=failing, layer_dir=tmp_path) == 2
    assert "gh auth login" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("bad", ["not json", '{"unexpected": 1}', "[1, 2]"])
def test_unparseable_milestones_are_a_gh_error(importer: ModuleType, bad: str) -> None:
    with pytest.raises(importer.GhError, match="milestones"):
        importer.fetch_milestones(make_stub(milestones=bad), REPO)


# --- fetch (happy path) ------------------------------------------------------------


def test_fetch_milestones_and_releases(importer: ModuleType) -> None:
    calls: list[list[str]] = []
    stub = make_stub(calls=calls)
    milestones = importer.fetch_milestones(stub, REPO)
    assert calls[0][-1] == "repos/o/r/milestones?state=all&per_page=100"
    assert [(m.number, m.title, m.due_on) for m in milestones] == [
        (1, "policy-to-oscal-mvp", None),
        (2, "multi-user-collaboration", "2026-12-31T00:00:00Z"),
    ]
    releases = importer.fetch_releases(stub, REPO)
    assert [r.tag for r in releases] == ["v0.2.0", "v0.1.0"]  # draft and pre-release dropped


def test_slurped_pages_are_flattened(importer: ModuleType) -> None:
    milestones = json.loads(fixture_text("gh_milestones.json"))
    pages = json.dumps([milestones[:1], milestones[1:]])
    assert [m.number for m in importer.fetch_milestones(make_stub(milestones=pages), REPO)] == [1, 2]


def test_fetch_issues_follows_cursors(importer: ModuleType) -> None:
    node = json.loads(fixture_text("gh_issues.json"))["data"]["repository"]["issues"]["nodes"]
    calls: list[list[str]] = []
    stub = make_stub(issues=[issue_page(node[:2], "c1"), issue_page(node[2:])], calls=calls)
    issues = importer.fetch_issues(stub, REPO)
    assert [i.number for i in issues] == [44, 61, 7, 99]
    assert any("after=c1" in a for a in calls[1])
    closed = next(i for i in issues if i.number == 7)
    assert (closed.state, closed.milestone) == ("closed", 1)
    assert next(i for i in issues if i.number == 99).parent == 44


def node(number: int) -> dict[str, Any]:
    return {
        "number": number,
        "title": f"t{number}",
        "state": "OPEN",
        "closedAt": None,
        "url": f"u{number}",
        "milestone": None,
        "parent": None,
        "blockedBy": {"nodes": []},
    }


def pages_of(count: int, last_has_next: bool) -> list[str]:
    pages = []
    for p in range(count // 100):
        more = p < count // 100 - 1 or last_has_next
        pages.append(issue_page([node(p * 100 + i) for i in range(100)], f"c{p}" if more else None))
    return pages


def test_exactly_the_issue_cap_succeeds(importer: ModuleType) -> None:
    assert len(importer.fetch_issues(make_stub(issues=pages_of(1000, False)), REPO)) == 1000


def test_more_issues_than_the_cap_fails(importer: ModuleType) -> None:
    with pytest.raises(importer.GhError, match="1000"):
        importer.fetch_issues(make_stub(issues=pages_of(1000, True)), REPO)


# --- render and write --------------------------------------------------------------


def sample_layer(reverse: bool = False) -> dict[str, list[dict[str, Any]]]:
    elements: list[dict[str, Any]] = [
        {"type": "Plateau", "id": "plat-b-2", "name": "b"},
        {"type": "Plateau", "id": "plat-a-1", "name": "a", "props": {"z": "1", "a": "2"}},
        {"type": "WorkPackage", "id": "wp-x-gh-3", "name": "GH-3 x"},
    ]
    rels = [{"type": "Realization", "source": "wp-x-gh-3", "target": "plat-a-1"}]
    views = [{"id": "view-plat-a-1", "name": "a", "members": ["plat-a-1"]}]
    if reverse:
        elements.reverse()
    return {"elements.yaml": elements, "relationships.yaml": rels, "views.yaml": views}


def test_render_is_sorted_and_byte_stable(importer: ModuleType) -> None:
    first = importer.render_layer(sample_layer())
    assert first == importer.render_layer(sample_layer())
    assert first == importer.render_layer(sample_layer(reverse=True))
    ids = [e["id"] for e in yaml.safe_load(first["elements.yaml"])]
    assert ids == ["plat-a-1", "plat-b-2", "wp-x-gh-3"]
    assert set(first) == {"elements.yaml", "relationships.yaml", "views.yaml"}
    assert b"20" not in first["elements.yaml"].split(b"\n")[0]  # header carries no timestamp


def test_write_layer_replaces_via_temp_files(importer: ModuleType, tmp_path: Path) -> None:
    layer = tmp_path / "gh-roadmap"
    files = importer.render_layer(sample_layer())
    importer.write_layer(files, layer)
    assert {p.name for p in layer.iterdir()} == set(files)
    assert (layer / "elements.yaml").read_bytes() == files["elements.yaml"]


@pytest.mark.parametrize("fail_on", [1, 2])
def test_failed_replace_leaves_no_temp_and_no_partial_layer(
    importer: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail_on: int
) -> None:
    layer = tmp_path / "gh-roadmap"
    old = dict.fromkeys(importer.LAYER_FILES, b"- old\n")
    layer.mkdir()
    for name, data in old.items():
        (layer / name).write_bytes(data)
    real_replace, count = importer.os.replace, {"n": 0}

    def flaky(src: Any, dst: Any) -> None:
        count["n"] += 1
        if count["n"] == fail_on:
            raise OSError("disk full")
        real_replace(src, dst)

    monkeypatch.setattr(importer.os, "replace", flaky)
    with pytest.raises(OSError, match="disk full"):
        importer.write_layer(importer.render_layer(sample_layer()), layer)
    assert {p.name for p in layer.iterdir()} == set(old)
    assert all((layer / name).read_bytes() == data for name, data in old.items())


# --- US1: mapping (T010, T011) -----------------------------------------------------

MODEL_DIR = Path(__file__).resolve().parents[3] / "architecture" / "model"


class Kit:
    """Builders for importer inputs plus a `layer()` shortcut returning parsed elements and links."""

    def __init__(self, importer: ModuleType) -> None:
        self.m = importer

    def milestone(self, number: int = 1, title: str = "mvp", description: str = "", state: str = "open") -> Any:
        return self.m.Milestone(number, title, description, state, None, f"https://x/milestone/{number}")

    def release(self, tag: str, published: str, body: str = "plat-mvp-1") -> Any:
        return self.m.Release(tag, "", body, published, f"https://x/releases/{tag}")

    def issue(self, number: int, title: str = "work", milestone: int | None = 1, **kw: Any) -> Any:
        state = kw.pop("state", "open")
        return self.m.Issue(
            number, title, state, kw.pop("closed_at", None), f"https://x/issues/{number}", milestone,
            kw.pop("parent", None), tuple(kw.pop("blocked_by", ())),
        )  # fmt: skip

    def layer(
        self, milestones: list[Any], releases: list[Any], issues: list[Any], bfn: frozenset[str] = frozenset()
    ) -> Any:
        return self.m.build_layer(milestones, releases, issues, bfn)


@pytest.fixture
def kit(importer: ModuleType) -> Kit:
    return Kit(importer)


def by_id(layer: Any) -> dict[str, dict[str, Any]]:
    return {e["id"]: e for e in layer["elements.yaml"]}


def links(layer: Any, type_: str | None = None) -> set[tuple[str, str, str]]:
    return {(r["type"], r["source"], r["target"]) for r in layer["relationships.yaml"] if type_ in (None, r["type"])}


def test_main_writes_the_fixture_layer(
    importer: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert importer.main(["--repo", REPO], run_gh=make_stub(), layer_dir=tmp_path) == 0
    assert capsys.readouterr().out.strip() == (
        "wrote gh-roadmap: 2 milestones, 2 releases, 1 unreleased deliverable, 3 work packages, 0 triggering"
    )
    elements = yaml.safe_load((tmp_path / "elements.yaml").read_text())
    kinds = [e["type"] for e in elements]
    assert (kinds.count("Plateau"), kinds.count("WorkPackage"), kinds.count("Deliverable")) == (2, 3, 3)
    assert {p.name for p in tmp_path.iterdir()} == {"elements.yaml", "relationships.yaml", "views.yaml"}
    assert len(yaml.safe_load((tmp_path / "views.yaml").read_text())) == 2


def test_closed_work_package_realizes_a_deliverable_never_a_plateau(kit: Kit) -> None:
    layer = kit.layer(
        [kit.milestone()], [], [kit.issue(1, state="closed", closed_at="2026-01-01T00:00:00Z"), kit.issue(2)]
    )
    for wp in ("wp-work-gh-1", "wp-work-gh-2"):
        targets = [t for _, s, t in links(layer, "Realization") if s == wp]
        assert targets == ["del-mvp-1-unreleased"]
    assert by_id(layer)["wp-work-gh-1"]["props"]["gh-state"] == "closed"


def test_issue_without_its_own_milestone_creates_nothing(kit: Kit) -> None:
    layer = kit.layer(
        [kit.milestone()], [], [kit.issue(1), kit.issue(2, milestone=None, parent=1), kit.issue(3, parent=2)]
    )
    assert sorted(i for i in by_id(layer) if i.startswith("wp-")) == ["wp-work-gh-1", "wp-work-gh-3"]


def test_issue_closed_between_two_releases_realizes_the_later_one_only(kit: Kit) -> None:
    releases = [kit.release("v1", "2026-01-01T00:00:00Z"), kit.release("v2", "2026-03-01T00:00:00Z")]
    issue = kit.issue(1, state="closed", closed_at="2026-02-01T00:00:00Z")
    layer = kit.layer([kit.milestone()], releases, [issue])
    assert links(layer, "Realization") >= {("Realization", "wp-work-gh-1", "del-release-v2")}
    assert not any(s == "wp-work-gh-1" and t != "del-release-v2" for _, s, t in links(layer, "Realization"))
    assert "del-mvp-1-unreleased" not in by_id(layer)


def test_issue_closed_after_the_latest_release_stays_unreleased(kit: Kit) -> None:
    layer = kit.layer(
        [kit.milestone()],
        [kit.release("v1", "2026-01-01T00:00:00Z")],
        [kit.issue(1, state="closed", closed_at="2026-02-01T00:00:00Z")],
    )
    assert ("Realization", "wp-work-gh-1", "del-mvp-1-unreleased") in links(layer)


def test_release_naming_no_imported_plateau_attaches_nothing(kit: Kit) -> None:
    layer = kit.layer(
        [kit.milestone()],
        [kit.release("v1", "2026-03-01T00:00:00Z", body="plat-ghost-9 and plat-mvp-1-extra")],
        [kit.issue(1, state="closed", closed_at="2026-02-01T00:00:00Z")],
    )
    assert "del-release-v1" in by_id(layer)
    assert not [r for r in links(layer, "Realization") if r[1] == "del-release-v1"]
    assert ("Realization", "wp-work-gh-1", "del-mvp-1-unreleased") in links(layer)


def test_drafts_and_prereleases_never_make_a_deliverable(importer: ModuleType, tmp_path: Path) -> None:
    importer.main(["--repo", REPO], run_gh=make_stub(), layer_dir=tmp_path)
    ids = {e["id"] for e in yaml.safe_load((tmp_path / "elements.yaml").read_text())}
    assert {"del-release-v0-3-0", "del-release-v0-3-0-rc1"}.isdisjoint(ids)
    assert {"del-release-v0-1-0", "del-release-v0-2-0"} <= ids


def test_unreleased_deliverable_only_for_a_milestone_with_work_packages(kit: Kit) -> None:
    layer = kit.layer([kit.milestone(), kit.milestone(2, "empty")], [], [kit.issue(1)])
    ids = by_id(layer)
    assert "del-mvp-1-unreleased" in ids
    assert "del-empty-2-unreleased" not in ids
    assert ("Realization", "del-mvp-1-unreleased", "plat-mvp-1") in links(layer)


def test_bfn_token_is_honoured_only_on_an_exact_match(kit: Kit) -> None:
    description = "Realizes bfn-real, not bfn-fake or bfn-real-extra."
    layer = kit.layer([kit.milestone(description=description)], [], [], frozenset({"bfn-real"}))
    assert links(layer, "Realization") == {("Realization", "plat-mvp-1", "bfn-real")}
    layer = kit.layer([kit.milestone(description=description)], [], [], frozenset())
    assert links(layer) == set()
    assert by_id(layer)["plat-mvp-1"]["desc"] == description


HOSTILE = [
    "quote \" and ' and : colon",
    "---\nnewline: [broken",
    "!!python/object/apply:os.system ['id']",
    "{a: b}, - c # d",
    "unicode ✓ and tab\t",
]


@pytest.mark.parametrize("text", HOSTILE)
def test_hostile_text_is_escaped_and_round_trips(importer: ModuleType, kit: Kit, text: str) -> None:
    layer = kit.layer([kit.milestone(title=text, description=text)], [], [kit.issue(1, title=text)])
    parsed = {name: yaml.safe_load(data) for name, data in importer.render_layer(layer).items()}
    elements = {e["id"]: e for e in parsed["elements.yaml"]}
    plateau = next(e for e in elements.values() if e["type"] == "Plateau")
    assert (plateau["name"], plateau["desc"]) == (text, text)
    assert next(e for e in elements.values() if e["type"] == "WorkPackage")["name"] == f"GH-1 {text}"
    assert all(i.startswith(("plat-", "del-", "wp-")) for i in elements)


def test_no_emitted_id_collides_with_the_first_party_model(importer: ModuleType, tmp_path: Path) -> None:
    importer.main(["--repo", REPO], run_gh=make_stub(), layer_dir=tmp_path)
    emitted = {e["id"] for e in yaml.safe_load((tmp_path / "elements.yaml").read_text())}
    first_party = {e["id"] for e in yaml.safe_load((MODEL_DIR / "elements.yaml").read_text())}
    assert emitted.isdisjoint(first_party)


def test_issue_with_a_missing_milestone_is_dropped(kit: Kit) -> None:
    layer = kit.layer([kit.milestone()], [], [kit.issue(1), kit.issue(2, milestone=9)])
    assert "wp-work-gh-2" not in by_id(layer)


def test_ids_are_unique_typed_and_resolvable(kit: Kit) -> None:
    layer = kit.layer(
        [kit.milestone(), kit.milestone(2, "later")],
        [kit.release("v1", "2026-03-01T00:00:00Z")],
        [kit.issue(1), kit.issue(2, milestone=2)],
    )
    ids = [e["id"] for e in layer["elements.yaml"]]
    assert len(ids) == len(set(ids))
    assert not any(i.startswith("gh-") for i in ids)
    assert all(s in ids and t in ids for _, s, t in links(layer))
    members = {m for v in layer["views.yaml"] for m in v["members"]}
    assert members <= set(ids)


def link(type_: str, source: str, target: str) -> dict[str, str]:
    return {"type": type_, "source": source, "target": target}


def test_derivation_filter_drops_only_implied_links(importer: ModuleType) -> None:
    chain = [link("Triggering", "a", "b"), link("Triggering", "b", "c")]
    assert importer.drop_derived([*chain, link("Triggering", "a", "c")]) == chain
    # A different type is not implied by the chain, so it stays.
    assert link("Aggregation", "a", "c") in importer.drop_derived([*chain, link("Aggregation", "a", "c")])
    # A cycle never deletes both directions.
    cycle = [link("Triggering", "a", "b"), link("Triggering", "b", "a")]
    assert importer.drop_derived(cycle) == sorted(cycle, key=lambda r: r["source"])


def test_fixture_layer_builds_and_validates(
    importer: ModuleType, build_mod: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    layer_dir = tmp_path / "gh-roadmap"
    assert importer.main(["--repo", REPO], run_gh=make_stub(), layer_dir=layer_dir) == 0
    monkeypatch.setattr(build_mod, "MODEL_LAYERS", [*build_mod.VENDORED_MODELS, layer_dir])
    out = MODEL_DIR.parents[1] / "build" / "test-gh-roadmap-model.xml"  # build.py prints OUT relative to the repo
    out.parent.mkdir(exist_ok=True)
    monkeypatch.setattr(build_mod, "OUT", out)
    try:
        assert build_mod.main() == 0
    finally:
        out.unlink(missing_ok=True)


# --- US3: refresh safely (T018, T019) ----------------------------------------------


def run_import(importer: ModuleType, layer_dir: Path, stub: Any = None, *extra: str) -> int:
    return int(importer.main(["--repo", REPO, *extra], run_gh=stub or make_stub(), layer_dir=layer_dir))


def snapshot(layer_dir: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted(layer_dir.iterdir())}


def issues_with(**changes: Any) -> list[str]:
    """The fixture issue page with fields of issue 44 overridden."""
    page = json.loads(fixture_text("gh_issues.json"))
    node = next(n for n in page["data"]["repository"]["issues"]["nodes"] if n["number"] == 44)
    node.update(changes)
    return [json.dumps(page)]


def test_second_run_with_no_change_is_byte_identical(
    importer: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run_import(importer, tmp_path) == 0
    first = snapshot(tmp_path)
    capsys.readouterr()
    assert run_import(importer, tmp_path) == 0
    assert snapshot(tmp_path) == first
    assert capsys.readouterr().out.strip() == "gh-roadmap: unchanged"


def test_closing_one_issue_changes_only_that_issue(importer: ModuleType, tmp_path: Path) -> None:
    run_import(importer, tmp_path)
    before = {name: yaml.safe_load(data) for name, data in snapshot(tmp_path).items()}
    closed = issues_with(state="CLOSED", closedAt="2026-10-01T00:00:00Z")
    run_import(importer, tmp_path, make_stub(issues=closed))
    after = {name: yaml.safe_load(data) for name, data in snapshot(tmp_path).items()}
    assert after["relationships.yaml"] == before["relationships.yaml"]  # no release after the close
    assert after["views.yaml"] == before["views.yaml"]
    changed = [
        (a["id"], a["props"]["gh-state"])
        for a, b in zip(after["elements.yaml"], before["elements.yaml"], strict=True)
        if a != b
    ]
    assert changed == [("wp-markdown-catalogue-converter-gh-44", "closed")]


def test_close_moves_the_link_only_when_a_release_follows(importer: ModuleType, tmp_path: Path) -> None:
    run_import(importer, tmp_path)
    before = yaml.safe_load((tmp_path / "relationships.yaml").read_text())
    closed = issues_with(state="CLOSED", closedAt="2026-09-15T00:00:00Z")  # between v0.1.0 and v0.2.0
    run_import(importer, tmp_path, make_stub(issues=closed))
    after = yaml.safe_load((tmp_path / "relationships.yaml").read_text())
    gone = [r for r in before if r not in after]
    added = [r for r in after if r not in before]
    assert gone == [link("Realization", "wp-markdown-catalogue-converter-gh-44", "del-policy-to-oscal-mvp-1-unreleased")]
    assert added == [link("Realization", "wp-markdown-catalogue-converter-gh-44", "del-release-v0-2-0")]


def failing_on(importer: ModuleType, needle: str, base: Any) -> Any:
    def stub(args: list[str]) -> str:
        if needle in " ".join(args):
            raise importer.GhError(f"`gh {needle}` failed")
        return str(base(args))

    return stub


@pytest.mark.parametrize("needle", ["milestones", "releases", "graphql"])
def test_a_failing_fetch_leaves_the_layer_untouched(importer: ModuleType, tmp_path: Path, needle: str) -> None:
    run_import(importer, tmp_path)
    before = snapshot(tmp_path)
    assert run_import(importer, tmp_path, failing_on(importer, needle, make_stub(issues=issues_with(title="new")))) == 2
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "stub_args",
    [
        {"milestones": "{not json"},
        {"releases": '{"unexpected": 1}'},
        {"issues": ["{}"]},
        {"issues": pages_of(1000, True)},
    ],
)
def test_unparseable_or_incomplete_data_leaves_the_layer_untouched(
    importer: ModuleType, tmp_path: Path, stub_args: dict[str, Any]
) -> None:
    run_import(importer, tmp_path)
    before = snapshot(tmp_path)
    assert run_import(importer, tmp_path, make_stub(**stub_args)) == 2
    assert snapshot(tmp_path) == before


def test_reopened_issue_returns_to_the_unreleased_deliverable(kit: Kit) -> None:
    release = kit.release("v1", "2026-03-01T00:00:00Z")
    closed = kit.layer([kit.milestone()], [release], [kit.issue(1, state="closed", closed_at="2026-02-01T00:00:00Z")])
    reopened = kit.layer([kit.milestone()], [release], [kit.issue(1)])
    assert ("Realization", "wp-work-gh-1", "del-release-v1") in links(closed)
    assert ("Realization", "wp-work-gh-1", "del-mvp-1-unreleased") in links(reopened)
    assert by_id(reopened)["wp-work-gh-1"]["props"]["gh-state"] == "open"


def test_moved_milestone_retargets_only_that_realization(kit: Kit) -> None:
    milestones = [kit.milestone(), kit.milestone(2, "later")]
    before = kit.layer(milestones, [], [kit.issue(1), kit.issue(2)])
    after = kit.layer(milestones, [], [kit.issue(1, milestone=2), kit.issue(2)])
    assert links(before) - links(after) == {("Realization", "wp-work-gh-1", "del-mvp-1-unreleased")}
    assert links(after) - links(before) >= {("Realization", "wp-work-gh-1", "del-later-2-unreleased")}


def test_removed_milestone_removes_the_element_and_its_links(kit: Kit) -> None:
    layer = kit.layer([kit.milestone()], [], [kit.issue(1, milestone=None)])
    assert all(i.startswith("plat-") for i in by_id(layer))
    assert links(layer) == set()


def test_retitled_issue_gets_a_new_id_and_the_old_one_is_gone(kit: Kit) -> None:
    old = by_id(kit.layer([kit.milestone()], [], [kit.issue(1, title="Old name")]))
    new = by_id(kit.layer([kit.milestone()], [], [kit.issue(1, title="New name")]))
    assert "wp-old-name-gh-1" in old
    assert "wp-new-name-gh-1" in new
    assert "wp-old-name-gh-1" not in new


def test_check_reports_stale_and_writes_nothing(
    importer: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run_import(importer, tmp_path, None, "--check") == 1  # no layer yet
    assert list(tmp_path.iterdir()) == []
    run_import(importer, tmp_path)
    before = snapshot(tmp_path)
    capsys.readouterr()
    assert run_import(importer, tmp_path, None, "--check") == 0
    assert "current" in capsys.readouterr().out
    assert run_import(importer, tmp_path, make_stub(issues=issues_with(title="renamed")), "--check") == 1
    assert snapshot(tmp_path) == before


# --- US2: dependencies and hierarchy (T022, T023) ----------------------------------


def dependency_layer(importer: ModuleType, tmp_path: Path) -> Any:
    stub = make_stub(issues=[fixture_text("gh_issues_dependencies.json")])
    assert importer.main(["--repo", REPO], run_gh=stub, layer_dir=tmp_path) == 0
    return {"relationships.yaml": yaml.safe_load((tmp_path / "relationships.yaml").read_text())}


def test_blocked_by_becomes_triggering_between_work_packages(importer: ModuleType, tmp_path: Path) -> None:
    triggers = links(dependency_layer(importer, tmp_path), "Triggering")
    assert ("Triggering", "wp-design-the-schema-gh-10", "wp-build-the-importer-gh-11") in triggers


def test_cross_milestone_block_gives_one_plateau_triggering(importer: ModuleType, tmp_path: Path) -> None:
    triggers = links(dependency_layer(importer, tmp_path), "Triggering")
    plateau = [t for t in triggers if t[1].startswith("plat-")]
    assert plateau == [("Triggering", "plat-policy-to-oscal-mvp-1", "plat-multi-user-collaboration-2")]
    assert all(s != t for _, s, t in triggers)


def test_parent_and_child_both_imported_are_aggregated(kit: Kit) -> None:
    issues = [kit.issue(13, "Epic"), kit.issue(14, "Child", parent=13), kit.issue(18, "Orphan", parent=91)]
    aggregations = links(kit.layer([kit.milestone()], [], issues), "Aggregation")
    assert aggregations == {("Aggregation", "wp-epic-gh-13", "wp-child-gh-14")}


def test_links_with_an_unimported_end_are_dropped(kit: Kit) -> None:
    issues = [kit.issue(1, blocked_by=[90]), kit.issue(2, milestone=None), kit.issue(3, blocked_by=[2])]
    layer = kit.layer([kit.milestone()], [], issues)
    assert links(layer, "Triggering") == set()


def test_cross_milestone_triggering_is_deduplicated_without_self_loops(kit: Kit) -> None:
    milestones = [kit.milestone(), kit.milestone(2, "later")]
    issues = [kit.issue(1), kit.issue(2), kit.issue(3, milestone=2, blocked_by=[1, 2]), kit.issue(4, blocked_by=[1])]
    plateau = {t for t in links(kit.layer(milestones, [], issues), "Triggering") if t[1].startswith("plat-")}
    assert plateau == {("Triggering", "plat-mvp-1", "plat-later-2")}


def test_dependency_cycles_are_emitted_as_written(kit: Kit) -> None:
    layer = kit.layer([kit.milestone()], [], [kit.issue(1, blocked_by=[2]), kit.issue(2, blocked_by=[1])])
    assert links(layer, "Triggering") == {
        ("Triggering", "wp-work-gh-1", "wp-work-gh-2"),
        ("Triggering", "wp-work-gh-2", "wp-work-gh-1"),
    }


def test_transitive_triggering_is_not_repeated(kit: Kit) -> None:
    issues = [kit.issue(1), kit.issue(2, blocked_by=[1]), kit.issue(3, blocked_by=[1, 2])]
    triggers = links(kit.layer([kit.milestone()], [], issues), "Triggering")
    assert ("Triggering", "wp-work-gh-1", "wp-work-gh-3") not in triggers
    assert len(triggers) == 2


def test_dependency_layer_still_validates(
    importer: ModuleType, build_mod: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    layer_dir = tmp_path / "gh-roadmap"
    stub = make_stub(issues=[fixture_text("gh_issues_dependencies.json")])
    assert importer.main(["--repo", REPO], run_gh=stub, layer_dir=layer_dir) == 0
    monkeypatch.setattr(build_mod, "MODEL_LAYERS", [*build_mod.VENDORED_MODELS, layer_dir])
    out = MODEL_DIR.parents[1] / "build" / "test-gh-roadmap-model.xml"
    out.parent.mkdir(exist_ok=True)
    monkeypatch.setattr(build_mod, "OUT", out)
    try:
        assert build_mod.main() == 0
    finally:
        out.unlink(missing_ok=True)
