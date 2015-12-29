#!/bin/bash -ex

NUMBER=${BUILD_NUMBER-0}

# full path to deploy dir
BUILD_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT="$BUILD_DIR/root"
PROJECT_ROOT="$( cd "$BUILD_DIR/../../../" && pwd )"
FRONTEND="$PROJECT_ROOT/frontend/admin"


cd $FRONTEND

npm install
bower --config.interactive=false install --allow-root
npm install
npm run compile


mkdir -p $ROOT
rm -rf $ROOT/*

mkdir -p $ROOT/DEBIAN
cp $BUILD_DIR/DEBIAN/* $ROOT/DEBIAN
sed -e "s/bossfrontendadmin\ (0\.0\.1)/bossfrontend\ (0\.0\.$BUILD_NUMBER)/" < "$BUILD_DIR/changelog" > "$ROOT/DEBIAN/changelog"
sed -e "s/version:\ 0\.0\.1/version:\ 0\.0\.$BUILD_NUMBER/" < $BUILD_DIR/control > "$ROOT/DEBIAN/control"


mkdir -p $ROOT/usr/share/boss/admin/
cp $FRONTEND/bin/admin/* $ROOT/usr/share/boss/admin/


cd $BUILD_DIR
dpkg -b $ROOT
