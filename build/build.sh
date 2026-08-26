#!/bin/bash
# 一鍵 build：自動建 venv、裝 python-markdown、產出 public/
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q --upgrade pip
fi
.venv/bin/pip list 2>/dev/null | grep -qi '^markdown ' || .venv/bin/pip install -q markdown
.venv/bin/python site.py
