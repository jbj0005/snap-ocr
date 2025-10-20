#!/usr/bin/env bash
set -euo pipefail

APP_NAME="Snap OCR"
BUNDLE_ID="com.example.snap-ocr"
ICON_PNG="assets/icon.png"
ICON_ICNS="assets/icon.icns"
ENTRY="src/snap_ocr/__main__.py"
DIST_APP="dist/${APP_NAME}.app"
INSTALL_APP=0
DEFAULT_INSTALL_DIR="/Applications"
FALLBACK_INSTALL_DIR="${HOME}/Applications"
INSTALL_DIR="${DEFAULT_INSTALL_DIR}"
DATA_ARGS=(
  "config.example.yaml:."
  "assets/icon.png:snap_ocr/assets"
)

usage() {
  cat <<USAGE
Usage: $(basename "$0") [--install] [--install-dir PATH]

Options:
  --install            Copy the built app bundle into \$HOME/Applications after build.
  --install-dir PATH   Copy the bundle into PATH instead of \$HOME/Applications.
  --help               Show this help message.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install)
      INSTALL_APP=1
      shift
      ;;
    --install-dir)
      if [[ $# -lt 2 ]]; then
        echo "Error: --install-dir requires a path argument" >&2
        usage
        exit 1
      fi
      INSTALL_APP=1
      INSTALL_DIR="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

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

if [[ ${INSTALL_APP} -eq 1 ]]; then
  DEST_DIR="${INSTALL_DIR%/}"
  DEST_APP="${DEST_DIR}/${APP_NAME}.app"
  echo "Installing ${APP_NAME}.app to ${DEST_APP}"

  if ! mkdir -p "${DEST_DIR}" 2>/dev/null; then
    if [[ "${INSTALL_DIR}" != "${FALLBACK_INSTALL_DIR%/}" ]]; then
      echo "Warning: Unable to write to ${DEST_DIR}; falling back to ${FALLBACK_INSTALL_DIR}" >&2
      DEST_DIR="${FALLBACK_INSTALL_DIR%/}"
      DEST_APP="${DEST_DIR}/${APP_NAME}.app"
      mkdir -p "${DEST_DIR}"
    else
      echo "Error: Unable to create ${DEST_APP}" >&2
      exit 1
    fi
  fi
  mkdir -p "${DEST_APP}"

  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "${DIST_APP}/" "${DEST_APP}/"
  else
    echo "rsync not found; using ditto for copy" >&2
    ditto "${DIST_APP}" "${DEST_APP}"
  fi
  touch "${DEST_APP}"
  echo "Installed ${APP_NAME}.app to ${DEST_APP}"
fi

cat <<EOF

Built ${DIST_APP}
Next steps:
  1) Run scripts/sign_and_notarize.sh after editing your identity/profile.
  2) Test the .app from dist/.
  3) Use --install to copy into ${INSTALL_DIR} automatically (already done if requested).
EOF
