#!/usr/bin/env bash
# Valida el proyecto con pyright usando el venv local.
# Sale con codigo != 0 si hay errores.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -x ".venv/bin/pyright" ]]; then
  echo "pyright no está instalado en .venv. Instalándolo..."
  .venv/bin/pip install --quiet pyright
fi

.venv/bin/pyright
