#!/bin/bash -ex


declare -A PIP_REQUIREMENTS=(
    ["Jinja2"]="pip install jinja2"
    ["j2cli"]="pip install j2cli[yaml]"
)


for req in "${!PIP_REQUIREMENTS[@]}"
do
    pip list | grep $req > /dev/null
    if [ $? -ne 0 ]; then
        echo "$req is required for build"
        echo "Install: ${PIP_REQUIREMENTS["$req"]}"
        exit 1
    fi
done

NUMBER=${BUILD_NUMBER-0}

# full path to deploy dir
BUILD_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VERSION="0.0.$NUMBER"
ROOT="$BUILD_DIR/boss_backend.$VERSION"
BOSS_ROOT="$ROOT/opt/boss"
PROJECT_ROOT="$( cd "$BUILD_DIR/../../../" && pwd )"
BUILDOUT="$PROJECT_ROOT/.buildout"

mkdir -p $ROOT/DEBIAN
cp $BUILD_DIR/DEBIAN/* $ROOT/DEBIAN

VERSION_YAML="version: $VERSION"

echo $VERSION_YAML | j2 --format=yaml $BUILD_DIR/changelog > "$ROOT/DEBIAN/changelog"
echo $VERSION_YAML | j2 --format=yaml $BUILD_DIR/control > "$ROOT/DEBIAN/control"

rm -rf $BOSS_ROOT/*
mkdir -p $BOSS_ROOT
mkdir -p $BOSS_ROOT/.buildout
mkdir -p $BOSS_ROOT/etc/

cp -r $BUILDOUT/parts/ $BUILDOUT/develop/ $BUILDOUT/eggs $BOSS_ROOT/.buildout/
cp -r $PROJECT_ROOT/backend/ $PROJECT_ROOT/bin/ $PROJECT_ROOT/boss_client/ $PROJECT_ROOT/configs/ $PROJECT_ROOT/lib/ $BOSS_ROOT
cp $PROJECT_ROOT/build $PROJECT_ROOT/version $BOSS_ROOT

mkdir -p $ROOT/etc
cp $PROJECT_ROOT/configs/stage/boss.sample.yaml $ROOT/etc/boss.yaml

mkdir -p $ROOT/etc/logrotate.d
cp $PROJECT_ROOT/configs/logrotate.conf $ROOT/etc/logrotate.d/boss.conf

mkdir -p $ROOT/etc/cron.daily/
cp $BUILD_DIR/logrotate $ROOT/etc/cron.daily/logrotate

cd $BUILD_DIR
dpkg -b $ROOT
