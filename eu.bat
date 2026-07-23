@echo off
chcp 65001 > nul
title notice html generator

:: 1. 현재 bat 파일이 있는 위치로 이동
cd /d "%~dp0"

echo =========================================
REM echo  현재 작업 경로: %CD%
echo =========================================
echo.

:: 2. 파이썬 스크립트 순차 실행
echo [1/2] collecting data ... (getNotice.py)
python getNotice.py all

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ getNotice.py 실행 중 오류가 발생했습니다.
    goto :ERROR
)

echo.
echo [2/2] gen HTML ... (genHTML.py)
python genHTML.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ genHTML.py 실행 중 오류가 발생했습니다.
    goto :ERROR
)

echo.
echo =========================================
echo  ✅ 모든 작업이 성공적으로 완료되었습니다!
echo =========================================
goto :END

:ERROR
echo.
echo ⚠️ 작업 도중 문제가 생겨 중단되었습니다.
pause
exit /b %ERRORLEVEL%

:END
:: 3초 후 자동으로 창 닫기 (원하시면 pause로 바끄셔도 됩니다)
timeout /t 3 > nul