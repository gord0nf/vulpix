@echo off

:: vulpix binary for windows. just a simple wrapper around vulpix.sh.

:: make sure bash exists
WHERE bash > NUL 2> NUL
IF %ERRORLEVEL% NEQ 0 (
  echo bash is required 1>&2
  exit 1
)

:: make sure VULPIX is defined
IF NOT DEFINED VULPIX (
  echo VULPIX environmental variable must be defined 1>&2
  exit 1
)

set "relative_script=bin\vulpix"
if "%VULPIX:~-1%"=="\" (
    set "script=%VULPIX%%relative_script%"
) else (
    set "script=%VULPIX%\%relative_script%"
)

bash "%script%" -- %*
