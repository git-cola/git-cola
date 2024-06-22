#!/bin/sh
tag="$1"
if test -z "${tag}"
then
    tag="v$(./bin/git-cola version --brief --builtin)"
fi
exec git tag -sm"git-cola $tag" "$tag"
