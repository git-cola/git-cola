#!/bin/sh
version=$(./bin/git-cola version --brief)
tag="v$version"
exec git tag -sm"git-cola $tag" "$tag"
