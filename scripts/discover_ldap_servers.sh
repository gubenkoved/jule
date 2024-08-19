#! /usr/bin/env bash

set -ex

DOMAIN=${1:-jnpr.net}

dig +noall +answer +multiline _ldap._tcp.$DOMAIN any
