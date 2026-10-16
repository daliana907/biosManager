# -*- coding: utf-8 -*-
# Gestor de BIOS y UEFI para NVDA
# Copyright (C) 2026 Daliana
# Released under the GNU General Public License version 2 (GPLv2)

import os
import tempfile


# Nombres heredados de versiones anteriores (era de scripts con nombre fijo).
# La version actual del backend crea temporales unicos por proceso con mkstemp
# (prefijos nvda_bios_pwd_/nvda_bios_salida_/nvda_bios_snapshot_, con limpieza
# propia y barrido de snapshots viejos), asi que ya no colisionan entre una
# instalacion NVDA portable y otra de escritorio aunque compartan %TEMP%.
_LEGACY = [
	"nvda_bios_preload.ps1",
	"nvda_bios_preload_out.json",
	"nvda_bios_launcher.ps1",
	"nvda_bios_apply.ps1",
	"nvda_bios_apply_launcher.ps1",
]


def _dirsTemporales():
	"""Directorio temporal del sistema mas el del perfil actual (portable)."""
	dirs = []
	try:
		dirs.append(tempfile.gettempdir())
	except Exception:
		pass
	try:
		import globalVars
		cfg = getattr(getattr(globalVars, "appArgs", None), "configPath", None)
		if cfg and cfg not in dirs:
			dirs.append(cfg)
	except Exception:
		pass
	return dirs


def onInstall():
	"""Se ejecuta al instalar o actualizar el complemento Gestor de BIOS y UEFI."""
	pass

def onUninstall():
	"""Limpia los temporales conocidos generados para consultar o aplicar cambios en la BIOS."""
	# H12: sin comodines ni borrado por prefijo; solo nombres conocidos, sin seguir enlaces.
	for base in _dirsTemporales():
		for f in _LEGACY:
			p = os.path.join(base, f)
			try:
				# No seguir enlaces ni directorios: solo ficheros regulares conocidos.
				if os.path.isfile(p) and not os.path.islink(p):
					os.remove(p)
			except OSError:
				pass