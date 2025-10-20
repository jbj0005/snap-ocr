#!/usr/bin/env bash
set -euo pipefail

APP_NAME="Snap OCR"
BUNDLE_ID="com.example.snap-ocr"
ICON_PNG="assets/icon.png"
ICON_ICNS="assets/icon.icns"
ENTRY="src/snap_ocr/__main__.py"
DATA_ARGS=(
  "config.example.yaml:."
  "assets/icon.png:snap_ocr/assets"
)

if command -v sips >/dev/null 2>&1; then
  echo "Converting ${ICON_PNG} to ${ICON_ICNS}"
  sips -s format icns "${ICON_PNG}" --out "${ICON_ICNS}" >/dev/null
else
  echo "Warning: sips not found; ${ICON_ICNS} may be stale" >&2
fi

PYINSTALLER_ARGS=(
  --clean
  --windowed
  --name "${APP_NAME}"
  --icon "${ICON_ICNS}"
  --osx-bundle-identifier "${BUNDLE_ID}"
)
for data in "${DATA_ARGS[@]}"; do
  PYINSTALLER_ARGS+=(--add-data "${data}")
done

pyinstaller "${PYINSTALLER_ARGS[@]}" "${ENTRY}"

cat <<EOF

Built dist/${APP_NAME}.app
Next steps:
  1) Run scripts/sign_and_notarize.sh after editing your identity/profile.
  2) Test the .app from dist/.
EOF
