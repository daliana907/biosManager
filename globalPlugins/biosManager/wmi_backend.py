# -*- coding: utf-8 -*-
# biosManager: Complemento para gestionar parámetros de BIOS/UEFI en NVDA
# Copyright (C) 2026 Daliana
# Este archivo está cubierto por la Licencia Pública General de GNU (GPLv2).
# Consulta el archivo LICENSE para más detalles.

import os
import subprocess
import ctypes
import logging
import json
import addonHandler
import tempfile
import shutil
import time
from typing import List, Dict, Tuple

addonHandler.initTranslation()

try:
	from logHandler import log
except ImportError:
	import logging
	log = logging.getLogger(__name__)


class WmiBackend:
	"""Clase para interactuar con la BIOS/UEFI mediante WMI."""

	# Cuanto se espera, como maximo, a que Windows conteste. Sin estos limites una
	# consulta que se queda colgada no termina nunca: el aviso de progreso sigue
	# sonando y no se puede volver a intentar.
	ESPERA_CON_PERMISOS = 120   # segundos, incluye el tiempo de aceptar el permiso
	ESPERA_CONSULTA = 30        # segundos, para las consultas normales a la BIOS


	def __init__(self):
		"""Inicializa la instancia del backend WMI y su caché en memoria para listas de selección."""
		self._selections_cache: Dict[str, List[str]] = {}

	def _ejecutarPowerShellElevado(self, ps_script, esperarSalida=False):
		import base64
		# Usamos archivos temporales seguros creados por el SO
		fd, out_file = tempfile.mkstemp(prefix="nvda_bios_salida_", suffix=".txt")
		os.close(fd)
		
		res = None
		try:
			out_file_esc = out_file.replace("'", "''")
			if esperarSalida:
				final_script = ps_script + f"\nOut-File -FilePath '{out_file_esc}' -Encoding UTF8"
			else:
				final_script = ps_script
				
			# Codificamos el payload para evitar archivos intermedios en disco
			encoded_payload = base64.b64encode(final_script.encode('utf-16le')).decode('ascii')
			
			launcher_script = f"""
$proc = new-object System.Diagnostics.Process
$proc.StartInfo.FileName = "powershell.exe"
$proc.StartInfo.Arguments = "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -EncodedCommand {encoded_payload}"
$proc.StartInfo.Verb = "runas"
$proc.StartInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
$proc.StartInfo.CreateNoWindow = $true
$proc.Start() | Out-Null
$proc.WaitForExit()
"""
			encoded_launcher = base64.b64encode(launcher_script.encode('utf-16le')).decode('ascii')
			
			log.info("BIOS Manager: Lanzando PowerShell con permisos de administrador...")
			try:
				res = subprocess.run(
					["powershell", "-ExecutionPolicy", "Bypass", "-NoProfile", "-EncodedCommand", encoded_launcher],
					creationflags=subprocess.CREATE_NO_WINDOW,
					timeout=self.ESPERA_CON_PERMISOS,
				)
			except subprocess.TimeoutExpired:
				log.error("BIOS Manager: se agotó la espera del permiso de administrador (2 minutos).")
				return False, None
				
			log.info(f"BIOS Manager: El lanzador terminó con código {res.returncode}.")
			
			salida = None
			if esperarSalida:
				salida = self._leerSalida(out_file)
			return res.returncode == 0, salida
		finally:
			# Si el proceso fue cancelado o expiró, NO borramos el archivo de salida
			# para evitar un ataque TOCTOU de Symlink LPE. Se deja a cargo de Windows
			# la limpieza de temporales.
			try:
				if os.path.exists(out_file) and res is not None and res.returncode == 0:
					os.remove(out_file)
			except Exception:
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
@($results) | ConvertTo-Json -Compress
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
			if isinstance(data, dict):
				data = [data]
			elif not isinstance(data, list):
				data = []
			log.info(f"BIOS Manager: JSON parseado. {len(data)} ajustes encontrados.")

			results = []
			for item in data:
				if not isinstance(item, dict):
					continue
				opts = item.get("Options", "")
				opts_list = [x.strip() for x in str(opts).split(",") if x.strip()] if opts else []
				name = str(item.get("Name") or "").strip()
				val = str(item.get("Value") or "").strip()
				if not name:
					continue
				results.append({
					"name": name,
					"value": val,
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
			escaped_name = setting_name.replace("'", "''")
			cmd = f"(Get-CimInstance -Namespace root\\wmi -ClassName Lenovo_GetBiosSelections | Invoke-CimMethod -MethodName GetBiosSelections -Arguments @{{Item='{escaped_name}'}}).Selections"
			res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True,
				creationflags=subprocess.CREATE_NO_WINDOW, timeout=self.ESPERA_CONSULTA)
			if res.returncode == 0 and res.stdout.strip():
				selections = [opt.strip() for opt in res.stdout.strip().split(",") if opt.strip()]
		except subprocess.TimeoutExpired:
			# Algunas BIOS no contestan a esta consulta. Sin limite de tiempo, la
			# ventana se quedaba cargando sin fin.
			log.error(f"BIOS Manager: la BIOS no respondió al preguntar las opciones de '{setting_name}'.")
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

	def apply_settings(self, settings_dict: Dict[str, str], password: str = "") -> Tuple[bool, str]:
		"""Aplica varios ajustes, los graba, y comprueba si la BIOS los aceptó.

		Pide los permisos de administrador una sola vez. Dentro de esa misma
		ejecución hace tres cosas: manda cada cambio anotando lo que responde la
		BIOS, graba, y vuelve a leer los ajustes para comparar lo que quedó con lo
		que se pidió.

		Si el equipo tiene puesta una contraseña de supervisor de BIOS, hay que
		pasarla en "password" para poder guardar los cambios (si no, la BIOS
		rechaza todo con "Access Denied", sin decir por qué). Lenovo tiene dos
		formas distintas de recibir esa contraseña según qué tan nuevo sea el
		equipo (2020 en adelante usa un paso de autenticación aparte; los
		modelos anteriores la piden pegada al propio comando). Este método
		prueba primero la forma nueva y, si el equipo no la tiene, cae solo a
		la forma vieja, sin pedir el permiso de administrador dos veces.

		Devuelve (todoCorrecto, informe), donde informe es un texto con una línea
		por ajuste, listo para leerse en voz alta.
		"""
		if not isinstance(settings_dict, dict) or not settings_dict:
			log.info("BIOS Manager: apply_settings invocado sin cambios pendientes.")
			# Translators: Mensaje cuando no hay cambios pendientes que aplicar en la BIOS.
			return True, _("No hay cambios")
		log.info(f"BIOS Manager: apply_settings iniciado para {len(settings_dict)} ajustes: {settings_dict}")
		# No se registra la contraseña en el log, solo si se proporcionó una o no.
		log.info(f"BIOS Manager: Contraseña de supervisor de BIOS provista: {bool(password)}")

		pendientes = "; ".join(
			f"{self._textoPowerShell(nombre)} = {self._textoPowerShell(valor)}"
			for nombre, valor in settings_dict.items()
		)
		clave_ps = self._textoPowerShell(password)
		ps_script = r"""
$pendientes = [ordered]@{ %s }
$claveSupervisor = %s
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

# Si hay contraseña, primero se intenta el mecanismo nuevo (equipos 2020 en
# adelante): un paso de autenticacion aparte que no existe en equipos mas
# viejos, por lo que ahi mismo se descarta con un simple try/catch.
$autenticadoConOpcode = $false
if ($claveSupervisor -ne '') {
    try {
        $op = Get-CimInstance -Namespace root\wmi -ClassName Lenovo_WmiOpcodeInterface -ErrorAction Stop | Invoke-CimMethod -MethodName WmiOpcodeInterface -Arguments @{Parameter="WmiOpcodePasswordAdmin:$claveSupervisor"} -ErrorAction Stop
        $autenticadoConOpcode = $true
    } catch {
        $autenticadoConOpcode = $false
    }
}

$guardado = ''
try {
    if ($claveSupervisor -ne '' -and -not $autenticadoConOpcode) {
        # Mecanismo antiguo: no existe el paso de autenticacion aparte, asi que
        # hay que volver a mandar cada ajuste con la contraseña incluida, y
        # grabar pasando tambien la contraseña.
        foreach ($nombre in $pendientes.Keys) {
            $valor = $pendientes[$nombre]
            try {
                Get-CimInstance -Namespace root\wmi -ClassName Lenovo_SetBiosSetting | Invoke-CimMethod -MethodName SetBiosSetting -Arguments @{Parameter="$nombre,$valor,$claveSupervisor,ascii,us"} -ErrorAction Stop | Out-Null
            } catch {}
        }
        $g = Get-CimInstance -Namespace root\wmi -ClassName Lenovo_SaveBiosSettings | Invoke-CimMethod -MethodName SaveBiosSettings -Arguments @{Parameter="$claveSupervisor,ascii,us"}
    } else {
        $g = Get-CimInstance -Namespace root\wmi -ClassName Lenovo_SaveBiosSettings | Invoke-CimMethod -MethodName SaveBiosSettings -Arguments @{Parameter=''}
    }
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
""" % (pendientes, clave_ps)

		ok, salida = self._ejecutarPowerShellElevado(ps_script, esperarSalida=True)
		if salida is None:
			log.error("BIOS Manager: No hubo respuesta al aplicar los ajustes.")
			# Translators: Mensaje de error cuando no se pudo aplicar ningún cambio a la BIOS.
			return False, _("No se pudo aplicar ningún cambio. Puede que se cancelara el aviso de permisos de administrador.")

		log.info(f"BIOS Manager: Respuesta de la BIOS al aplicar: {salida.strip()[:1000]}")
		try:
			datos = json.loads(salida)
		except ValueError:
			log.error("BIOS Manager: No se pudo interpretar la respuesta de la BIOS.", exc_info=True)
			# Translators: Mensaje de error cuando la respuesta de la BIOS no tiene formato válido.
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
		# Translators: Resumen corto de un orden de arranque con muchos dispositivos.
		return _("primero {dispositivo}, de {total} dispositivos").format(dispositivo=partes[0], total=len(partes))

	@staticmethod
	def _informeDeCambios(datos, settings_dict):
		"""Compara lo pedido con lo que quedó en la BIOS y arma el informe hablado."""
		if not isinstance(datos, dict):
			datos = {}
		ajustes_raw = datos.get("Settings") or []
		if isinstance(ajustes_raw, dict):
			# PowerShell devuelve un objeto suelto, no una lista, cuando hay uno solo.
			ajustes_raw = [ajustes_raw]
		elif not isinstance(ajustes_raw, (list, tuple)):
			ajustes_raw = []
		ajustes = [a for a in ajustes_raw if isinstance(a, dict)]

		lineas = []
		todoCorrecto = True
		for ajuste in ajustes:
			nombre = ajuste.get("Name") or "?"
			pedido = ajuste.get("Requested") or ""
			respuesta_raw = ajuste.get("SetResult")
			respuesta = str(respuesta_raw).strip() if respuesta_raw is not None else ""
			actual = ajuste.get("Current")
			if actual is not None and actual == pedido:
				# Translators: Notificación de confirmación de un ajuste de BIOS aplicado con éxito.
				lineas.append(_("{ajuste}: confirmado, {valor}.").format(ajuste=nombre, valor=WmiBackend._valorLegible(pedido)))
			elif respuesta.lower().startswith("success"):
				# Translators: Notificación cuando un ajuste fue aceptado pero el cambio requiere reinicio.
				lineas.append(
					_("{ajuste}: la BIOS aceptó el cambio a {pedido}, pero todavía figura como "
					  "{actual}. Puede que haga falta reiniciar.").format(
						ajuste=nombre, pedido=WmiBackend._valorLegible(pedido),
						actual=WmiBackend._valorLegible(actual))
				)
			else:
				todoCorrecto = False
				# Translators: Texto por defecto cuando la BIOS no da respuesta sobre un ajuste.
				sinResp = _("la BIOS no dio ninguna respuesta")
				motivo = respuesta if respuesta else sinResp
				if "access denied" in motivo.lower():
					# Translators: Motivo de fallo cuando la BIOS rechaza el cambio por autenticación.
					motivo = _(
						"acceso denegado. El equipo tiene una contraseña de supervisor de BIOS "
						"configurada; escribila en el campo de contraseña de esta ventana e intentá de nuevo."
					)
				# Translators: Notificación cuando un ajuste de BIOS no pudo aplicarse.
				lineas.append(_("{ajuste}: no se aplicó. Motivo: {motivo}. Sigue en {valor}.").format(ajuste=nombre, motivo=motivo, valor=WmiBackend._valorLegible(actual)))

		nombresInformados = {a.get("Name") for a in ajustes if a.get("Name")}
		# Un ajuste pedido del que no volvió noticia también es un fallo.
		for nombre in settings_dict:
			if nombre not in nombresInformados:
				todoCorrecto = False
				# Translators: Notificación cuando la BIOS no devuelve información sobre un ajuste pedido.
				lineas.append(_("{ajuste}: la BIOS no informó nada sobre este ajuste.").format(ajuste=nombre))
		guardado_raw = datos.get("SaveResult")
		guardado = str(guardado_raw).strip() if guardado_raw is not None else ""
		if not guardado.lower().startswith("success"):
			todoCorrecto = False
			# Translators: Texto cuando la BIOS no responde al grabar los cambios.
			sinRespGuardar = _("sin respuesta")
			# Translators: Notificación con el resultado del guardado permanente de ajustes en la BIOS.
			lineas.append(_("Al grabar los cambios en la BIOS: {resultado}.").format(resultado=guardado or sinRespGuardar))

		return todoCorrecto, "\n".join(lineas)

	def discard_settings(self) -> Tuple[bool, str]:
		"""
		Descarta los cambios pendientes de la sesión actual usando PowerShell si hiciera falta.
		"""
		try:
			cmd = "(Get-CimInstance -Namespace root\\wmi -ClassName Lenovo_DiscardBiosSettings | Invoke-CimMethod -MethodName DiscardBiosSettings -Arguments @{Parameter=''}).return"
			res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True,
				creationflags=subprocess.CREATE_NO_WINDOW, timeout=self.ESPERA_CONSULTA)
			if res.returncode == 0:
				ret_val = res.stdout.strip()
				if ret_val.lower() == "success":
					# Translators: Mensaje cuando se descartan cambios pendientes.
					return True, _("Cambios descartados.")
				# Translators: Mensaje cuando la BIOS devuelve un resultado inesperado al descartar.
				return False, _("La BIOS devolvió: {resultado}").format(resultado=ret_val)
			# Translators: Mensaje de error devuelto por PowerShell al descartar ajustes.
			return False, _("Error de PowerShell: {error}").format(error=res.stderr.strip())
		except subprocess.TimeoutExpired:
			log.error("BIOS Manager: la BIOS no respondió al descartar los cambios.")
			# Translators: Mensaje de error cuando la BIOS no responde al descartar cambios.
			return False, _("La BIOS no respondió. Los cambios pueden seguir pendientes.")
		except Exception as e:
			# Translators: Mensaje cuando ocurre una excepción inesperada descartando ajustes.
			return False, _("Excepción: {error}").format(error=e)

	@staticmethod
	def reboot_to_uefi() -> Tuple[bool, str]:
		"""
		Reinicia el equipo directamente a la pantalla de configuración del firmware UEFI.
		Usa 'shutdown /r /fw /f /t 2'. El /f fuerza a cerrar los programas abiertos,
		para que el reinicio no se quede esperando si alguno pide guardar cambios.
		"""
		log.info("BIOS Manager: Solicitando reinicio del sistema al firmware UEFI...")
		try:
			log.info("BIOS Manager: Pidiendo permisos de Administrador para reiniciar...")
			# El comando shutdown /fw SIEMPRE requiere privilegios elevados (SeSystemEnvironmentPrivilege).
			# Lanzamos UAC directamente en vez de usar subprocess, que fallaría silenciosamente con Access Denied.
			ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", "shutdown.exe", "/r /fw /f /t 2", None, 1)
			if ret > 32:
				log.info("BIOS Manager: Comando shutdown (runas) aceptado por el usuario.")
				# Translators: Mensaje que avisa del reinicio inminente del sistema a UEFI/BIOS.
				return True, _("El sistema se reiniciará en la BIOS / UEFI en breve.")
			else:
				log.warning(f"BIOS Manager: Permiso denegado o error al lanzar shutdown (código {ret}).")
				if ret == 5:
					# Translators: Mensaje cuando el usuario cancela el diálogo de permisos de administrador.
					return False, _("Se requiere permiso de administrador para reiniciar en la BIOS.")
				else:
					# Translators: Mensaje genérico cuando ShellExecute falla.
					return False, _("No se pudo iniciar la solicitud de reinicio (código {code}).").format(code=ret)
		except Exception as e:
			log.error(f"BIOS Manager: Error al ejecutar shutdown elevado: {e}", exc_info=True)
			# Translators: Mensaje cuando ocurre una excepción ejecutando el comando de reinicio.
			return False, _("Error al ejecutar comando de reinicio: {error}").format(error=e)
