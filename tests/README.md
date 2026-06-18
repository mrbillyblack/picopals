# Unit Tests — a short guide

This folder holds the automated tests for the **picopals** backend API.
It's written to be approachable if you're new to unit testing in Python.

## What's here

| File | What it covers |
|------|----------------|
| `test_pet_logic.py` | The **pure simulation** (`app/pet_logic.py`): hatching timeline, stat decay, feeding/playing/cleaning, sickness & medicine, light/sleep. No database or network — fast and deterministic. |
| `test_api.py` | The **HTTP API** end-to-end via FastAPI's `TestClient`: creating users, recovery codes, polling pet state, actions, reset, and error cases. |
| `conftest.py` | Shared **fixtures**. Spins the app up against a throwaway SQLite DB and an in-memory fake for Redis, so you need *neither MySQL nor Redis running* to test. |
| `pytest.ini` | Points `pytest` at the backend package so `import app...` works. |

## Concepts in 60 seconds

- **Unit test**: a small, isolated check that one piece of code does what you
  expect. Each `test_*` function is one case. It runs the code, then `assert`s
  the result. If an assert fails, the test fails.
- **Fixture**: reusable setup, declared with `@pytest.fixture`. Our `client`
  fixture builds a fresh app + database for each test so tests can't pollute
  each other. A test just adds `client` as an argument to receive it.
- **Mock / fake**: a stand-in for a real dependency. We *fake Redis* with a
  plain dict (`fake_redis` fixture, `autouse=True` so it applies everywhere)
  so tests don't need a Redis server and stay fast and deterministic.
- **Arrange / Act / Assert**: the shape of most tests — set things up, do the
  thing, check the outcome. Skim `test_pet_logic.py` to see the pattern.

## Running the tests

From this `tests/` directory:

```bash
# 1. Create a virtual environment (once)
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

# 2. Install deps (backend + test tools)
pip install -r requirements.txt

# 3. Run everything
pytest

# Useful variations:
pytest -v                       # verbose: show each test name
pytest test_pet_logic.py        # one file
pytest -k hatch                 # only tests whose name matches "hatch"
pytest -x                       # stop at first failure
```

A green run looks like `27 passed in 0.4s`. Red output points at the exact
line and the expected-vs-actual values.

### Running inside Docker (no local Python)

If you'd rather not install Python locally, run them in the backend image:

```bash
# from the repo root
docker compose build backend
docker run --rm -v "${PWD}/tests:/tests" -w /tests \
  -e DATABASE_URL=sqlite+pysqlite:///./test.db \
  picopals-backend sh -c "pip install pytest httpx && pytest"
```

## Adding a test

1. Pick the right file (`pet_logic` for pure logic, `api` for HTTP behavior).
2. Write a function named `test_something_specific`.
3. Arrange inputs, act, then `assert` the outcome. Prefer one behavior per test.
4. For new endpoints, the `client` fixture is all you need.

## Measuring coverage (optional)

```bash
pip install pytest-cov
pytest --cov=app --cov-report=term-missing
```

`--cov-report=html` writes a browsable `htmlcov/index.html` highlighting any
lines the tests never executed.
