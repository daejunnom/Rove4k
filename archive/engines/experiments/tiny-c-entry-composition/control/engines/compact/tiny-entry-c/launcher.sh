#!/bin/sh
p=$(tail -c+76 "$0"|xz -dc)||exit
exec python3 -c "$p" "$0" "$@"
