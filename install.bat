@echo off
echo Installing requirements...
pip install -r requirements.txt

echo.
echo Initializing database...
python init_db.py

echo.
echo Installation complete! You can now run the app using run.bat.
pause
