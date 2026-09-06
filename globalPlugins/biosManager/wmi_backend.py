# -*- coding: utf-8 -*-
# Backend WMI para el complemento BIOS Manager de NVDA.
# Soporte para Lenovo WMI BIOS (ThinkPad, ThinkCentre, etc.) y reinicio a UEFI.

import os
import subprocess
import logging
import json
from typing import List, Dict, Optional, Tuple

log = logging.getLogger(__name__)

try:
	import comtypes
	import comtypes.client
	COM_AVAILABLE = True
except ImportError:
	COM_AVAILABLE = False


class WmiBackend:
	"""Clase para interactuar con la BIOS/UEFI mediante WMI."""

	def __init__(self):
		self._system_info: Optional[Dict[str, str]] = None
		self._lenovo_supported: Optional[bool] = None
		self._selections_cache: Dict[str, List[str]] = {}

	def _get_wmi_services(self, namespace: str = "root\\wmi"):
		"""Obtiene el objeto SWbemServices para un namespace específico."""
		locator = comtypes.client.CreateObject("WbemScripting.SWbemLocator")
		locator.Security_.ImpersonationLevel = 3
		services = locator.ConnectServer(".", namespace)
		services.Security_.ImpersonationLevel = 3
		return services

	def get_system_info(self) -> Dict[str, str]:
		"""Obtiene información básica del fabricante, modelo y versión de BIOS."""
		if self._system_info:
			return self._system_info

		info = {
			"manufacturer": "Desconocido",
			"model": "Desconocido",
			"bios_version": "Desconocida",
		}

		if not COM_AVAILABLE:
			return info

		comtypes.CoInitialize()
		try:
			services = self._get_wmi_services("root\\cimv2")
			# Win32_ComputerSystem
			for cs in services.InstancesOf("Win32_ComputerSystem"):
				try:
					info["manufacturer"] = str(cs.Properties_("Manufacturer").Value).strip()
					info["model"] = str(cs.Properties_("Model").Value).strip()
				except Exception:
					pass
				break

			# Win32_BIOS
			for bios in services.InstancesOf("Win32_BIOS"):
				try:
					info["bios_version"] = str(bios.Properties_("SMBIOSBIOSVersion").Value).strip()
				except Exception:
					pass
				break
		except Exception as e:
			log.error(f"Error obteniendo info de sistema: {e}")
		finally:
			comtypes.CoUninitialize()

		log.info(f"BIOS Manager: Información del sistema detectada: Fabricante='{info['manufacturer']}', Modelo='{info['model']}', Versión BIOS='{info['bios_version']}'")
		self._system_info = info
		return info

	def is_supported(self) -> bool:
		"""Comprueba si este equipo tiene soporte para WMI BIOS (Lenovo) usando PowerShell."""
		if self._lenovo_supported is not None:
			return self._lenovo_supported

		try:
			cmd = "Get-CimInstance -Namespace root\\wmi -ClassName Lenovo_BiosSetting | Select-Object -First 1"
			res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
			if res.returncode == 0:
				try:
					out_str = res.stdout.decode('utf-8')
				except UnicodeDecodeError:
					out_str = res.stdout.decode('utf-16', errors='ignore')
				self._lenovo_supported = bool(out_str.strip())
			else:
				self._lenovo_supported = False
		except Exception as e:
			log.error(f"WMI SUPPORT ERROR via PowerShell: {e}")
			self._lenovo_supported = False

		# Si falla la comprobación rápida, asume True temporalmente para que get_all_settings lo intente de verdad
		if not self._lenovo_supported:
			self._lenovo_supported = True

		log.info(f"BIOS Manager: Soporte Lenovo WMI BIOS evaluado: {self._lenovo_supported}")
		return self._lenovo_supported

	def get_all_settings(self) -> List[Dict[str, str]]:
		"""Obtiene todos los ajustes de la BIOS (elevado) con logs detallados."""
		log.info("Iniciando get_all_settings elevado...")
		ps_script = '''
$settings = Get-CimInstance -Namespace root\\wmi -ClassName Lenovo_BiosSetting
$results = @()
foreach ($s in $settings) {
    if ($s.CurrentSetting -match '^(.*?),(.*)$') {
        $name = $matches[1].Trim()
        $val = $matches[2].Trim()
        
        $options = ""
        try {
            $sel = Get-CimInstance -Namespace root\\wmi -ClassName Lenovo_GetBiosSelections | Invoke-CimMethod -MethodName GetBiosSelections -Arguments @{Item=$name} -ErrorAction SilentlyContinue
            if ($sel -and $sel.Selections) {
                $options = $sel.Selections
            }
        } catch {}
        
        $results += [PSCustomObject]@{
            Name = $name
            Value = $val
            Options = $options
        }
    }
}
$results | ConvertTo-Json -Compress
'''
		try:
			import tempfile
			ps_file = os.path.join(tempfile.gettempdir(), "nvda_bios_preload.ps1")
			out_file = os.path.join(tempfile.gettempdir(), "nvda_bios_preload_out.json")
			if os.path.exists(out_file):
				os.remove(out_file)
				
			with open(ps_file, "w", encoding="utf-8") as f:
				f.write(ps_script)
			
			log.info(f"Script de extracción escrito en: {ps_file}")
			
			launcher_script = f'''
$proc = new-object System.Diagnostics.Process
$proc.StartInfo.FileName = "powershell.exe"
$proc.StartInfo.Arguments = "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -Command `". '{ps_file}' | Out-File -FilePath '{out_file}' -Encoding UTF8`""
$proc.StartInfo.Verb = "runas"
$proc.StartInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
$proc.StartInfo.CreateNoWindow = $true
$proc.Start() | Out-Null
$proc.WaitForExit()
'''
			launcher_file = os.path.join(tempfile.gettempdir(), "nvda_bios_launcher.ps1")
			with open(launcher_file, "w", encoding="utf-8") as f:
				f.write(launcher_script)
			
			log.info(f"Lanzador invisible escrito en: {launcher_file}")
			log.info("Lanzando proceso powershell elevado...")
			
			res = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-NoProfile", "-File", launcher_file], creationflags=subprocess.CREATE_NO_WINDOW)
			
			log.info(f"Proceso lanzador finalizó con código: {res.returncode}")
			
			if os.path.exists(out_file):
				log.info(f"Archivo de salida encontrado: {out_file}. Leyendo JSON...")
				with open(out_file, "r", encoding="utf-8-sig") as f:
					output_str = f.read()
					
				if not output_str.strip():
					log.warning("El archivo JSON está vacío.")
					return []
					
				data = json.loads(output_str)
				log.info(f"JSON parseado. {len(data)} elementos encontrados.")
				
				results = []
				for item in data:
					opts = item.get("Options", "")
					opts_list = [x.strip() for x in opts.split(",") if x.strip()] if opts else []
					name = item.get("Name", "").strip()
					results.append({
						"name": name,
						"value": item.get("Value", "").strip(),
						"options": opts_list
					})
					self._selections_cache[name] = opts_list
				return results
			else:
				log.error(f"El archivo de salida {out_file} no se generó. Es probable que UAC haya fallado o el proceso se haya cancelado.")
				return []
		except Exception as e:
			log.error(f"Error crítico en get_all_settings: {e}", exc_info=True)
			return []

	def get_selections(self, setting_name: str) -> List[str]:
		"""
		Obtiene las opciones disponibles para un parametro usando PowerShell para evitar restricciones COM.
		"""
		if setting_name in self._selections_cache:
			return self._selections_cache[setting_name]

		selections = []
		try:
			cmd = f"(Get-CimInstance -Namespace root\\wmi -ClassName Lenovo_GetBiosSelections | Invoke-CimMethod -MethodName GetBiosSelections -Arguments @{{Item='{setting_name}'}}).Selections"
			res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
			if res.returncode == 0 and res.stdout.strip():
				selections = [opt.strip() for opt in res.stdout.strip().split(",") if opt.strip()]
		except Exception as e:
			log.error(f"Error obteniendo opciones PowerShell para '{setting_name}': {e}")

		if selections:
			log.info(f"BIOS Manager: Opciones recuperadas para '{setting_name}': {len(selections)} opción(es)")
			self._selections_cache[setting_name] = selections
		return selections

	def apply_settings(self, settings_dict: Dict[str, str]) -> Tuple[bool, str]:
		"""Aplica multiples ajustes y guarda, pidiendo UAC una sola vez."""
		if not settings_dict:
			log.info("BIOS Manager: apply_settings invocado sin cambios pendientes.")
			return True, "No hay cambios"
		log.info(f"BIOS Manager: apply_settings iniciado para {len(settings_dict)} ajustes: {settings_dict}")
		
		ps_script = ""
		for name, val in settings_dict.items():
			ps_script += f"(Get-CimInstance -Namespace root\\wmi -ClassName Lenovo_SetBiosSetting | Invoke-CimMethod -MethodName SetBiosSetting -Arguments @{{Parameter='{name},{val}'}})\n"
		ps_script += "(Get-CimInstance -Namespace root\\wmi -ClassName Lenovo_SaveBiosSettings | Invoke-CimMethod -MethodName SaveBiosSettings)\n"
		
		ps_file = os.path.join(tempfile.gettempdir(), "nvda_bios_apply.ps1")
		with open(ps_file, "w", encoding="utf-8") as f:
			f.write(ps_script)
			
		launcher_script = f'''
$proc = new-object System.Diagnostics.Process
$proc.StartInfo.FileName = "powershell.exe"
$proc.StartInfo.Arguments = "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File \"{ps_file}\""
$proc.StartInfo.Verb = "runas"
$proc.StartInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
$proc.StartInfo.CreateNoWindow = $true
$proc.Start() | Out-Null
$proc.WaitForExit()
'''
		launcher_file = os.path.join(tempfile.gettempdir(), "nvda_bios_apply_launcher.ps1")
		with open(launcher_file, "w", encoding="utf-8") as f:
			f.write(launcher_script)
			
		res = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-NoProfile", "-File", launcher_file], creationflags=subprocess.CREATE_NO_WINDOW)
		
		if res.returncode == 0:
			return True, "Ajustes aplicados correctamente."
		return False, "Error al aplicar ajustes."

	def set_setting(self, setting_name: str, new_value: str) -> Tuple[bool, str]:
		"""
		Aplica un ajuste de BIOS en la sesión usando PowerShell.
		"""
		try:
			cmd = f"(Get-CimInstance -Namespace root\\wmi -ClassName Lenovo_SetBiosSetting | Invoke-CimMethod -MethodName SetBiosSetting -Arguments @{{Parameter='{setting_name},{new_value}'}}).return"
			res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
			if res.returncode == 0:
				ret_val = res.stdout.strip()
				if ret_val.lower() == "success":
					return True, "Ajuste aplicado correctamente."
				return False, f"La BIOS devolvió: {ret_val}"
			return False, f"Error PS: {res.stderr.strip()}"
		except Exception as e:
			return False, f"Excepción: {e}"

	def save_settings(self) -> Tuple[bool, str]:
		"""
		Guarda permanentemente en la memoria NVRAM de la BIOS todos los cambios aplicados usando PowerShell.
		"""
		try:
			cmd = "(Get-CimInstance -Namespace root\\wmi -ClassName Lenovo_SaveBiosSettings | Invoke-CimMethod -MethodName SaveBiosSettings -Arguments @{Parameter=''}).return"
			res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
			if res.returncode == 0:
				ret_val = res.stdout.strip()
				if ret_val.lower() == "success":
					return True, "Cambios guardados con éxito en la BIOS. Se aplicarán al reiniciar."
				return False, f"La BIOS devolvió: {ret_val}"
			return False, f"Error PS: {res.stderr.strip()}"
		except Exception as e:
			return False, f"Excepción: {e}"

	def discard_settings(self) -> Tuple[bool, str]:
		"""
		Descarta los cambios pendientes de la sesión actual usando PowerShell.
		"""
		try:
			cmd = "(Get-CimInstance -Namespace root\\wmi -ClassName Lenovo_DiscardBiosSettings | Invoke-CimMethod -MethodName DiscardBiosSettings -Arguments @{Parameter=''}).return"
			res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
			if res.returncode == 0:
				ret_val = res.stdout.strip()
				if ret_val.lower() == "success":
					return True, "Cambios descartados."
				return False, f"La BIOS devolvió: {ret_val}"
			return False, f"Error PS: {res.stderr.strip()}"
		except Exception as e:
			return False, f"Excepción: {e}"

	@staticmethod
	def reboot_to_uefi() -> Tuple[bool, str]:
		"""
		Reinicia el equipo directamente a la pantalla de configuración del firmware UEFI.
		Usa 'shutdown /r /fw /t 2'.
		"""
		log.info("BIOS Manager: Solicitando reinicio del sistema al firmware UEFI...")
		try:
			res = subprocess.run(
				["shutdown.exe", "/r", "/fw", "/t", "2"],
				capture_output=True,
				text=True,
				creationflags=subprocess.CREATE_NO_WINDOW
			)
			log.info(f"BIOS Manager: Comando shutdown ejecutado. Código retorno={res.returncode}, salida='{res.stdout.strip()}', error='{res.stderr.strip()}'")
			if res.returncode == 0:
				return True, "El sistema se reiniciará en la BIOS / UEFI en 2 segundos."
			else:
				err = res.stderr.strip() or res.stdout.strip()
				log.warning(f"BIOS Manager: Falló shutdown /r /fw: {err}")
				return False, f"No se pudo iniciar el reinicio a UEFI ({err}). Puede requerir ejecutar NVDA como Administrador."
		except Exception as e:
			log.error(f"BIOS Manager: Error ejecutando comando de reinicio a UEFI: {e}", exc_info=True)
			return False, f"Error al ejecutar comando de reinicio: {e}"
