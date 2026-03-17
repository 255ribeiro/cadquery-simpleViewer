# Publishing package

General instructions creating and publishing a pypi package using uv

## Creating the package

### 1. Create the project
```bash
uv init --lib cadquery-simpleViewer
cd cadquery-simpleViewer
```

### 2. Add runtime dependencies
```bash
uv add plotly cadquery
```

### 3. Add development dependencies
```bash
uv add --dev pytest ruff
```


This produces the following structure — the `src` layout ensures the library is well isolated from the project root and from any Python invocations during development: 
```
cadquery-simpleViewer/
├── src/
│   └── cadquery_simpleviewer/
│       ├── __init__.py          ← public API: exposes show()
│       ├── viewer.py            ← show() and show_object() functions
│       ├── plane.py             ← _base_plane() helper
│       └── py.typed             ← marks the package as typed (created by uv)
├── tests/
│   └── test_viewer.py
├── pyproject.toml
├── README.md
├── uv.lock
└── .python-version
```

### Put the code in the project

## Publishing the package

### **Get a PyPI Token**
1. Go to [PyPI Account Settings → API Tokens](https://pypi.org/manage/account/token/).
2. Create a new token:
   - **Name**: Give it a descriptive name.
   - **Scope**: Restrict to specific projects or allow all projects. 
3. **Copy the token immediately** — it won’t be shown again. 

### **Export the Token**
Store the token securely in your environment:
```bash
export PYPI_TOKEN=pypi-xxxx-xxxx-xxxx-xxxx
```
Then use it with tools like `uv` or `twine`:
```bash
uv publish --token $PYPI_TOKEN
```

## With powershell 

### **Export the Token**

```powershell
$env:PYPI_TOKEN = "pypi-..."
```

### Building and publishing
```powershell
uv build

uv publish --token $env:PYPI_TOKEN
```


## Important

### Uptade the version number in .toml file before building and publishing