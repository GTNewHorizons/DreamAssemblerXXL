#!/usr/bin/env bash
mkdir -p .github/workflows
if [ ! -e .github/workflows/release-tags.yml ]; then
  echo "Repository does not have any workflows"
  exit 1
fi

if grep -Fq 'GTNH-Actions-Workflows' .github/workflows/release-tags.yml &> /dev/null; then
  printf 'Repository already processed!\n' >&2
  exit 1
fi

echo "Removing existing workflows if they exist"
[ ! -e .github/workflows/build-and-test.yml ] || rm .github/workflows/build-and-test.yml
[ ! -e .github/workflows/release-tags.yml ] || rm .github/workflows/release-tags.yml

if [ -e .github/scripts/test-no-crash-reports.sh ]; then
  rm .github/scripts/test-no-crash-reports.sh
  git add .github/scripts/test-no-crash-reports.sh
fi

echo "Copying new workflows from ExampleMod1.7.10"
cp ~/dev/mc/ExampleMod1.7.10/.github/workflows/build-and-test.yml .github/workflows/
cp ~/dev/mc/ExampleMod1.7.10/.github/workflows/release-tags.yml .github/workflows/

echo "Adding files and committing"
git add .github/workflows/build-and-test.yml .github/workflows/release-tags.yml
git commit -m "[ci skip] Migrate github actions to GTNH-Actions-Workflows"

git push origin master
