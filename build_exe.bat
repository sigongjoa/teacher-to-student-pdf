@echo off
echo ========================================
echo  PDF Converter - Build EXE
echo ========================================
echo.

echo [1/3] Installing packages...
python -m pip install PyMuPDF pyinstaller -q

echo [2/3] Building EXE... (this may take a while)
python -m PyInstaller --onefile --windowed --name "PDFConverter" teacher_to_student_pdf.py

echo.
echo [3/3] Build complete!
echo.
echo ========================================
echo  EXE location: dist\PDFConverter.exe
echo ========================================
echo.

if exist "dist\PDFConverter.exe" (
    explorer dist
)

pause
