@echo off
REM Run the Projects CLI and pass through every argument.
REM Using %* with proper quoting to handle project names with spaces.
python "%~dp0project-manager.py" %*
