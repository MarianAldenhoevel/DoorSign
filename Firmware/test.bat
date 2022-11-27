@echo off
set host=localhost
set host=192.168.0.113

cls

rem Fetch the index page without naming it:
rem curl --verbose %host%

rem Fetch the API data:
rem curl --verbose %host%/api

rem Set RGB on pixel #0:
rem curl --verbose -X POST %host%/api?manual=1^&r0=255^&g0=255^&b0=0 

rem Trigger a reset. No response expected.
rem curl --verbose -X POST --max-time 5 %host%/reset 

rem Upload a file (OTA):
rem curl --verbose --data-binary "@test.data" %host%/test.data

rem Upload a largish binary file to a subdirectory (OTA):
curl --verbose --data-binary "@www\android-chrome-512x512.png" %host%/www/test.data