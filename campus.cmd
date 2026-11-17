@echo off
setlocal
set "campus_python=%~dp0runtime\python\python.exe"
if not exist "%campus_python%" (
    echo Bundled Python was not found. Extract the entire deployment ZIP first.
    exit /b 1
)
pushd "%~dp0" || exit /b 1
"%campus_python%" -B -X utf8 -m campus %*
set "campus_exit=%errorlevel%"
popd
exit /b %campus_exit%
