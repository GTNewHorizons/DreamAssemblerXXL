#!/bin/bash
curl https://raw.githubusercontent.com/GTNewHorizons/ExampleMod1.7.10/main/build.gradle -o build.gradle -sS && echo "Build.gradle downloaded"
curl https://raw.githubusercontent.com/GTNewHorizons/ExampleMod1.7.10/main/.github/workflows/release-tags.yml -o .github/workflows/release-tags.yml -sS --create-dirs && echo "Release Tags action downloaded" 
curl https://raw.githubusercontent.com/GTNewHorizons/ExampleMod1.7.10/main/CODEOWNERS -o CODEOWNERS -sS && echo "CODEOWNERS downloaded"
git add CODEOWNERS .github/workflows/release-tags.yml build.gradle && echo "Everything added to git"
