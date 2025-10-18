#!/usr/bin/env bash
set -euo pipefail

APP_NAME="Snap OCR"
BUNDLE_ID="com.example.snap-ocr"
ICON_PNG="assets/icon.png"
ICON_ICNS="assets/icon.icns"
ENTRY="src/snap_ocr/__main__.py"
DATA_ARGS="config.example.yaml:."

if [[ ! -f ${ICON_ICNS} ]]; then
  if command -v sips >/dev/null 2>&1; then
    echo "Converting ${ICON_PNG} to ${ICON_ICNS}"
    sips -s format icns "${ICON_PNG}" --out "${ICON_ICNS}"
  else
    echo "Warning: sips not found; ${ICON_ICNS} missing" >&2
  fi
fi

pyinstaller   --clean   --windowed   --name "${APP_NAME}"   --icon "${ICON_ICNS}"   --osx-bundle-identifier "${BUNDLE_ID}"   --add-data "${DATA_ARGS}"   "${ENTRY}"

cat <<EOF

Built dist/${APP_NAME}.app
Next steps:
  1) Run scripts/sign_and_notarize.sh after editing your identity/profile.
  2) Test the .app from dist/.
EOF
