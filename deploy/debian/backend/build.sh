#!/bin/bash -ex


NUMBER=${BUILD_NUMBER-0}

# full path to deploy dir
BUILD_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT="$BUILD_DIR/root"
BOSS_ROOT="$ROOT/opt/boss"
PROJECT_ROOT="$( cd "$BUILD_DIR/../../../" && pwd )"
BUILDOUT="$PROJECT_ROOT/.buildout"

mkdir -p $ROOT/DEBIAN
cp $BUILD_DIR/DEBIAN/* $ROOT/DEBIAN
sed -e "s/bossbackend\ (0\.0\.1)/bossbackend\ (0\.0\.$BUILD_NUMBER)/" < "$BUILD_DIR/changelog" > "$ROOT/DEBIAN/changelog"
sed -e "s/version:\ 0\.0\.1/version:\ 0\.0\.$BUILD_NUMBER/" < $BUILD_DIR/control > "$ROOT/DEBIAN/control"

rm -rf $BOSS_ROOT/*
mkdir -p $BOSS_ROOT
mkdir -p $BOSS_ROOT/.buildout
mkdir -p $BOSS_ROOT/etc/

cp -r $BUILDOUT/parts/ $BUILDOUT/develop/ $BUILDOUT/eggs $BOSS_ROOT/.buildout/
cp -r $PROJECT_ROOT/backend/ $PROJECT_ROOT/bin/ $PROJECT_ROOT/boss_client/ $PROJECT_ROOT/configs/ $PROJECT_ROOT/lib/ $BOSS_ROOT
cp $PROJECT_ROOT/build $PROJECT_ROOT/version $BOSS_ROOT

mkdir -p $ROOT/etc
cp $PROJECT_ROOT/configs/stage/boss.sample.yaml $ROOT/etc/boss.yaml

# mkdir -p $ROOT/etc/logrotate.d
# cp $PROJECT_ROOT/configs/logrotate.conf $ROOT/etc/logrotate.d/boss.conf

mkdir -p $ROOT/etc/cron.daily/
echo "#!/bin/sh\n\nlogrotate $PROJECT_ROOT/configs/logrotate.conf" > $ROOT/etc/cron.daily/boss

cd $BUILD_DIR
dpkg -b $ROOT
