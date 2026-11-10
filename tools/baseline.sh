#!/bin/sh
out=${1:-baseline}
mkdir -p "$out"
i=0
while IFS= read -r c; do
  i=$((i+1))
  eval "python3 bible.py $c" > "$out/$i.txt" 2>&1
done <<'CMDS'
list
read 創世記 1
read Genesis 1:1 --en --cuv
search 起初 --lang big5
intro 創世記
orig 創世記 1:1 --word 1
strong G26
CMDS
