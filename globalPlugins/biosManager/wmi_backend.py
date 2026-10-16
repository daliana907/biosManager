# -*- coding: utf-8 -*-
# biosManager: Complemento para gestionar parámetros de BIOS/UEFI en NVDA
# Copyright (C) 2026 Daliana
# Este archivo está cubierto por la Licencia Pública General de GNU (GPLv2).
# Consulta el archivo LICENSE para más detalles.

import os
import re
import subprocess
import ctypes
import json
import addonHandler
import tempfile
import time
import base64
from typing import List, Dict, Tuple, Optional

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

	# H1: ajustes que nunca se tocan por riesgo de bloqueo (brick / lockout).
	# Solo se comparan nombres, nunca valores.
	DENEGADOS = frozenset({"SecureBoot", "TPM", "PhysicalPresence", "BIOSPassword"})
	# H11: allowlist de nombres de ajuste para evitar inyección en PowerShell.
	_NOMBRE_PERMITIDO = re.compile(r"^[A-Za-z0-9_\- ]{1,64}$")
	# H8: códigos distintos para "se canceló el UAC" frente a "equipo no Lenovo".
	UAC_CANCEL = "UAC_CANCEL"
	UNSUPPORTED = "UNSUPPORTED"
	# Límite conservador de línea de comandos Windows (32767); se usa 30000.
	_MAX_LAUNCHER = 30000


	def __init__(self):
		"""Inicializa la instancia del backend WMI y su caché en memoria para listas de selección."""
		self._selections_cache: Dict[str, List[str]] = {}
		self._last_error: Optional[str] = None

	@staticmethod
	def _borrarTemporalConReintento(path, intentos: int = 5) -> None:
		"""Borra un temporal con reintentos (el elevado/antivirus puede retenerlo brevemente)."""
		if not path:
			return
		for _i in range(max(1, intentos)):
			try:
				if os.path.exists(path):
					os.remove(path)
				return
			except (PermissionError, OSError):
				try:
					time.sleep(0.2)
				except Exception:
					pass
			except Exception:
				return

	@staticmethod
	def _limpiarTemporalesViejos(maxAgeHours: float = 1.0) -> None:
		"""Borra nvda_bios_snapshot_*.json de más de 1 h en el temporal."""
		try:
			tmpdir = tempfile.gettempdir()
			now = time.time()
			try:
				names = os.listdir(tmpdir)
			except Exception:
				return
			for _name in names:
				if not _name.startswith("nvda_bios_snapshot_") or not _name.endswith(".json"):
					continue
				_p = os.path.join(tmpdir, _name)
				try:
					if os.path.islink(_p):
						continue
					if (now - os.path.getmtime(_p)) > (maxAgeHours * 3600.0):
						WmiBackend._borrarTemporalConReintento(_p)
				except Exception:
					continue
		except Exception:
			pass

	@staticmethod
	def _rutaPowerShell() -> str:
		"""H11: ruta absoluta del powershell del sistema para no depender del PATH."""
		try:
			system_root = os.environ.get("SystemRoot", r"C:\Windows") or r"C:\Windows"
			candidata = os.path.join(system_root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
			if os.path.isfile(candidata):
				return candidata
		except Exception:
			pass
		return "powershell.exe"

	@staticmethod
	def _nombreValido(nombre) -> bool:
		"""H11: allowlist para nombres de ajuste."""
		try:
			return bool(WmiBackend._NOMBRE_PERMITIDO.match(str(nombre)))
		except Exception:
			return False

	def _crearFicheroPassword(self, password: str):
		"""H3: guarda la clave en un fichero temporal ACL 600, nunca en argv ni en el script.

		Devuelve la ruta o None si no hay clave. El llamador debe invocar
		_borrarFicheroPassword para zeroizar tras su uso.
		"""
		try:
			clave = str(password or "").replace("\0", "")
		except Exception:
			clave = ""
		if not clave:
			return None
		try:
			fd, ruta = tempfile.mkstemp(prefix="nvda_bios_pwd_", suffix=".tmp")
		except OSError as e:
			log.error(f"BIOS Manager: no se pudo crear el fichero temporal de contraseña: {e}")
			return None
		try:
			try:
				os.fchmod(fd, 0o600)
			except Exception:
				pass
			try:
				if os.name == "nt":
					# ACL 600 aproximada en Windows: solo lectura/escritura del propietario + Admin/SYSTEM.
					subprocess.run(
						["icacls", ruta, "/inheritance:r", "/grant:r", f"{os.environ.get('USERNAME', 'Administrators')}:R", f"{os.environ.get('USERNAME', 'Administrators')}:W"],
						capture_output=True,
						timeout=10,
						creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
					)
			except Exception:
				pass
			os.write(fd, clave.encode("utf-8"))
		finally:
			try:
				os.close(fd)
			except Exception:
				pass
		return ruta

	@staticmethod
	def _borrarFicheroPassword(ruta):
		"""H3: zeroiza (sobrescribe con ceros) y borra el fichero temporal de contraseña."""
		if not ruta:
			return
		try:
			try:
				size = os.path.getsize(ruta)
			except Exception:
				size = 0
			try:
				with open(ruta, "r+b") as f:
					if size > 0:
						f.write(b"\x00" * min(size, 65536))
						f.flush()
						try:
							os.fsync(f.fileno())
						except Exception:
							pass
			except Exception:
				pass
		finally:
			try:
				if os.path.exists(ruta):
					os.remove(ruta)
			except Exception:
				pass
			try:
				os.environ.pop("BIOS_PWD_FILE", None)
			except Exception:
				pass

	def _ejecutarPowerShellElevado(self, ps_script, esperarSalida=False):
		out_file = None
		res = None
		CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
		try:
			# Usamos archivos temporales seguros creados por el SO
			try:
				fd, out_file = tempfile.mkstemp(prefix="nvda_bios_salida_", suffix=".txt")
			except OSError as e:
				log.error(f"BIOS Manager: no se pudo crear el fichero temporal de salida: {e}")
				return False, None
			os.close(fd)
			out_file_esc = out_file.replace("'", "''")
			if esperarSalida:
				final_script = f"& {{\n{ps_script}\n}} | Out-File -FilePath '{out_file_esc}' -Encoding UTF8"
			else:
				final_script = ps_script
				
			# Codificamos el payload para evitar archivos intermedios en disco
			encoded_payload = base64.b64encode(final_script.encode('utf-16le')).decode('ascii')
			ps_exe = self._rutaPowerShell()
			ps_exe_esc = str(ps_exe).replace('"', '""')
			launcher_script = f"""
$proc = new-object System.Diagnostics.Process
$proc.StartInfo.FileName = "{ps_exe_esc}"
$proc.StartInfo.Arguments = "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -EncodedCommand {encoded_payload}"
$proc.StartInfo.Verb = "runas"
$proc.StartInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
$proc.StartInfo.CreateNoWindow = $true
try {{
    if (-not $proc.Start()) {{
        exit 1
    }}
    $proc.WaitForExit()
    exit $proc.ExitCode
}} catch {{
    exit 1
}}
"""
			encoded_launcher = base64.b64encode(launcher_script.encode('utf-16le')).decode('ascii')
			# H5: comprobar longitud antes de lanzar (límite de línea de comandos Windows).
			if len(encoded_launcher) >= self._MAX_LAUNCHER:
				log.error("BIOS Manager: script demasiado largo, se aborta para no truncar la línea de comandos.")
				return False, None
			
			log.info("BIOS Manager: Lanzando PowerShell con permisos de administrador...")
			try:
				res = subprocess.run(
					[ps_exe, "-ExecutionPolicy", "Bypass", "-NoProfile", "-EncodedCommand", encoded_launcher],
					creationflags=CREATE_NO_WINDOW,
					timeout=self.ESPERA_CON_PERMISOS,
				)
			except subprocess.TimeoutExpired:
				log.error("BIOS Manager: se agotó la espera del permiso de administrador (2 minutos).")
				return False, None
			except Exception as e:
				log.error(f"BIOS Manager: Error ejecutando powershell: {e}", exc_info=True)
				return False, None
				
			log.info(f"BIOS Manager: El lanzador terminó con código {res.returncode}.")
			
			salida = None
			if esperarSalida and res is not None and res.returncode == 0:
				salida = self._leerSalida(out_file)
			return res is not None and res.returncode == 0, salida
		finally:
			try:
				if out_file and os.path.exists(out_file):
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
				with open(out_file, "r", encoding="utf-8-sig", errors="replace") as f:
					return f.read()
			except OSError as e:
				log.warning(f"BIOS Manager: Todavía no se puede leer la salida (intento {intento + 1}): {e}")
				time.sleep(espera)
		log.error(f"BIOS Manager: No se pudo leer el archivo de salida {out_file}.")
		return None

	def _obtenerFabricante(self):
		"""H8: consulta el fabricante sin elevar (antes del UAC) para distinguir
		equipo no compatible de UAC cancelado. Devuelve str, "" si vacío o None si no se pudo saber."""
		try:
			ps_exe = self._rutaPowerShell()
			cmd = "(Get-CimInstance -ClassName Win32_ComputerSystem -ErrorAction SilentlyContinue).Manufacturer"
			res = subprocess.run(
				[ps_exe, "-NoProfile", "-Command", cmd],
				capture_output=True, text=True,
				creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
				timeout=self.ESPERA_CONSULTA,
			)
			if res.returncode == 0 and res.stdout and res.stdout.strip():
				return res.stdout.strip()
			return ""
		except Exception as e:
			log.debug(f"BIOS Manager: no se pudo obtener el fabricante: {e}")
			return None

	def get_all_settings(self) -> List[Dict[str, str]]:
		"""Obtiene todos los ajustes de la BIOS (elevado) con logs detallados."""
		self._last_error = None
		# H8: detectar fabricante antes de mostrar el UAC.
		try:
			fab = self._obtenerFabricante()
		except Exception:
			fab = None
		if isinstance(fab, str) and fab and "lenovo" not in fab.lower():
			self._last_error = self.UNSUPPORTED
			log.warning(f"BIOS Manager: equipo no compatible (fabricante: {fab}). No se pedirá elevación.")
			return []
		log.info("Iniciando get_all_settings elevado...")
		ps_script = '''
$settings = Get-CimInstance -Namespace root\\wmi -ClassName Lenovo_BiosSetting -ErrorAction SilentlyContinue
if (-not $settings) {
    $settings = Get-WmiObject -Namespace root\\wmi -Class Lenovo_BiosSetting -ErrorAction SilentlyContinue
}
$selInstance = Get-CimInstance -Namespace root\\wmi -ClassName Lenovo_GetBiosSelections -ErrorAction SilentlyContinue
if (-not $selInstance) {
    $selInstance = Get-WmiObject -Namespace root\\wmi -Class Lenovo_GetBiosSelections -ErrorAction SilentlyContinue
}
$results = @()
foreach ($s in $settings) {
    if ($s.CurrentSetting -match '^(.*?),(.*)$') {
        $name = $matches[1].Trim()
        $val = $matches[2].Trim()
        
        $options = ""
        # Optimización e-sports/senior: para ajustes booleanos (Enable/Disable), las opciones son siempre Enable,Disable.
        # Evitamos saturar el bus SMM del firmware con 150+ llamadas IPC que producían timeout y cierre en Windows 11.
        if ($val -eq 'Enable' -or $val -eq 'Disable') {
            $options = 'Enable,Disable'
        } elseif ($selInstance) {
            try {
                if ($selInstance -is [System.Management.ManagementObject]) {
                    $sel = $selInstance.GetBiosSelections($name)
                    if ($sel -and $sel.Selections) {
                        $options = $sel.Selections
                    }
                } else {
                    $sel = $selInstance | Invoke-CimMethod -MethodName GetBiosSelections -Arguments @{Item=$name} -ErrorAction SilentlyContinue
                    if ($sel -and $sel.Selections) {
                        $options = $sel.Selections
                    }
                }
            } catch {}
        }
        
        $results += [PSCustomObject]@{
            Name = $name
            Value = $val
            Options = $options
        }
    }
}
ConvertTo-Json -InputObject @($results) -Compress
'''
		try:
			ok, salida = self._ejecutarPowerShellElevado(ps_script, esperarSalida=True)
			if not ok or salida is None:
				self._last_error = self.UAC_CANCEL
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

			seen = set()
			results = []
			for item in data:
				if not isinstance(item, dict):
					continue
				opts = item.get("Options", "")
				if isinstance(opts, (list, tuple)):
					opts_list = [str(x).strip() for x in opts if str(x).strip()]
				elif opts:
					opts_list = [x.strip() for x in str(opts).split(",") if x.strip()]
				else:
					opts_list = []
				name = str(item.get("Name") or "").strip()
				val = str(item.get("Value") or "").strip()
				if not name or name in seen:
					continue
				seen.add(name)
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
		# H11: allowlist para el nombre; se rechaza sin llamar a PowerShell.
		if not self._nombreValido(setting_name):
			log.warning(f"BIOS Manager: nombre de ajuste rechazado por allowlist: {setting_name!r}")
			return []
		if setting_name in self._selections_cache:
			return self._selections_cache[setting_name]

		selections = []
		try:
			escaped_name = setting_name.replace("'", "''")
			cmd = (
				f"$s = Get-CimInstance -Namespace root\\wmi -ClassName Lenovo_GetBiosSelections -ErrorAction SilentlyContinue; "
				f"if (-not $s) {{ $s = Get-WmiObject -Namespace root\\wmi -Class Lenovo_GetBiosSelections -ErrorAction SilentlyContinue }}; "
				f"if ($s -is [System.Management.ManagementObject]) {{ ($s.GetBiosSelections('{escaped_name}')).Selections }} "
				f"else {{ ($s | Invoke-CimMethod -MethodName GetBiosSelections -Arguments @{{Item='{escaped_name}'}} -ErrorAction SilentlyContinue).Selections }}"
			)
			res = subprocess.run([self._rutaPowerShell(), "-NoProfile", "-Command", cmd], capture_output=True, text=True,
				creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=self.ESPERA_CONSULTA)
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
		# H11: validar nombres con allowlist; H9: en logs solo nombres, nunca valores.
		nombres = list(settings_dict.keys())
		for _n in nombres:
			if not self._nombreValido(_n):
				log.warning("BIOS Manager: ajuste rechazado por allowlist.")
				# Translators: Mensaje cuando un nombre de ajuste no pasa la validación.
				return False, _("Nombre de ajuste no válido.")
			try:
				_v = str(settings_dict[_n] or "")
			except Exception:
				_v = ""
			if len(_v) > 4096:
				log.warning("BIOS Manager: valor rechazado por exceder 4096 caracteres.")
				# Translators: Mensaje cuando un valor excede la longitud máxima.
				return False, _("Valor demasiado largo (máximo 4096 caracteres).")
		# H1: denegar ajustes críticos que pueden bloquear el equipo.
		_bloqueados = [n for n in nombres if n in self.DENEGADOS or str(n).lower() in {d.lower() for d in self.DENEGADOS}]
		if _bloqueados:
			log.warning(f"BIOS Manager: ajustes denegados por seguridad: {sorted(_bloqueados)}")
			# Translators: Mensaje cuando se intenta cambiar un ajuste bloqueado por seguridad.
			return False, _("Ajuste bloqueado por seguridad: {nombres}. No se aplicó ningún cambio.").format(nombres=", ".join(sorted(_bloqueados)))
		log.info(f"BIOS Manager: apply_settings iniciado para {len(nombres)} ajustes: {sorted(nombres)}")
		try:
			self._limpiarTemporalesViejos(maxAgeHours=1.0)
		except Exception:
			pass
		try:
			_hay_clave = bool(str(password or "").replace("\0", ""))
		except Exception:
			_hay_clave = False
		log.info(f"BIOS Manager: Contraseña de supervisor de BIOS provista: {_hay_clave}")
		# H3: la clave nunca se interpola en el script; va en fichero temporal ACL 600 vía env.
		_ruta_pwd = self._crearFicheroPassword(password)
		if _hay_clave and not _ruta_pwd:
			log.error("BIOS Manager: no se pudo custodiar la contraseña de forma segura.")
			# Translators: Mensaje cuando no se puede custodiar la contraseña de forma segura.
			return False, _("No se pudo custodiar la contraseña de forma segura. No se aplicó ningún cambio.")
		if _ruta_pwd:
			try:
				os.environ["BIOS_PWD_FILE"] = _ruta_pwd
			except Exception:
				pass
		else:
			try:
				os.environ.pop("BIOS_PWD_FILE", None)
			except Exception:
				pass
		# H1: snapshot previo a JSON antes de SaveBiosSettings (solo nombres + fecha, sin valores sensibles en log).
		_snapshot_path = None
		try:
			_fd, _snapshot_path = tempfile.mkstemp(prefix="nvda_bios_snapshot_", suffix=".json")
			try:
				os.fchmod(_fd, 0o600)
			except Exception:
				pass
			with os.fdopen(_fd, "w", encoding="utf-8", errors="replace") as _sf:
				json.dump({"timestamp": int(time.time()), "pending": sorted(nombres)}, _sf)
			log.info(f"BIOS Manager: snapshot previo guardado en {_snapshot_path}")
		except Exception as e:
			log.debug(f"BIOS Manager: no se pudo guardar snapshot previo: {e}")
			_snapshot_path = None
		pendientes = "; ".join(
			f"{self._textoPowerShell(nombre)} = {self._textoPowerShell(str(settings_dict[nombre]).replace(chr(0), ''))}"
			for nombre in nombres
		)
		_snapshot_esc = (str(_snapshot_path).replace("'", "''") if _snapshot_path else "")
		ps_script = r"""
$pendientes = [ordered]@{ %s }
$claveSupervisor = ''
try {
    $pwdFile = $env:BIOS_PWD_FILE
    if ($pwdFile -and (Test-Path $pwdFile)) {
        $claveSupervisor = ([System.IO.File]::ReadAllText($pwdFile)).Trim([char]0).Trim()
    }
} catch {}
$snapshotPath = '%s'
try {
    if ($snapshotPath -ne '') {
        $previos = @{}
        try {
            foreach ($s in Get-CimInstance -Namespace root\wmi -ClassName Lenovo_BiosSetting -ErrorAction Stop) {
                if ($s.CurrentSetting -match '^(.*?),(.*)$') { $previos[$matches[1].Trim()] = $matches[2].Trim() }
            }
        } catch {}
        $soloPedidos = @{}
        foreach ($k in $pendientes.Keys) { if ($previos.ContainsKey($k)) { $soloPedidos[$k] = $previos[$k] } }
        $soloPedidos | ConvertTo-Json -Compress | Out-File -FilePath $snapshotPath -Encoding UTF8
    }
} catch {}
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
""" % (pendientes, _snapshot_esc)

		try:
			ok, salida = self._ejecutarPowerShellElevado(ps_script, esperarSalida=True)
		except Exception as e:
			log.error(f"BIOS Manager: Excepción al ejecutar PowerShell para aplicar ajustes: {e}", exc_info=True)
			try:
				self._borrarTemporalConReintento(_snapshot_path)
			except Exception:
				pass
			# Translators: Mensaje de error cuando ocurre una excepción ejecutando PowerShell.
			return False, _("Error al ejecutar PowerShell para aplicar ajustes: {error}").format(error=e)
		finally:
			# H3: zeroizar la clave siempre, incluso si PowerShell falló.
			try:
				self._borrarFicheroPassword(_ruta_pwd)
			except Exception:
				pass
			_ruta_pwd = None
			# Borrar snapshot tras Save/Discard (éxito o fracaso), con reintento.
			try:
				self._borrarTemporalConReintento(_snapshot_path)
			except Exception:
				pass
			_snapshot_path = None
		if not ok or salida is None:
			log.error("BIOS Manager: No hubo respuesta al aplicar los ajustes o la ejecución falló.")
			# Translators: Mensaje de error cuando no se pudo aplicar ningún cambio a la BIOS.
			return False, _("No se pudo aplicar ningún cambio. Puede que se cancelara el aviso de permisos de administrador.")

		# H9: no volcar valores en el log, solo conteo y longitud.
		try:
			_largo = len(salida.strip())
		except Exception:
			_largo = 0
		log.info(f"BIOS Manager: Respuesta de la BIOS al aplicar recibida ({_largo} caracteres) para {len(nombres)} ajuste(s).")
		try:
			datos = json.loads(salida)
		except ValueError:
			log.error("BIOS Manager: No se pudo interpretar la respuesta de la BIOS.", exc_info=True)
			# Translators: Mensaje de error cuando la respuesta de la BIOS no tiene formato válido.
			return False, _("La BIOS respondió algo que no se pudo interpretar. Mira el registro de NVDA para el detalle.")

		todoCorrecto, informe = self._informeDeCambios(datos, settings_dict)
		# H1: si algo falló, descartar cambios pendientes en firmware para no dejar estado a medias.
		if not todoCorrecto:
			try:
				self.discard_settings()
			except Exception as e:
				log.debug(f"BIOS Manager: DiscardBiosSettings tras fallo no pudo completarse: {e}")
		return todoCorrecto, informe

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
		if not lineas:
			# Translators: Mensaje de confirmación cuando todos los ajustes se aplicaron correctamente.
			lineas.append(_("Todos los cambios se aplicaron y confirmaron con éxito."))

		return todoCorrecto, "\n".join(lineas)

	def discard_settings(self) -> Tuple[bool, str]:
		"""
		Descarta los cambios pendientes de la sesión actual usando PowerShell si hiciera falta.
		"""
		try:
			self._limpiarTemporalesViejos(maxAgeHours=1.0)
		except Exception:
			pass
		try:
			cmd = (
				"$d = Get-CimInstance -Namespace root\\wmi -ClassName Lenovo_DiscardBiosSettings -ErrorAction SilentlyContinue; "
				"if (-not $d) { $d = Get-WmiObject -Namespace root\\wmi -Class Lenovo_DiscardBiosSettings -ErrorAction SilentlyContinue }; "
				"if ($d -is [System.Management.ManagementObject]) { ($d.DiscardBiosSettings('')).return } "
				"else { ($d | Invoke-CimMethod -MethodName DiscardBiosSettings -Arguments @{Parameter=''}).return }"
			)
			res = subprocess.run([WmiBackend._rutaPowerShell(), "-NoProfile", "-Command", cmd], capture_output=True, text=True,
				creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=self.ESPERA_CONSULTA)
			ret_val = res.stdout.strip() if res.returncode == 0 else ""
			err_val = res.stderr.strip() if res.stderr else ""

			if res.returncode != 0 or "access denied" in ret_val.lower() or "access denied" in err_val.lower() or "privilege" in err_val.lower():
				log.info("BIOS Manager: discard_settings estándar falló o requirió permisos. Intentando con elevación...")
				ok_elev, salida_elev = self._ejecutarPowerShellElevado(cmd, esperarSalida=True)
				if ok_elev and salida_elev is not None:
					ret_val = salida_elev.strip()
					res = None

			if (res is None or res.returncode == 0) and ret_val.lower() == "success":
				# Translators: Mensaje cuando se descartan cambios pendientes.
				return True, _("Cambios descartados.")
			elif ret_val:
				# Translators: Mensaje cuando la BIOS devuelve un resultado inesperado al descartar.
				return False, _("La BIOS devolvió: {resultado}").format(resultado=ret_val)
			# Translators: Mensaje de error devuelto por PowerShell al descartar ajustes.
			return False, _("Error de PowerShell: {error}").format(error=err_val)
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
		Usa 'shutdown /r /fw /t 30' sin /f para no forzar el cierre de programas:
		se da margen de 30 s y el usuario puede abortar con 'shutdown /a'.
		"""
		log.info("BIOS Manager: Solicitando reinicio del sistema al firmware UEFI...")
		try:
			log.info("BIOS Manager: Pidiendo permisos de Administrador para reiniciar...")
			# El comando shutdown /fw SIEMPRE requiere privilegios elevados (SeSystemEnvironmentPrivilege).
			# Lanzamos UAC directamente en vez de usar subprocess, que fallaría silenciosamente con Access Denied.
			# H2: sin /f y con /t 30 para permitir guardar trabajo y abortar con shutdown /a.
			ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", "shutdown.exe", "/r /fw /t 30", None, 1)
			if ret > 32:
				log.info("BIOS Manager: Comando shutdown (runas) aceptado por el usuario.")
				# Translators: Mensaje que avisa del reinicio programado a UEFI/BIOS e informa cómo abortarlo.
				return True, _("El sistema se reiniciará en la BIOS / UEFI en 30 segundos. Puedes abortar con shutdown /a.")
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
