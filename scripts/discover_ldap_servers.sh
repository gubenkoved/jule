#! /usr/bin/env bash

set -ex

DOMAIN=${1:-example.org}

dig +noall +answer +multiline _ldap._tcp.$DOMAIN any
