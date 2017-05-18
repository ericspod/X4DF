#! /bin/bash

trang x4df.rnc x4df.rng || exit $?
trang x4df.rnc x4df.xsd
#trang x4df.rnc x4df.dtd # wildcards not supported?
