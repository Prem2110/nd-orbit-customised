#!/usr/bin/env bash
# Build script — run before `cf push`
# Compiles the React frontend and places the output inside backend/static/
# so FastAPI can serve the SPA alongside the API from a single CF app.

set -euo pipefail

echo "==> Building React frontend..."
cd "$(dirname "$0")/frontend"
npm install --silent
npm run build

echo "==> Copying build output to backend/static/..."
cd "$(dirname "$0")"
rm -rf backend/static
mkdir -p backend/static
cp -r frontend/dist/. backend/static/

echo "==> Done. backend/static/ is ready."
echo "    Deploy with: cf push --vars-file vars.yml"
