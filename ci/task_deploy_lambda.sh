#!/bin/sh

set +x

VERSION=`cat VERSION`

if [ -z "$function_name" ]; then
    echo "Please specify param `function_name`"
    exit 1
fi
if [ -z "$s3_bucket" ]; then
    echo "Please specify param `s3_bucket`"
    exit 1
fi

s3_key="${function_name}/${function_name}-${VERSION}.zip"
echo "Deploying lambda s3://${s3_bucket}/${s3_key}..."

aws lambda update-function-code --function-name $function_name \
    --s3-bucket $s3_bucket --s3-key $s3_key --region $region

