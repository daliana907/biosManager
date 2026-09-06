import os
import tempfile
from logHandler import log

def onInstall():
	log.info("BIOS Manager: instalación completada.")

def onUninstall():
	log.info("BIOS Manager: desinstalación completada.")
	try:
		tmp = tempfile.gettempdir()
		files_to_remove = [
			"nvda_bios_preload.ps1",
			"nvda_bios_preload_out.json",
			"nvda_bios_launcher.ps1",
			"nvda_bios_apply.ps1",
			"nvda_bios_apply_launcher.ps1"
		]
		for f in files_to_remove:
			p = os.path.join(tmp, f)
			if os.path.exists(p):
				os.remove(p)
		log.info("BIOS Manager: archivos temporales eliminados correctamente.")
	except Exception as e:
		log.warning(f"BIOS Manager: error al limpiar rastros: {e}")