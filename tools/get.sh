#!/bin/bash
# Usage: tools/get.sh <download folder> [--with-ubisoft]
# Fetches the source recordings. The Ubisoft set is CC BY-NC-ND 4.0: fetch it only for private, non-commercial use.
D="$1"; [ -n "$D" ] || { echo "usage: $0 <download folder> [--with-ubisoft]"; exit 1; }
mkdir -p "$D/style" "$D/cmu" "$D/lafan"
curl -sL --max-time 30 https://www.ianxmason.com/100style/ > "$D/style/index.html"
for n in Neutral Old WalkingStickLeft Elated Strutting Swat Crouched Drunk Angry StartStop Followed InTheDark; do
  id=$(grep -o "uc?id=[^&]*&amp;export=download\"[^>]*>${n}_FW.bvh" "$D/style/index.html" | head -1 | sed 's/uc?id=\([^&]*\).*/\1/')
  if [ -z "$id" ]; then echo "NOID $n"; continue; fi
  curl -sL --max-time 180 "https://drive.google.com/uc?id=${id}&export=download" -o "$D/style/${n}_FW.bvh"
  echo "$n $(head -c 9 "$D/style/${n}_FW.bvh" | tr -d '\n') $(wc -c < "$D/style/${n}_FW.bvh")"
done
for f in 137/137_33 137/137_20 137/137_29 137/137_16 142/142_07 142/142_16 132/132_29 77/77_25 105/105_32 139/139_29; do
  b=$(basename $f); s=$(dirname $f); s3=$(printf "%03d" $s)
  for u in "https://raw.githubusercontent.com/una-dinosauria/cmu-mocap/master/data/$s3/$b.bvh" "https://raw.githubusercontent.com/una-dinosauria/cmu-mocap/master/data/$s/$b.bvh"; do
    curl -sfL --max-time 60 "$u" -o "$D/cmu/$b.bvh" && break
  done
  echo "cmu $b $(head -c 9 "$D/cmu/$b.bvh" 2>/dev/null | tr -d '\n') $(wc -c < "$D/cmu/$b.bvh" 2>/dev/null)"
done
[ "$2" = "--with-ubisoft" ] || exit 0
curl -sL --max-time 500 https://media.githubusercontent.com/media/ubisoft/ubisoft-laforge-animation-dataset/master/lafan1/lafan1.zip -o "$D/lafan/lafan1.zip"
echo "lafan $(wc -c < "$D/lafan/lafan1.zip")"
cd "$D/lafan" && unzip -o -q lafan1.zip 'aiming*' 'walk1_subject1.bvh' 2>&1 | tail -2; ls "$D/lafan" | head -20
