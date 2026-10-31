@echo off
py -m venv .venv
call .venv\Scripts\activate
py -m pip install --upgrade pip
pip install -r requirements.txt
py app.py
