#!/bin/sh
LAST_TAG=$(git tag | tail -1)
git dch --debian-tag="$LAST_TAG" --release --since="$LAST_TAG" --id-length=7
