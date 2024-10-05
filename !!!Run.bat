:: 新建Windows Terminal tab, 使用pwsh7运行python脚本. 可以主动选择conda环境
@echo off
SET USINGCONDA=1
SET CONDAENV=WebR
SET PYFILENAME=textpublisher.py
IF %USINGCONDA% == 1 (
  SET PSCOMMAND="{conda activate %CONDAENV%\; python ./%PYFILENAME% \; Read-Host -Prompt 'All work is done. Press Enter to close'}"
)ELSE(
  SET PSCOMMAND="{python ./%PYFILENAME% \; Read-Host -Prompt 'All work is done. Press Enter to close'}"
)
wt nt pwsh -WorkingDirectory %~dp0 -c pwsh -Command %PSCOMMAND%
