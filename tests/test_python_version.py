"""One environment, the same everywhere: the Python version, the locked libraries, the Docker image, CI and the texts."""
import fnmatch
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


def test_the_python_version_is_the_same_everywhere():
    version = read(".python-version").strip()
    assert re.fullmatch(r"3\.\d+\.\d+", version), version              # an exact release, not a range or a minor series
    minor = version.rsplit(".", 1)[0]
    assert re.findall(r"^FROM python:(\S+)-slim\b", read("Dockerfile"), re.M) == [version]
    project = tomllib.loads(read("pyproject.toml"))["project"]
    assert project["requires-python"] == f"=={minor}.*"                   # uv resolves the lock for that series only
    assert f'requires-python = "=={minor}.*"' in read("uv.lock")
    for name in ("README.md", "CLAUDE.md"):
        # every version a text names is this one; "python3.12" as the name of a command is its minor series
        named = re.findall(r"(?i)\bpython[ -]?(3\.\d+(?:\.\d+)?)", read(name))
        assert version in named and set(named) <= {version, minor}, (name, named)


def test_the_libraries_are_declared_once_and_locked():
    pyproject = tomllib.loads(read("pyproject.toml"))
    declared = pyproject["project"]["dependencies"] + pyproject["dependency-groups"]["dev"]
    assert all(re.fullmatch(r"[a-z0-9-]+==[\d.]+", d) for d in declared), declared        # exact pins, nothing open
    lock = tomllib.loads(read("uv.lock"))
    locked = {p["name"]: p.get("version") for p in lock["package"]}
    for d in declared:
        name, pinned = d.split("==")
        assert locked[name] == pinned, (name, locked.get(name), pinned)
    assert not (ROOT / "requirements.txt").exists()                      # one place for the libraries, not two


def test_every_command_runs_in_the_one_image():
    docker = read("Dockerfile")
    assert "RUN uv sync --locked" in docker and "COPY pyproject.toml uv.lock .python-version ./" in docker
    assert "RUN python -m pytest -q -p no:cacheprovider && python -m thesis build --offline" in docker
    assert 'CMD ["python", "-m", "http.server", "8000", "--bind", "0.0.0.0", "--directory", "docs"]' in docker
    # CI builds the same image and runs the build in it, instead of setting Python up on its own
    workflow = read(".github/workflows/build.yml")
    assert "docker build -t near-real-usage ." in workflow and "near-real-usage\n          python -m thesis build" in workflow
    assert "setup-python" not in workflow and "pip install" not in workflow
    makefile = read("Makefile")
    for target in ("serve", "test", "offline", "build", "snapshot", "census", "wallets", "outcomes", "thesis"):
        assert re.search(rf"^(?:\S+ )*{target}(?: \S+)*:", makefile, re.M), target
    assert '-v "$(CURDIR):/app" $(IMAGE)-env' in makefile and "docker build --target env" in makefile
    command = "docker build -t near-real-usage . && docker run --rm -p 8000:8000 near-real-usage"
    assert command in read("README.md") and command in docker
    patterns = [line.strip() for line in read(".dockerignore").splitlines() if line.strip() and not line.startswith("#")]

    def left_out(path):
        return any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(path, p.removeprefix("**/")) or path.startswith(p.rstrip("/") + "/")
                   for p in patterns)

    # what the tests and the build read stays in the build context, and what a clean clone does not have stays out
    for kept in ("data/bq/account_age.csv", "data/raw/nearblocks_charts.json", "data/raw/census_sample.csv",
                 "data/snapshot/thesis_summary.json", "docs/summary.json", "docs/index.html", "sql/account_age.sql",
                 "tests/test_python_version.py", "thesis/__main__.py", ".github/workflows/build.yml", ".python-version",
                 "Dockerfile", "Makefile", "pyproject.toml", "uv.lock", "README.md", "THESIS.md", "PREDICTIONS.md",
                 "AGENTS.md", "CLAUDE.md", "predictions.csv", "predictions.csv.ots"):
        assert (ROOT / kept).exists() and not left_out(kept), kept
    assert all(left_out(p) for p in (".venv/bin/python", ".git/HEAD", "data/census_cache/blocks", "thesis/__pycache__/x.pyc"))
