# Run all tests
```shell
uv run pytest
```
# Run with verbose output
```shell
uv run pytest -v
```
# Run a single file
```shell
uv run pytest tests/test_viewer.py
```
# Run a single test
```shell
uv run pytest tests/test_viewer.py::test_build_traces_custom_names
```
# Run with coverage report
```shell
uv run pytest --cov=cadquery_simpleviewer --cov-report=term-missing
```