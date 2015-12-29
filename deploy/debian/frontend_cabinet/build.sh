#!/bin/bash -ex

NUMBER=${BUILD_NUMBER-0}

# full path to deploy dir
BUILD_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT="$BUILD_DIR/root"
PROJECT_ROOT="$( cd "$BUILD_DIR/../../../" && pwd )"
FRONTEND="$PROJECT_ROOT/frontend/lk"


cd $FRONTEND

npm install
bower --config.interactive=false install --allow-root
npm install
npm run compile


mkdir -p $ROOT
rm -rf $ROOT/*

mkdir -p $ROOT/DEBIAN
cp $BUILD_DIR/DEBIAN/* $ROOT/DEBIAN
sed -e "s/bossfrontendcabinet\ (0\.0\.1)/bossfrontendcabinet\ (0\.0\.$BUILD_NUMBER)/" < "$BUILD_DIR/changelog" > "$ROOT/DEBIAN/changelog"
sed -e "s/version:\ 0\.0\.1/version:\ 0\.0\.$BUILD_NUMBER/" < $BUILD_DIR/control > "$ROOT/DEBIAN/control"


mkdir -p $ROOT/usr/share/boss/cabinet/
cp $FRONTEND/bin/lk/* $ROOT/usr/share/boss/cabinet/


cd $BUILD_DIR
dpkg -b $ROOT
