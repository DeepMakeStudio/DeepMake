%echo off
CALL "%HomePath%\Miniconda3\Scripts\activate.bat"
CALL conda activate deepmake
cd %~dp0
python startup.py