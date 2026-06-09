import pytest

from pole_position.cli import console


@pytest.fixture(autouse=True)
def _clear_color_env(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)


def _force_color(monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")


def _no_color(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")


def test_plain_output_when_color_disabled(monkeypatch, capsys):
    _no_color(monkeypatch)

    console.success("Added module: garage")
    console.error("boom")
    console.warn("careful")
    console.heading("Created")
    console.item("src/app/router.py")
    console.step("Run polepos check")
    console.field("Template", "standard")

    out = capsys.readouterr().out
    assert "\033" not in out
    assert out == (
        "Added module: garage\n"
        "boom\n"
        "careful\n"
        "Created\n"
        "  src/app/router.py\n"
        "  Run polepos check\n"
        "Template: standard\n"
    )


def test_color_and_glyphs_when_enabled(monkeypatch, capsys):
    _force_color(monkeypatch)

    console.success("done")
    console.error("nope")
    console.warn("hmm")
    console.step("next")

    out = capsys.readouterr().out
    assert f"{console.GREEN}✓ done{console.RESET}" in out
    assert f"{console.RED}✗ nope{console.RESET}" in out
    assert f"{console.YELLOW}! hmm{console.RESET}" in out
    assert f"{console.CYAN}  → next{console.RESET}" in out


def test_no_color_takes_precedence_over_force_color(monkeypatch, capsys):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("NO_COLOR", "")  # presence (even empty) disables color

    console.success("done")

    out = capsys.readouterr().out
    assert out == "done\n"


def test_style_without_codes_is_identity(monkeypatch):
    _force_color(monkeypatch)
    assert console.style("plain") == "plain"


def test_heading_and_item_are_styled_when_enabled(monkeypatch, capsys):
    _force_color(monkeypatch)

    console.heading("Next steps")
    console.item("src/app/db/models.py")

    out = capsys.readouterr().out
    assert f"{console.BOLD}Next steps{console.RESET}" in out
    assert f"{console.DIM}  src/app/db/models.py{console.RESET}" in out


def test_color_follows_isatty_without_env(monkeypatch, capsys):
    class _TTY:
        def isatty(self):
            return True

        def write(self, _data):
            return 0

        def flush(self):
            return None

    # No NO_COLOR/FORCE_COLOR set (autouse fixture cleared them).
    monkeypatch.setattr(console.sys, "stdout", _TTY())
    assert console._use_color() is True

    monkeypatch.setattr(console.sys.stdout, "isatty", lambda: False)
    assert console._use_color() is False
