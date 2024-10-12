:: 新建Windows Terminal tab, 使用pwsh运行python脚本. 可以主动选择conda环境
:: @echo off
SET USINGFINALPROCESS=1
SET USINGCONDA=1
SET USINGBACKUPDIR=1

SET CONDAENV="WebR"
SET PYFILENAME="txtPub.py"
SET BACDIR="D:\BeetSoup\Onedrive\!Novel"
SET SAVDIR="./!!!Backups/"
IF %USINGCONDA% == 1 (
  SET "ENTERENV=conda activate %CONDAENV:~1,-1%\;"
) ELSE (
  SET "ENTERENV= "
)
IF %USINGFINALPROCESS% == 1 (
  SET "FTECHISTR= $iStr = Read-Host 'All work is done. Press CLEAR to remove all into `%SAVDIR%` ' \;"
  IF %USINGBACKUPDIR% == 1 ( SET "WEBSYNC=Copy-Item -Path ./*.ePub -Destination %BACDIR% -Force \;" ) ELSE ( SET "WEBSYNC=  "   )
  SET "SAVETXT2BAC= Move-Item -Path ./*.txt  -Destination %SAVDIR% -Force \;"
  SET "SAVEEPUB2BAC=Move-Item -Path ./*.ePub -Destination %SAVDIR% -Force \;"
  SET "FINAL= %FTECHISTR% if ('CLEAR'.Equals( $iStr ) ) { %WEBSYNC% %SAVETXT2BAC% %SAVETXT2BAC% } \; "
) ELSE (
  SET "FINAL= "
)

SET "RUNNING=python ./Utils/%PYFILENAME:~1,-1%\;"

SET PSCOMMAND="{%ENTERENV% %RUNNING% %FINAL% }"

wt nt pwsh -WorkingDirectory %~dp0 -c pwsh -Command %PSCOMMAND%
