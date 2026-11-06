@echo off
cd /d "%~dp0"
if not exist venv\Scripts\activate.bat (
  echo First-time setup, please wait...
  py -3 -m venv venv
  call venv\Scripts\activate.bat
  pip install -r requirements.txt
) else (
  call venv\Scripts\activate.bat
)
if not exist Health_Content.xlsx python make_content.py
streamlit run app.py
pause
