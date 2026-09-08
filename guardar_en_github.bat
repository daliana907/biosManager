@echo off
title Guardar BIOS Manager en GitHub
cd /d "%~dp0"
echo.
echo ===========================================================
echo   GUARDAR BIOS MANAGER EN GITHUB
echo ===========================================================
echo.
echo Archivos que han cambiado desde la ultima vez que guardaste:
echo.
git status --short
echo.
echo -----------------------------------------------------------
echo Guardando...
git add -A
git commit -m "Correcciones y limpieza de BIOS Manager" -m "- Seis fallos corregidos, entre ellos uno que impedia aplicar cambios en la BIOS y otro que dejaba ilegible el archivo de resultados." -m "- Ahora se comprueba si la BIOS acepto o rechazo cada cambio de verdad, en vez de darlo por bueno." -m "- El guardado ya no bloquea NVDA: se hace en segundo plano." -m "- Editor del orden de arranque rehecho: lista con Alt+flechas y resumen corto de lo que cambia." -m "- Aviso al cerrar si queda un cambio escrito sin aplicar, que antes se perdia en silencio." -m "- Unas 119 lineas de codigo muerto eliminadas y dos agujeros de seguridad tapados." -m "- Red de pruebas automaticas: 42 comprobaciones."
echo.
echo -----------------------------------------------------------
echo Subiendo a GitHub...
git push
echo.
echo ===========================================================
if errorlevel 1 (
  echo   NO SE PUDO SUBIR A GITHUB.
  echo   El trabajo SI quedo guardado en tu equipo, no se ha perdido nada.
  echo   Lo de arriba dice por que fallo la subida.
) else (
  echo   LISTO. Guardado en tu equipo y subido a GitHub.
)
echo ===========================================================
echo.
pause
