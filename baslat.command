#!/bin/bash
# Çift tıklayınca platformu başlatır ve tarayıcıda açar (macOS).
cd "$(dirname "$0")"
python3 -m pip install -q -r requirements.txt
( sleep 2; open "http://127.0.0.1:5050" ) &
python3 app.py
