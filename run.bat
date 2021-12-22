@echo off
title Eclip5e Bots 

pushd %~dp0
:run
python PGBot.py
if %errorlevel% neq 0 pause
exit