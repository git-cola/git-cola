#!/bin/sh
version=v$(./bin/git-cola version --brief) &&
cd ../git-cola.github.io &&
git add -u &&
git add share &&
git commit -sm"git-cola $version" &&
git push origin master
