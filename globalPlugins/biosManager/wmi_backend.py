# -*- coding: utf-8 -*-
# Backend WMI para el complemento BIOS Manager de NVDA.
# Soporte para Lenovo WMI BIOS (ThinkPad, ThinkCentre, etc.) y reinicio a UEFI.

import os
import subprocess
import logging
import json
import addonHandler
import tempfile
import shutil
import time
from typing import List, Dict, Tuple

addonHandler.initTranslation()

log = logging.getLogger(__name__)


class WmiBackend:
	"""Clase para interactuar con la BIOS/UEFI mediante WMI."""

	def __init__(self):
		self._selections_cache: Dict[str, List[str]] = {}

	def _ejecutarPowerShellElevado(self, ps_script, esperarSalida=False):
		"""Ejecuta un script de PowerShell pidiendo permisos de administrador una sola vez.

		El script se escribe en una carpeta temporal propia, de un solo uso y con
		nombre al azar, que se borra al terminar. Antes cada parte usaba su propio
		archivo con un nombre fijo y previsible en la carpeta temporal compartida,
		que otro programa podía sustituir entre que se escribía y se ejecutaba con
		permisos de administrador.

		ps_script: el texto del script a ejecutar.
		esperarSalida: si es True, la salida del script se guarda en un archivo y
		               se devuelve su contenido.

		Devuelve (ok, salida). ok dice si el lanzador terminó sin error; salida es
		el texto que produjo el script, o None si no se pidió o no se generó
		(por ejemplo, si se canceló el aviso de permisos).
		"""
		carpeta = tempfile.mkdtemp(prefix="nvda_bios_")
		# El archivo de salida va en la carpeta temporal normal de Windows, no dentro
		# de la carpeta privada: lo escribe el proceso con permisos de administrador y,
		# si queda dentro de una carpeta recién creada, NVDA no siempre puede leerlo
		# después. El nombre igual es distinto en cada ejecución.
		out_file = os.path.join(tempfile.gettempdir(), f"nvda_bios_salida_{os.path.basename(carpeta)}.txt")
		try:
			ps_file = os.path.join(carpeta, "script.ps1")
			with open(ps_file, "w", encoding="utf-8") as f:
				f.write(ps_script)

			if esperarSalida:
				orden = f". '{ps_file}' | Out-File -FilePath '{out_file}' -Encoding UTF8"
			else:
				orden = f". '{ps_file}'"

			launcher_script = f'''
$proc = new-object System.Diagnostics.Process
$proc.StartInfo.FileName = "powershell.exe"
$proc.StartInfo.Arguments = "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -Command `"{orden}`""
$proc.StartInfo.Verb = "runas"
$proc.StartInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
$proc.StartInfo.CreateNoWindow = $true
$proc.Start() | Out-Null
$proc.WaitForExit()
'''
			launcher_file = os.path.join(carpeta, "lanzador.ps1")
			with open(launcher_file, "w", encoding="utf-8") as f:
				f.write(launcher_script)

			log.info("BIOS Manager: Lanzando PowerShell con permisos de administrador...")
			res = subprocess.run(
				["powershell", "-ExecutionPolicy", "Bypass", "-NoProfile", "-File", launcher_file],
				creationflags=subprocess.CREATE_NO_WINDOW,
			)
			log.info(f"BIOS Manager: El lanzador terminó con código {res.returncode}.")

			salida = None
			if esperarSalida:
				salida = self._leerSalida(out_file)
			return res.returncode == 0, salida
		finally:
			shutil.rmtree(carpeta, ignore_errors=True)
			try:
				if os.path.exists(out_file):
					os.remove(out_file)
			except OSError:
				pass

	@staticmethod
	def _leerSalida(out_file, intentos=6, espera=0.4):
		"""Lee el archivo de salida, reintentando si todavía está ocupado.

		El archivo lo acaba de crear un proceso con permisos de administrador y a
		veces tarda un instante en quedar libre (el antivirus lo revisa al crearse).
		Devuelve el texto, o None si no se generó o no se pudo leer.
		"""
		for intento in range(intentos):
			if not os.path.exists(out_file):
				time.sleep(espera)
				continue
			try:
				with open(out_file, "r", encoding="utf-8-sig") as f:
					return f.read()
			except OSError as e:
				log.warning(f"BIOS Manager: Todavía no se puede leer la salida (intento {intento + 1}): {e}")
				time.sleep(espera)
		log.error(f"BIOS Manager: No se pudo leer el archivo de salida {out_file}.")
		return None

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
			ok, salida = self._ejecutarPowerShellElevado(ps_script, esperarSalida=True)
			if salida is None:
				log.error("BIOS Manager: No se generó la salida. Es probable que se cancelara el aviso de permisos de administrador.")
				return []
			if not salida.strip():
				log.warning("BIOS Manager: La salida del script está vacía.")
				return []

			data = json.loads(salida)
			log.info(f"BIOS Manager: JSON parseado. {len(data)} ajustes encontrados.")

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
		except Exception as e:
			log.error(f"BIOS Manager: Error crítico en get_all_settings: {e}", exc_info=True)
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

	@staticmethod
	def _textoPowerShell(texto):
		"""Convierte un texto en un literal de PowerShell entre comillas simples.

		Las comillas simples de dentro se duplican, que es como PowerShell las escapa.
		Así un nombre o un valor con comillas no puede partir la orden al medio.
		"""
		return "'" + str(texto).replace("'", "''") + "'"

	def apply_settings(self, settings_dict: Dict[str, str]) -> Tuple[bool, str]:
		"""Aplica varios ajustes, los graba, y comprueba si la BIOS los aceptó.

		Pide los permisos de administrador una sola vez. Dentro de esa misma
		ejecución hace tres cosas: manda cada cambio anotando lo que responde la
		BIOS, graba, y vuelve a leer los ajustes para comparar lo que quedó con lo
		que se pidió.

		Devuelve (todoCorrecto, informe), donde informe es un texto con una línea
		por ajuste, listo para leerse en voz alta.
		"""
		if not settings_dict:
			log.info("BIOS Manager: apply_settings invocado sin cambios pendientes.")
			return True, _("No hay cambios")
		log.info(f"BIOS Manager: apply_settings iniciado para {len(settings_dict)} ajustes: {settings_dict}")

		pendientes = "; ".join(
			f"{self._textoPowerShell(nombre)} = {self._textoPowerShell(valor)}"
			for nombre, valor in settings_dict.items()
		)
		ps_script = r"""
$pendientes = @{ %s }
$resultados = @()
foreach ($nombre in $pendientes.Keys) {
    $valor = $pendientes[$nombre]
    $respuesta = ''
    try {
        $r = Get-CimInstance -Namespace root\wmi -ClassName Lenovo_SetBiosSetting | Invoke-CimMethod -MethodName SetBiosSetting -Arguments @{Parameter="$nombre,$valor"}
        $respuesta = [string]$r.return
    } catch {
        $respuesta = "Excepcion: $($_.Exception.Message)"
    }
    $resultados += [PSCustomObject]@{ Name = $nombre; Requested = $valor; SetResult = $respuesta }
}

$guardado = ''
try {
    $g = Get-CimInstance -Namespace root\wmi -ClassName Lenovo_SaveBiosSettings | Invoke-CimMethod -MethodName SaveBiosSettings -Arguments @{Parameter=''}
    $guardado = [string]$g.return
} catch {
    try {
        $g = Get-CimInstance -Namespace root\wmi -ClassName Lenovo_SaveBiosSettings | Invoke-CimMethod -MethodName SaveBiosSettings
        $guardado = [string]$g.return
    } catch {
        $guardado = "Excepcion: $($_.Exception.Message)"
    }
}

$actuales = @{}
try {
    foreach ($s in Get-CimInstance -Namespace root\wmi -ClassName Lenovo_BiosSetting) {
        if ($s.CurrentSetting -match '^(.*?),(.*)$') {
            $actuales[$matches[1].Trim()] = $matches[2].Trim()
        }
    }
} catch {}

$salida = @()
foreach ($r in $resultados) {
    $salida += [PSCustomObject]@{
        Name = $r.Name
        Requested = $r.Requested
        SetResult = $r.SetResult
        Current = $actuales[$r.Name]
    }
}
[PSCustomObject]@{ SaveResult = $guardado; Settings = @($salida) } | ConvertTo-Json -Compress -Depth 4
""" % pendientes

		ok, salida = self._ejecutarPowerShellElevado(ps_script, esperarSalida=True)
		if salida is None:
			log.error("BIOS Manager: No hubo respuesta al aplicar los ajustes.")
			return False, _("No se pudo aplicar ningún cambio. Puede que se cancelara el aviso de permisos de administrador.")

		log.info(f"BIOS Manager: Respuesta de la BIOS al aplicar: {salida.strip()[:1000]}")
		try:
			datos = json.loads(salida)
		except ValueError:
			log.error("BIOS Manager: No se pudo interpretar la respuesta de la BIOS.", exc_info=True)
			return False, _("La BIOS respondió algo que no se pudo interpretar. Mira el registro de NVDA para el detalle.")

		return self._informeDeCambios(datos, settings_dict)

	@staticmethod
	def _valorLegible(valor):
		"""Acorta los valores que son una lista pegada con dos puntos.

		El orden de arranque llega como 'A:B:C:D:E:F'. Leído tal cual en el mensaje
		final es un chorizo; se resume igual que en la lista de ajustes.
		"""
		texto = str(valor or "")
		partes = [d.strip() for d in texto.split(":") if d.strip()]
		if len(partes) < 3:
			return texto
		return _("primero {dispositivo}, de {total} dispositivos").format(dispositivo=partes[0], total=len(partes))

	@staticmethod
	def _informeDeCambios(datos, settings_dict):
		"""Compara lo pedido con lo que quedó en la BIOS y arma el informe hablado."""
		ajustes = datos.get("Settings") or []
		if isinstance(ajustes, dict):
			# PowerShell devuelve un objeto suelto, no una lista, cuando hay uno solo.
			ajustes = [ajustes]

		lineas = []
		todoCorrecto = True
		for ajuste in ajustes:
			nombre = ajuste.get("Name") or "?"
			pedido = ajuste.get("Requested") or ""
			respuesta = (ajuste.get("SetResult") or "").strip()
			actual = ajuste.get("Current")
			if actual is not None and actual == pedido:
				lineas.append(_("{ajuste}: confirmado, {valor}.").format(ajuste=nombre, valor=WmiBackend._valorLegible(pedido)))
			elif respuesta.lower().startswith("success"):
				lineas.append(
					_("{ajuste}: la BIOS aceptó el cambio a {pedido}, pero todavía figura como "
					  "{actual}. Puede que haga falta reiniciar.").format(
						ajuste=nombre, pedido=WmiBackend._valorLegible(pedido),
						actual=WmiBackend._valorLegible(actual))
				)
			else:
				todoCorrecto = False
				motivo = respuesta if respuesta else _("la BIOS no dio ninguna respuesta")
				lineas.append(_("{ajuste}: no se aplicó. Motivo: {motivo}. Sigue en {valor}.").format(ajuste=nombre, motivo=motivo, valor=WmiBackend._valorLegible(actual)))

		nombresInformados = {a.get("Name") for a in ajustes}
		# Un ajuste pedido del que no volvió noticia también es un fallo.
		for nombre in settings_dict:
			if nombre not in nombresInformados:
				todoCorrecto = False
				lineas.append(_("{ajuste}: la BIOS no informó nada sobre este ajuste.").format(ajuste=nombre))

		guardado = (datos.get("SaveResult") or "").strip()
		if not guardado.lower().startswith("success"):
			todoCorrecto = False
			lineas.append(_("Al grabar los cambios en la BIOS: {resultado}.").format(resultado=guardado or _("sin respuesta")))

		return todoCorrecto, "\n".join(lineas)

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
					return True, _("Cambios descartados.")
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
				return True, _("El sistema se reiniciará en la BIOS / UEFI en 2 segundos.")
			else:
				err = res.stderr.strip() or res.stdout.strip()
				log.warning(f"BIOS Manager: Falló shutdown /r /fw: {err}")
				return False, f"No se pudo iniciar el reinicio a UEFI ({err}). Puede requerir ejecutar NVDA como Administrador."
		except Exception as e:
			log.error(f"BIOS Manager: Error ejecutando comando de reinicio a UEFI: {e}", exc_info=True)
			return False, f"Error al ejecutar comando de reinicio: {e}"
