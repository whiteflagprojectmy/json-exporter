#! /bin/bash

# Definitions
SCRIPT_DIR=`dirname ${BASH_SOURCE[0]}`
ZIP_NAME="wfp.zip"

# Copy files to current directory
cp $SCRIPT_DIR/../schema.json $SCRIPT_DIR
cp $SCRIPT_DIR/../white_flag_my/lambda_function.py $SCRIPT_DIR

# Copy module files to their respective module directories
mkdir -p $SCRIPT_DIR/whiteflag
touch $SCRIPT_DIR/whiteflag/__init__.py
cp $SCRIPT_DIR/../white_flag_my/whiteflag.py $SCRIPT_DIR/whiteflag

# Install dependencies to current directory
pip install --platform=manylinux1_x86_64 --python-version 3.8 --only-binary=:all: --no-cache -t $SCRIPT_DIR -r $SCRIPT_DIR/requirements.txt

# Zip for AWS
zip -r $SCRIPT_DIR/$ZIP_NAME $SCRIPT_DIR

# Delete all unnecessary files to keep our directory clean
find $SCRIPT_DIR -mindepth 1 -maxdepth 1 \
                             -not -name 'requirements.txt'  \
                             -not -name 'wfp.zip'           \
                             -not -name 'package_for_aws.sh'\
                             -exec rm -rf '{}' \;

echo "Done. Please upload $SCRIPT_DIR/$ZIP_NAME to S3 and update the Lambda Function with this new file"