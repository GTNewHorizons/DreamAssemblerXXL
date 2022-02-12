#!/usr/bin/env bash
curl https://raw.githubusercontent.com/GTNewHorizons/ExampleMod1.7.10/main/build.gradle -o build.gradle -sS && echo "Build.gradle downloaded"
curl https://raw.githubusercontent.com/GTNewHorizons/ExampleMod1.7.10/main/.github/workflows/release-tags.yml -o .github/workflows/release-tags.yml -sS --create-dirs && echo "Release Tags action downloaded" 
curl https://raw.githubusercontent.com/GTNewHorizons/ExampleMod1.7.10/main/CODEOWNERS -o CODEOWNERS -sS && echo "CODEOWNERS downloaded"
rm -f .github/scripts/test-no-crash-reports.sh
curl https://raw.githubusercontent.com/GTNewHorizons/ExampleMod1.7.10/main/.github/scripts/test-no-error-reports.sh -o .github/scripts/test-no-error-reports.sh -sS && echo "Test Errors script downloaded"
curl https://raw.githubusercontent.com/GTNewHorizons/ExampleMod1.7.10/main/.github/workflows/build-and-test.yml -o .github/workflows/build-and-test.yml -sS && echo "Build and Test action downloaded"

git add CODEOWNERS .github/scripts/test-no-error-reports.sh .github/workflows/release-tags.yml .github/workflows/build-and-test.yml build.gradle && echo "Everything added to git"
git update-index --chmod=+x .github/scripts/test-no-error-reports.sh && chmod +x .github/scripts/test-no-error-reports.sh
git update-index --chmod=+x gradlew && chmod +x gradlew