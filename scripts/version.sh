#!/bin/sh
VERSION=$(git describe HEAD 2>/dev/null)
VERSION=$(echo "$VERSION" | sed -e 's/^v//')
VERSION=$(echo "$VERSION" | sed -e 's/-/./g')
VERSION=$(echo "$VERSION" | perl -p -e 's/(\d+\.\d+)\.[^.]+$/\1/')
echo $VERSION
