#!/bin/sh
set -e
set -x

. "$(dirname "$0")/common.sh"

version="v$(./bin/git-cola version --builtin)"
cd "${DOCUMENT_ROOT}"

git add -u
git add share
git commit -s -m "git-cola ${version}"
git push origin
