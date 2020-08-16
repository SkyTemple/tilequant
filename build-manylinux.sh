#!/usr/bin/env bash
set -x
set -e
cd /io

rm /io/__aikku93_tilequant -rf || true
rm /io/build -rf || true

for PYBIN in /opt/python/*/bin; do
    if [[ "$PYBIN" != *"cp27"* ]] && [[ "$PYBIN" != *"cp35"* ]]; then
        "${PYBIN}/pip" install -r /io/dev-requirements.txt
        "${PYBIN}/pip" wheel /io/ --no-deps -w dist/ -vvv
    fi
done
for whl in dist/*.whl; do
    auditwheel repair "$whl" -w /io/dist/
done

rm /io/__aikku93_tilequant -rf
rm /io/build -rf
chmod a+rwX /io/dist -R
