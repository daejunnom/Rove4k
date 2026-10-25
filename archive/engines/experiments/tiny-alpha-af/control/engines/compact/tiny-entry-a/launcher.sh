#!/bin/sh
p=$(tail -c+78 "$0"|lzma -dc)||exit
exec python3 -c "$p" "$0" "$@"
