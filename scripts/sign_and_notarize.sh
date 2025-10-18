#!/usr/bin/env bash
set -euo pipefail

APP="dist/Snap OCR.app"
ZIP="dist/Snap_OCR.zip"
IDENTITY="Developer ID Application: YOUR NAME (TEAMID)"
PROFILE="notarytool-profile"
ENTITLEMENTS="packaging/entitlements.plist"

/usr/bin/codesign --deep --force --options runtime --entitlements "${ENTITLEMENTS}" --sign "${IDENTITY}" "${APP}"

ditto -c -k --keepParent "${APP}" "${ZIP}"

xcrun notarytool submit "${ZIP}" --keychain-profile "${PROFILE}" --wait

xcrun stapler staple "${APP}"

echo "Notarization complete."
