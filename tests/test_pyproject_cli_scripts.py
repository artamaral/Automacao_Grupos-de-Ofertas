import tomllib
from pathlib import Path


def test_pyproject_registers_expected_cli_scripts() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    scripts = pyproject["project"]["scripts"]

    expected_scripts = {
        "ofertas-harness",
        "ofertas-review-decide",
        "ofertas-review-export",
        "ofertas-review-gate",
        "ofertas-review-list",
        "ofertas-review-summary",
        "ofertas-manifest-create",
        "ofertas-manifest-validate",
        "ofertas-manifest-inspect",
        "ofertas-manifest-count",
        "ofertas-manifest-hash",
        "ofertas-review-bundle",
        "ofertas-local-doctor",
        "ofertas-local-flow",
    }

    assert expected_scripts <= set(scripts)
