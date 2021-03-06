#!/bin/sh
#
# This script sets up the DEB environment needed
#

DEB_PATH="$1"
DISTRIB_PATH="$2"
DISTRIB_FILE="$3"
DISTRIB_VERSION="$4"
DISTRIB_MODE="$5"
LIBICU="$6"
DISTRIB_RELEASE="1"

if [ -z "$DISTRIB_MODE" ]; then
    echo
    echo "usage: $0 <path to deb installer> <path to distrib directory> <distrib file root> <major.minor> <mode> <libicu>"
    echo 
    echo "example: $0 /home/builder/tinderbuild/internal/installers/deb/ /home/builder/tinderbuild/ Chandler_linux_foo 0.4 debug libicu38"
    echo
    exit 1
fi

echo
echo "$(basename $0) started with these arguments:"
echo "DEB_PATH (1)=$DEB_PATH"
echo "DISTRIB_PATH (2)=$DISTRIB_PATH"
echo "DISTRIB_FILE (3)=$DISTRIB_FILE"
echo "DISTRIB_VERSION (4)=$DISTRIB_VERSION"
echo "DISTRIB_MODE (4)=$DISTRIB_MODE"
echo "LIBICU (5)=$LIBICU"

if [ "$DISTRIB_MODE" = "release" ]; then
  DISTRIB_MODE="_"
else
  DISTRIB_MODE="_${DISTRIB_MODE}_"
fi

if [ ! -d "$DEB_PATH" ]; then
    echo "ERROR: debian local environment does not seem to be setup"
    exit 1
fi

echo "Clearing debian chandler working image"
rm -rf ${DEB_PATH}/chandler
rm -f ${DEB_PATH}/chandler_*.deb

echo "Preparing build tree"
cd ${DEB_PATH}
mkdir -p chandler
PKG_ROOT=$(cd chandler && pwd)

echo "Creating man page"
mkdir -p "$PKG_ROOT"/usr/share/man/man1
cat ${DISTRIB_PATH}/chandler/distrib/linux/chandler.1 | sed "s/CHANDLER_VERSION/${DISTRIB_VERSION}-${DISTRIB_RELEASE}/" > chandler/usr/share/man/man1/chandler.1
gzip -9 chandler/usr/share/man/man1/chandler.1

mkdir -p chandler/usr/lib chandler/DEBIAN
cd chandler/usr/lib

echo "Creating build tree from distribution files"
if [ -f ${DISTRIB_PATH}/${DISTRIB_FILE}.tar.gz ]; then
    CMD="tar xzf ${DISTRIB_PATH}/${DISTRIB_FILE}.tar.gz"
    echo $CMD; $CMD
    mv ${DISTRIB_FILE} chandler
else
    CMD="cp -a ${DISTRIB_PATH}/${DISTRIB_FILE} chandler"
    echo $CMD; $CMD
fi

echo "Creating copyright/license file"
mkdir -p "$PKG_ROOT"/usr/share/doc/chandler
COPYRIGHT_PATH="$PKG_ROOT"/usr/share/doc/chandler/copyright
echo > "$COPYRIGHT_PATH" <<EOF
Copyright (c) 2003-2008 Open Source Applications Foundation

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

EOF
cat chandler/LICENSE.txt chandler/NOTICE.txt >> "$COPYRIGHT_PATH"
rm chandler/LICENSE.txt chandler/NOTICE.txt

echo "Writing menu"
mkdir -p "$PKG_ROOT"/usr/share/menu
MENU_PATH="$PKG_ROOT"/usr/share/menu/chandler
echo '?package(chandler): needs="X11" section="Applications/Project Management" title="Chandler" longtitle="Chandler - Note-to-Self organizer" command="/usr/bin/chandler" icon="/usr/share/icons/hicolor/scalable/apps/chandler.svg"' > $MENU_PATH

echo "Writing desktop file"
mkdir -p "$PKG_ROOT"/usr/share/applications
cp $DEB_PATH/chandler.desktop "$PKG_ROOT"/usr/share/applications/chandler.desktop

echo "Writing changelog"
cat ${DISTRIB_PATH}/chandler/distrib/linux/changelog | 
   gzip -c -9 > "$PKG_ROOT"/usr/share/doc/chandler/changelog.Debian.gz

echo "Creating /usr/bin/chandler symlink"
mkdir -p "$PKG_ROOT"/usr/bin
(cd "$PKG_ROOT"/usr/bin && ln -s ../lib/chandler/chandler)

echo "Removing test code"
find chandler -type d -name 'test*' -prune -exec rm -rf '{}' \;
find chandler -type d -name 'DataFiles' -prune -exec rm -rf '{}' \;
find chandler -type d -name 'recorded_scripts' -prune -exec rm -rf '{}' \;

echo "Correcting permissions"
for file in chandler/release/db/bin/*; do
    chmod u+w "$file"
    strip "$file"
done
find chandler/release/site-packages/lucene-* \
     chandler/release/site-packages/wx/tools/Editra \
         -type f -exec chmod -x {} \;

echo "Stripping executables and libraries"
find chandler -type f -name '*.so' -print -exec strip {} \; -exec chmod -x {} \;
find chandler -type f -name 'lib*.so.*' -print -exec strip {} \; -exec chmod -x {} \;
find chandler/release/j2re-image/bin chandler/release/j2re-image/lib/jexec -type f -exec strip {} \; -print

echo "Copying shared icons"
mkdir -p "$PKG_ROOT"/usr/share/icons/hicolor/scalable/apps
mv -v chandler/Chandler.egg-info/resources/images/Logos/Superdoge.svg \
      "$PKG_ROOT"/usr/share/icons/hicolor/scalable/apps/chandler.svg
mkdir -p "$PKG_ROOT"/usr/share/icons/hicolor/64x64/apps
mv -v chandler/Chandler.egg-info/resources/images/Logos/Chandler_64.png \
      "$PKG_ROOT"/usr/share/icons/hicolor/64x64/apps/chandler.png
mkdir -p "$PKG_ROOT"/usr/share/pixmaps
cp "$PKG_ROOT"/usr/share/icons/hicolor/64x64/apps/chandler.png "$PKG_ROOT"/usr/share/pixmaps/chandler.png

rm -rf chandler/Chandler.egg-info/resources/images/Logos

echo "Ensuring all files have a+r set"
chmod -R a+r chandler/

echo "Making all files owner writable"
find chandler -type f -perm 0444 -exec chmod u+w {} \;

cd ${DEB_PATH}
CHANDLER_SIZE=`du -c -k ${DEB_PATH}/chandler/usr/lib/chandler | tail -n1 | awk '{ print $1 }'`
CHANDLER_ARCH=$(eval $(dpkg-architecture); echo $DEB_HOST_ARCH)
sed -e "s/CHANDLER_VERSION/${DISTRIB_VERSION}-${DISTRIB_RELEASE}/" \
    -e "s/CHANDLER_SIZE/${CHANDLER_SIZE}/" \
    -e "s/CHANDLER_ARCH/${CHANDLER_ARCH}/" \
    -e "s/LIBICU/${LIBICU}/" \
        < ${DEB_PATH}/control.in > ${DEB_PATH}/chandler/DEBIAN/control
echo `pwd`

CMD="fakeroot -- dpkg-deb -b chandler chandler_${DISTRIB_VERSION}-${DISTRIB_RELEASE}_i386.deb"
echo "Calling $CMD"
$CMD

CMD="cp ${DEB_PATH}/chandler_${DISTRIB_VERSION}-${DISTRIB_RELEASE}_i386.deb ${DISTRIB_PATH}/Chandler_linux${DISTRIB_MODE}${DISTRIB_VERSION}-${DISTRIB_RELEASE}_i386.deb"
echo "Calling $CMD"
$CMD

echo "deb generation done"
