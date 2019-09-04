#!/bin/sh

set +x

if [ -z "$LAMBDA_NAME" ]; then
    echo "Please specify param LAMBDA_NAME"
    exit 1
fi

make VERSION=`cat VERSION` LAMBDA="$LAMBDA_NAME"
cp *.zip ../dist
