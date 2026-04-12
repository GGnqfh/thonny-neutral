#!/bin/bash

set -e

thonny_version=$(<../../thonny/VERSION)

echo "Releasing $thonny_version"
echo 
echo "### Creating regular installer ###############################################"
./prepare_dist_bundle.sh $thonny_version "-intel64" ../requirements-regular-bundle.txt
echo "--- Creating installer -------------------------------------"
./create_installer_from_build.sh "thonny" "Thonny" $thonny_version "x64"
