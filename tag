#!/bin/sh
tag="$1"
if test -z "${tag}"
then
    tag="v$(./bin/git-cola version --brief | cut -d. -f1,2,3)"
fi
exec git tag -sm"git-cola $tag" "$tag"
