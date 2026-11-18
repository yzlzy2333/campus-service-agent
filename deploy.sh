#!/bin/sh
set -eu

usage() {
    printf '%s\n' 'Usage: ./deploy.sh setup | ./deploy.sh run [campus options]'
}

case ${1:-} in
    setup)
        if [ "$#" -ne 1 ]; then
            usage >&2
            exit 2
        fi
        ;;
    run) ;;
    -h|--help)
        usage
        exit 0
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac

if [ "$(uname -s)" != 'Linux' ]; then
    printf '%s\n' 'This deployment branch is for Linux.' >&2
    exit 1
fi

cd "$(CDPATH= cd -P -- "$(dirname "$0")" && pwd)"
venv_python=.venv/bin/python

case "$1" in
    setup)
        if ! command -v python3.12 >/dev/null 2>&1; then
            printf '%s\n' 'Install Python 3.12 with venv support, then try again.' >&2
            exit 1
        fi
        python3.12 -m venv .venv
        "$venv_python" -m pip install -r requirements.txt
        ;;
    run)
        if [ ! -x "$venv_python" ]; then
            printf '%s\n' 'Run ./deploy.sh setup first.' >&2
            exit 1
        fi
        shift
        exec "$venv_python" -X utf8 -m campus "$@"
        ;;
esac
