@echo off
set host=localhost
set host=192.168.0.113

cls

rem NOTE: Requests for static resources go to /www implicitly. To access root folder use /..

rem Timing:
rem curl --verbose --silent --output NUL --write-out "\nEstablish Connection: %%{time_connect}s\nTTFB: %%{time_starttransfer}s\nTotal: %%{time_total}s\n" --path-as-is %host%

rem Static: Fetch the index page without naming it.
rem curl --verbose --silent --output NUL --path-as-is %host%

rem Static: Fetch the index page explicitly.
rem curl --verbose --silent --output NUL --path-as-is %host%/index.html

rem Static: Fetch favicon.
rem curl --verbose --silent --output NUL --path-as-is %host%/favicon.ico

rem Debug: Get "core dump" file.
curl --verbose --path-as-is --path-as-is %host%/../core.txt

rem Debug: Delete "core dump" file. 
rem curl --verbose --request DELETE --path-as-is %host%/../core.txt 

rem API: Fetch the data object.
rem curl --verbose --silent --output NUL --path-as-is %host%/api

rem API: Set RGB on pixel #0.
rem curl --verbose --request POST --path-as-is %host%/api?manual=1^&r0=255^&g0=255^&b0=0 

rem API: Trigger a reset. No response expected.
rem curl --verbose --request POST --path-as-is %host%/reset 

rem OTA: Upload a largish binary file to /www subdirectory.
rem curl --verbose --data-binary "@www\android-chrome-512x512.png" --path-as-is %host%/test.data

rem OTA: Delete a file from /www subdirectory
rem curl --verbose --request DELETE --path-as-is %host%/test.data 

rem OTA: Upload a file to root folder.
rem curl --verbose --data-binary "@test.data" --path-as-is %host%/../test.data

rem OTA: Delete a file from root folder.
rem curl --verbose --request DELETE --path-as-is %host%/../test.data 

rem OTA: List root folder requires trickery because root is mappped to wwww.
rem curl --verbose --path-as-is %host%/../

rem OTA: List www folder requires trickery because / is mapped to index.html.
rem curl --verbose --path-as-is %host%/../
