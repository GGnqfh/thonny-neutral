#!/bin/bash

set -e

thonny_version=$(<../../thonny/VERSION)

xcrun stapler staple "dist/thonny-${thonny_version}-arm64.pkg"
xcrun stapler staple "dist/thonny-${thonny_version}-x64.pkg"
