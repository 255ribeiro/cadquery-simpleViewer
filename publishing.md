
```powershell
$env:PYPI_TOKEN = "pypi-..."

uv build

uv publish --token $env:PYPI_TOKEN
```


```bash

export PYPI_TOKEN=pypi-...

uv build

uv publish --token $PYPI_TOKEN

```