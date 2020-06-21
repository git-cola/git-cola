#!/bin/bash
folder=tmp/a_repo

nodeI=0

function node() {
    n=$nodeI
    nodeI=$((nodeI+1))

    touch $n >> /dev/null
    git add $n >> /dev/null
    if ! [ "$1" == "" ] ; then
        n=$1
    fi
    git commit -m node-$n- >> /dev/null
    if ! [ "$1" == "" ] ; then
        git tag -m "" $n  >> /dev/null
    fi
}

function get_SHA1() {
    git log --all --grep node-$1- | grep commit | sed -e 's/commit //'
}

function goto() {
    SHA1=$(get_SHA1 $1)
    git checkout $SHA1 -b $2 >> /dev/null
}

function merge() {
    n=$nodeI
    nodeI=$((nodeI+1))

    SHA1=$(get_SHA1 $1)
    git merge --no-ff $SHA1 -m node-$n- >> /dev/null
}

function range() {
    i=$1
    I=$2
    res=$i
    while [[ i -lt I ]] ; do
        i=$((i+1))
        res="$res $i"
    done
    echo $res
}

function nodes() {
    I=$(($1-1))
    for i in $(range 0 $I) ; do
        node
    done
}

rm -rf "$folder"
mkdir "$folder"
cd "$folder"

git init
git symbolic-ref HEAD refs/heads/main

# Tags are used to get difference between row and generation values.
# Branches main & b2 occupied 2 rows per generation because of tags.
# Branches b0 is at the left of tags. Therefore, b0 uses 1 row per generation.
# The same is for b1 too. The b1 is short but tag 'b1' cannot be placed
# right at the row the branch ends, because the tags at the right were already
# placed (they have less generation value). Hence, a gap between last two
# commits of b1 is big. Let b0 forks at a row inside the gap. The fork commit
# have greater generation than last commit of b1. Hence, it is placed after.
# Because of the bug, making many enough branches starting from the fork will
# manage to overlapping of last commit of b1 and a commit of a branch.

node tag0
node tag1
node tag2
node tag3
node tag4
nodes 1

goto tag0 b0
nodes 8
b0_head=$n

goto tag0 b1
nodes 5

goto tag0 b2
nodes 10

git checkout b0
nodes 5

goto $b0_head b5
nodes 5

goto $b0_head b6
nodes 5

goto $b0_head b7
nodes 5

git checkout b2

../../../bin/git-dag --all &

