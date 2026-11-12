#!/bin/sh
out=${1:-baseline}
mkdir -p "$out"
i=0
while IFS= read -r c; do
  i=$((i+1))
  eval "python3 bible.py $c" > "$out/$i.txt" 2>&1
done <<'CMDS'
list
list 舊約
read 創世記 1
read 創世記 1:1
read 創 1:1
read gen 1:1
read 創世 1:1
read Genesis 1:1 --en --cuv
read 創世記 1 --no-outline --no-footnote
read 創世記 1 --cuv
read 詩篇 3
search 起初 --lang big5
search beginning --lang eng
intro 創世記
intro 詩篇
note 創世記 1:1 1
orig 創世記 1:1 --word 1
strong G26
CMDS
