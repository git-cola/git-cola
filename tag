#!/bin/sh
tag="$1"
exec git tag -sm"git-cola $tag" "$tag"
