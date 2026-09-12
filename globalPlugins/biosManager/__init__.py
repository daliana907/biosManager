# -*- coding: utf-8 -*-
# biosManager: Complemento para gestionar parámetros de BIOS/UEFI en NVDA
# Copyright (C) 2026 Daliana
# Este archivo está cubierto por la Licencia Pública General de GNU (GPLv2).
# Consulta el archivo LICENSE para más detalles.

import os
import re
import threading
import time
import wx
import addonHandler
addonHandler.initTranslation()
import globalPluginHandler
import globalVars
import scriptHandler
import inputCore
import gui
import ui

from .dialog import BiosManagerDialog
from .wmi_backend import WmiBackend

try:
	from logHandler import log
except ImportError:
	import logging
	log = logging.getLogger(__name__)


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	# Translators: Nombre de la categoría en el diálogo de Gestos de Entrada de NVDA.
	scriptCategory = _("Gestor de BIOS y UEFI")

	def __init__(self):
		"""Arranca el complemento en cuanto NVDA lo carga."""
		if getattr(globalVars.appArgs, "secureMode", False):
			raise globalPluginHandler.ActionCancelled("biosManager does not run in secure mode")

		super().__init__()
		log.info("BIOS Manager: Inicializando complemento (v1.7)...")
		self.backend = WmiBackend()
		self._dialog = None

		# Agregar submenú organizado en el menú Herramientas de NVDA
		try:
			self._toolsMenu = gui.mainFrame.sysTrayIcon.toolsMenu
			self._subMenu = wx.Menu()

			# Translators: Opción del menú para abrir la configuración de BIOS/UEFI.
			self._itemConfig = self._subMenu.Append(
				wx.ID_ANY,
				_("&Configuración de la BIOS / UEFI..."),
				_("Abre la ventana accesible para consultar y configurar la BIOS/UEFI")
			)

			# Translators: Opción del menú para reiniciar directamente en el firmware UEFI.
			self._itemReboot = self._subMenu.Append(
				wx.ID_ANY,
				_("&Reiniciar en la configuración de UEFI / BIOS..."),
				_("Reinicia el equipo directamente en la pantalla de configuración del firmware UEFI")
			)

			# Translators: Opción del menú para comprobar conflictos con otros complementos.
			self._itemConflicts = self._subMenu.Append(
				wx.ID_ANY,
				_("&Comprobar conflictos con otros complementos..."),
				_("Comprueba si existen conflictos de atajos de teclado o complementos incompatibles con el Gestor de BIOS")
			)

			# Translators: Opción del menú para consultar la documentación.
			self._itemDoc = self._subMenu.Append(
				wx.ID_ANY,
				_("&Documentación"),
				_("Abre la ayuda y documentación del Gestor de BIOS")
			)

			gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self._on_menu_open, self._itemConfig)
			gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self._on_menu_reboot, self._itemReboot)
			gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self._on_menu_conflicts, self._itemConflicts)
			gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self._on_menu_doc, self._itemDoc)

			# Translators: Nombre del submenú en el menú Herramientas de NVDA.
			self._subMenuItem = self._toolsMenu.AppendSubMenu(
				self._subMenu,
				_("&Gestor de BIOS y UEFI"),
				_("Opciones y configuración accesible de la BIOS/UEFI")
			)
			log.info("BIOS Manager: Submenú 'Gestor de BIOS y UEFI' registrado en Herramientas exitosamente.")
		except Exception as e:
			log.error(f"BIOS Manager: No se pudo registrar el submenú en Herramientas: {e}", exc_info=True)
			self._subMenuItem = None

		threading.Thread(target=self._startupBackgroundWorker, daemon=True).start()
		log.info("BIOS Manager: Complemento iniciado y listo.")

	def terminate(self):
		"""Deja todo como estaba cuando NVDA descarga el complemento."""
		log.info("BIOS Manager: Finalizando complemento...")
		if hasattr(self, "_dialog") and self._dialog:
			try:
				self._dialog.Destroy()
			except Exception as e:
				log.debug(f"BIOS Manager: Error destruyendo diálogo en terminate: {e}")
			self._dialog = None

		try:
			if hasattr(self, "_itemConfig") and self._itemConfig:
				gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, source=self._itemConfig)
			if hasattr(self, "_itemReboot") and self._itemReboot:
				gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, source=self._itemReboot)
			if hasattr(self, "_itemConflicts") and self._itemConflicts:
				gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, source=self._itemConflicts)
			if hasattr(self, "_itemDoc") and self._itemDoc:
				gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, source=self._itemDoc)
			if hasattr(self, "_subMenuItem") and self._subMenuItem:
				try:
					self._toolsMenu.DestroyItem(self._subMenuItem)
				except Exception:
					self._toolsMenu.Remove(self._subMenuItem)
		except Exception as e:
			log.debug(f"BIOS Manager: Error retirando submenú en terminate: {e}")

		super().terminate()
		log.info("BIOS Manager: Complemento finalizado limpiamente.")

	def _on_menu_open(self, event):
		log.info("BIOS Manager: Opción 'Configuración de la BIOS / UEFI' seleccionada en el menú.")
		self.open_dialog()

	def _on_menu_reboot(self, event):
		log.info("BIOS Manager: Opción 'Reiniciar en la configuración de UEFI / BIOS' seleccionada en el menú.")
		self.script_rebootToUefi(None)

	def _on_menu_conflicts(self, event):
		log.info("BIOS Manager: Opción 'Comprobar conflictos' seleccionada en el menú.")
		wx.CallAfter(self._checkAddonConflicts, interactive=True)

	def _on_menu_doc(self, event):
		try:
			addon = addonHandler.getCodeAddon()
			if addon:
				addon.openDocumentation()
				return
		except Exception as e:
			log.warning(f"BIOS Manager: Error abriendo documentación mediante API de NVDA: {e}")
		# Translators: Mensaje de error si no se encuentra la documentación del complemento.
		gui.messageBox(
			_("No se pudo abrir la documentación del complemento."),
			# Translators: Título del diálogo de error al abrir la documentación.
			_("Documentación - Gestor de BIOS"),
			wx.OK | wx.ICON_ERROR,
		)

	def _startupBackgroundWorker(self):
		try:
			time.sleep(3.0)
			self._checkAddonConflicts(interactive=False)
		except Exception as e:
			log.error(f"BIOS Manager: Error durante la comprobación de conflictos: {e}", exc_info=True)

	def auditConflicts(self):
		"""
		Audita y registra en nvda.log posibles conflictos con otros complementos instalados o activos,
		incluyendo colisiones directas de atajos de teclado (gestos) y complementos de BIOS duplicados.
		Devuelve una tupla (conflicts, warnings).
		"""
		conflicts = []
		warnings = []

		our_gestures_map = {}
		g_map = getattr(self, "_gestureMap", {}) or {}
		if g_map:
			for g_id, script_ref in g_map.items():
				norm_g = str(g_id).strip().lower().replace(" ", "")
				desc = getattr(script_ref, "description", "") or getattr(script_ref, "__doc__", "") or getattr(script_ref, "__name__", str(script_ref))
				our_gestures_map[norm_g] = desc

		log.info("BIOS Manager: Iniciando auditoría exhaustiva de compatibilidad y conflictos con otros complementos...")

		# 1. Comprobar complementos duplicados de BIOS usando límites de palabra completa
		try:
			available_addons = list(addonHandler.getAvailableAddons())
			log.info(f"BIOS Manager: Analizando {len(available_addons)} complementos disponibles en el sistema...")
			for addon in available_addons:
				addon_name = getattr(addon, "name", "").lower()
				if addon_name == "biosmanager":
					continue

				if getattr(addon, "isDisabled", False):
					continue

				manifest = getattr(addon, "manifest", {}) or {}
				summary = manifest.get("summary", "")

				if re.search(r'\b(bios|uefi)\b', summary, re.IGNORECASE):
					msg = f"Complemento con funciones similares activo: '{addon.name}' ({summary}). Podría colisionar en la gestión de firmware."
					warnings.append(msg)
					log.warning(f"BIOS Manager ADVERTENCIA DE COMPATIBILIDAD: {msg}")
		except Exception as e:
			log.error(f"BIOS Manager: No se pudo verificar la lista de complementos instalados: {e}", exc_info=True)

		# 2. Comprobar colisiones directas de atajos con otros plugins globales
		try:
			running = getattr(globalPluginHandler, "runningPlugins", set())
			log.info(f"BIOS Manager: Inspeccionando {len(running)} plugins globales activos en busca de colisiones de atajos...")
			for plugin in running:
				if plugin is self:
					continue
				plugin_mod = getattr(plugin, "__module__", str(type(plugin)))
				if "biosmanager" in plugin_mod.lower():
					continue

				g_map = getattr(plugin, "_gestureMap", {}) or {}
				if not g_map:
					g_map = getattr(plugin, "_ScriptableObject__gestures", {}) or {}

				for g_id, script_ref in g_map.items():
					norm_g = str(g_id).strip().lower().replace(" ", "")
					if norm_g in our_gestures_map:
						script_name = getattr(script_ref, "__name__", str(script_ref))
						our_feature = our_gestures_map[norm_g]
						collision_msg = (
							f"Colisión de atajo: '{norm_g}' está asignado tanto a '{our_feature}' (BIOS Manager) "
							f"como a '{script_name}' en el plugin '{plugin_mod}'."
						)
						conflicts.append(collision_msg)
						log.warning(f"BIOS Manager CONFLICTO DE ATAJO: {collision_msg}")
		except Exception as e:
			log.error(f"BIOS Manager: Error inspeccionando runningPlugins: {e}", exc_info=True)

		# 3. Comprobar colisiones con comandos globales de NVDA
		try:
			import globalCommands
			cmd_obj = getattr(globalCommands, "commands", None)
			if cmd_obj:
				cmd_map = getattr(cmd_obj, "_gestureMap", {}) or {}
				for cmd_g, cmd_script in cmd_map.items():
					norm_cmd = str(cmd_g).strip().lower().replace(" ", "")
					if norm_cmd in our_gestures_map:
						our_feature = our_gestures_map[norm_cmd]
						cmd_desc = getattr(cmd_script, "description", "") or getattr(cmd_script, "__name__", str(cmd_script))
						collision_msg = (
							f"Colisión de atajo: '{norm_cmd}' está asignado simultáneamente a '{our_feature}' (BIOS Manager) "
							f"y al comando nativo de NVDA '{cmd_desc}'."
						)
						conflicts.append(collision_msg)
						log.warning(f"BIOS Manager CONFLICTO CON NVDA CORE: {collision_msg}")
		except Exception as e:
			log.debug(f"BIOS Manager: No se pudo verificar comandos globales nativos: {e}")

		# Resumen final en el log
		total_issues = len(conflicts) + len(warnings)
		if total_issues == 0:
			log.info("BIOS Manager: Auditoría de conflictos finalizada con éxito. No se detectaron colisiones de atajos ni complementos incompatibles activos.")
		else:
			log.warning(
				f"BIOS Manager: Auditoría de conflictos finalizada. Se detectaron {len(conflicts)} colisión(es) directa(s) de atajos "
				f"y {len(warnings)} advertencia(s) de compatibilidad."
			)

		return conflicts, warnings

	def _checkAddonConflicts(self, interactive=False):
		"""Revisa si otro complemento choca con este."""
		conflicts, warnings = self.auditConflicts()
		if interactive:
			total = len(conflicts) + len(warnings)
			if total == 0:
				# Translators: Mensaje cuando no se detecta ningún conflicto de compatibilidad.
				gui.messageBox(
					_("No se han detectado conflictos de atajos de teclado ni complementos incompatibles activos con el Gestor de BIOS."),
					# Translators: Título del cuadro de auditoría de compatibilidad.
					_("Auditoría de compatibilidad - Gestor de BIOS"),
					wx.OK | wx.ICON_INFORMATION,
				)
			else:
				lines = []
				if conflicts:
					# Translators: Encabezado de la lista de colisiones de atajos detectadas.
					lines.append(_("COLISIONES DIRECTAS DE ATAJOS:"))
					for c in conflicts:
						lines.append(f"• {c}")
				if warnings:
					if lines:
						lines.append("")
					# Translators: Encabezado de la lista de advertencias de compatibilidad.
					lines.append(_("ADVERTENCIAS DE COMPATIBILIDAD:"))
					for w in warnings:
						lines.append(f"• {w}")
				lines.append("")
				# Translators: Nota aclaratoria al final del informe de auditoría.
				lines.append(_("Nota: Los detalles completos también se han registrado en el archivo de log de NVDA."))
				gui.messageBox(
					"\n".join(lines),
					# Translators: Título del cuadro de advertencia de compatibilidad.
					_("Auditoría de compatibilidad - Gestor de BIOS"),
					wx.OK | wx.ICON_WARNING,
				)

	def open_dialog(self):
		"""Abre la ventana de ajustes de la BIOS."""
		log.info("BIOS Manager: Abriendo diálogo accesible de configuración de BIOS...")
		if self._dialog and bool(self._dialog):
			try:
				log.info("BIOS Manager: El diálogo ya estaba abierto, trayéndolo al frente.")
				self._dialog.Raise()
				self._dialog.SetFocus()
				return
			except Exception as e:
				log.debug(f"BIOS Manager: Diálogo previo no válido, recreando: {e}")
				self._dialog = None

		try:
			log.info("BIOS Manager: Instanciando BiosManagerDialog...")
			self._dialog = BiosManagerDialog(parent=gui.mainFrame, backend=self.backend)
			self._dialog.Show()
			log.info("BIOS Manager: Diálogo mostrado con éxito.")
		except Exception as e:
			log.error(f"BIOS Manager: Error abriendo ventana de BIOS: {e}", exc_info=True)
			# Translators: Mensaje cuando falla la apertura de la ventana de configuración de la BIOS.
			ui.message(_("Error al abrir la ventana de BIOS: {error}").format(error=e))

	@scriptHandler.script(
		# Translators: Descripción del script para abrir la configuración accesible de la BIOS/UEFI.
		description=_("Abre la ventana de configuración accesible de la BIOS/UEFI."),
		speakOnDemand=True,
		category=scriptCategory,
	)
	def script_openBiosManager(self, gesture: inputCore.InputGesture):
		log.info("BIOS Manager: Script de apertura ejecutado.")
		self.open_dialog()

	@scriptHandler.script(
		# Translators: Descripción del script para comprobar conflictos con otros complementos.
		description=_("Comprueba si existen conflictos de atajos de teclado o complementos incompatibles con el Gestor de BIOS."),
		category=scriptCategory,
	)
	def script_checkConflicts(self, gesture: inputCore.InputGesture):
		log.info("BIOS Manager: Script de comprobación de conflictos ejecutado desde atajo de teclado.")
		self._checkAddonConflicts(interactive=True)

	@scriptHandler.script(
		# Translators: Descripción del script para reiniciar el equipo en la configuración UEFI.
		description=_("Reinicia el equipo directamente en la pantalla de configuración del firmware UEFI."),
		category=scriptCategory,
	)
	def script_rebootToUefi(self, gesture: inputCore.InputGesture):
		log.info("BIOS Manager: Script de reinicio a UEFI ejecutado desde atajo de teclado.")
		# Translators: Pregunta de confirmación antes de reiniciar el equipo para entrar a UEFI.
		pregunta = _("¿Seguro que deseas reiniciar el equipo ahora mismo para acceder a la BIOS / UEFI?")
		# Translators: Título del diálogo de confirmación para reiniciar a UEFI.
		titulo = _("Reiniciar a UEFI - Gestor de BIOS")
		if gui.messageBox(pregunta, titulo, wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
			ok, msg = self.backend.reboot_to_uefi()
			if not ok:
				ui.message(msg)
