# -*- coding: utf-8 -*-
# Gestor de BIOS y UEFI para NVDA
# Copyright (C) 2026 Daliana
# Released under the GNU General Public License version 2 (GPLv2)

import os
import tempfile

def onInstall():
	pass

def onUninstall():
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
		try:
			if os.path.exists(p):
				os.remove(p)
		except OSError:
			pass