%echo off
CALL "%HomePath%\Miniconda3\Scripts\activate.bat"

copy "%~dp0\environment.yml" "%temp%\DeepMake_environment.yml"
copy "%~dp0\plugin\Diffusers\environment.yml" "%temp%\Diffusers_environment.yml

%echo on
CALL conda env update -f "%temp%\DeepMake_environment.yml"
CALL conda env update -f "%temp%\Diffusers_environment.yml"
