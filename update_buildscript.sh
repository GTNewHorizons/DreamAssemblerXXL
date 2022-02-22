#!/usr/bin/env bash
curl https://raw.githubusercontent.com/GTNewHorizons/ExampleMod1.7.10/main/build.gradle -o build.gradle -sS && echo "Build.gradle downloaded"
curl https://raw.githubusercontent.com/GTNewHorizons/ExampleMod1.7.10/main/.github/workflows/release-tags.yml -o .github/workflows/release-tags.yml -sS --create-dirs && echo "Release Tags action downloaded" 
curl https://raw.githubusercontent.com/GTNewHorizons/ExampleMod1.7.10/main/CODEOWNERS -o CODEOWNERS -sS && echo "CODEOWNERS downloaded"
rm -f .github/scripts/test-no-*
curl https://raw.githubusercontent.com/GTNewHorizons/ExampleMod1.7.10/main/.github/scripts/test_no_error_reports -o .github/scripts/test_no_error_reports -sS && echo "Test Errors script downloaded"
curl https://raw.githubusercontent.com/GTNewHorizons/ExampleMod1.7.10/main/.github/workflows/build-and-test.yml -o .github/workflows/build-and-test.yml -sS && echo "Build and Test action downloaded"
curl https://raw.githubusercontent.com/GTNewHorizons/ExampleMod1.7.10/main/.editorconfig -o .editorconfig -sS && echo "editorconfig downloaded"

git add CODEOWNERS .github/scripts/test_no_error_reports .github/workflows/release-tags.yml .github/workflows/build-and-test.yml .editorconfig build.gradle && echo "Everything added to git"
git update-index --chmod=+x .github/scripts/test_no_error_reports && chmod +x .github/scripts/test_no_error_reports
git update-index --chmod=+x gradlew && chmod +x gradlew
