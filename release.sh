#!/bin/bash

set -e

make test
git tag "v`cat setup.py| grep version | tr "'" " " | awk '{print $2}'`"
git push --tags
make upload
