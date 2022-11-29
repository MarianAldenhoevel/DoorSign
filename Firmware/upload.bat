@echo off
rem Batch file to upload all the files named in filelist.txt to the doorsign by POSTing them
rem to the webserver on the board.

set host=192.168.0.113

cls
echo ! Uploading doorsign firmware files to %%host%% 

for /F "eol=# tokens=*" %%f in (filelist.txt) do call :upload %%f
goto :done

:upload
echo:
echo ! ---------------------------------------------------------------------------------
echo ! upload %1
curl --verbose --data-binary "@%1" --path-as-is %host%/../%1

goto :eof

:done
echo:
echo ! ---------------------------------------------------------------------------------
echo ! Upload complete. Triggering reset.
curl --verbose --request POST --max-time 5 --path-as-is %host%/reset 
