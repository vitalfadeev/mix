#!/bin/sh

if [ $# -lt 2 ]
then
    echo Usage $0 <sound.3gpp> <image.jpg>
    exit 1
fi

# simple
# ffmpeg -loop 1 -y -i "$2" -i "$1" -shortest -acodec copy -vcodec mjpeg result.avi

# youtube
ffmpeg -loop 1 -y -i "$2" -i "$1" -shortest -acodec copy -vcodec mjpeg -codec:v libx264 -crf 21 -bf 2 -flags +cgop -pix_fmt yuv420p -codec:a aac -strict -2 -b:a 384k -r:a 48000 -movflags faststart result.avi

