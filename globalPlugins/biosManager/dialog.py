import wx
import addonHandler
addonHandler.initTranslation()
import threading
import re
from logHandler import log
import ui

class BiosManagerDialog(wx.Dialog):
	def __init__(self, parent, backend):
		self.backend = backend
		self._all_settings = []
		self._filtered_settings = []
		self._pending_changes = {}
		super().__init__(parent, title=_("Configuración de la BIOS / UEFI"), size=(800, 600))
		
		main_sizer = wx.BoxSizer(wx.VERTICAL)
		self.makeSettings(main_sizer)
		
		# Standard Dialog Buttons
		btn_sizer = wx.StdDialogButtonSizer()
		self.btn_ok = wx.Button(self, wx.ID_OK, label=_("&Aceptar"))
		self.btn_ok.Bind(wx.EVT_BUTTON, self.onSave)
		btn_sizer.AddButton(self.btn_ok)
		
		self.btn_cancel = wx.Button(self, wx.ID_CANCEL, label=_("&Cancelar"))
		self.btn_cancel.Bind(wx.EVT_BUTTON, self.onCancel)
		btn_sizer.AddButton(self.btn_cancel)
		
		btn_sizer.Realize()
		main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)
		
		self.SetSizer(main_sizer)
		self.CenterOnParent()

	def makeSettings(self, settingsSizer):
		# Splitter layout: List on left, Editor on right
		main_hbox = wx.BoxSizer(wx.HORIZONTAL)
		
		# LEFT PANEL (List)
		left_vbox = wx.BoxSizer(wx.VERTICAL)
		
		lbl_search = wx.StaticText(self, label=_("&Buscar ajuste:"))
		left_vbox.Add(lbl_search, 0, wx.BOTTOM, 4)
		
		search_hbox = wx.BoxSizer(wx.HORIZONTAL)
		self.txt_search = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
		self.txt_search.Bind(wx.EVT_TEXT, self._on_search)
		search_hbox.Add(self.txt_search, 1, wx.EXPAND | wx.RIGHT, 5)
		
		btn_clear = wx.Button(self, label=_("L&impiar"))
		btn_clear.Bind(wx.EVT_BUTTON, self._on_clear_search)
		search_hbox.Add(btn_clear, 0, wx.EXPAND)
		
		left_vbox.Add(search_hbox, 0, wx.EXPAND | wx.BOTTOM, 10)
		
		lbl_list = wx.StaticText(self, label=_("&Lista de Ajustes:"))
		left_vbox.Add(lbl_list, 0, wx.BOTTOM, 4)
		
		self.list_ctrl = wx.ListCtrl(
			self,
			style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN
		)
		self.list_ctrl.InsertColumn(0, _("Ajuste"), width=200)
		self.list_ctrl.InsertColumn(1, _("Valor Actual"), width=150)
		self.list_ctrl.InsertColumn(2, _("Pendiente de guardar"), width=140)
		self.list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_item_selected)
		
		# Placeholder temporal
		self.list_ctrl.InsertItem(0, _("Cargando opciones de BIOS..."))
		self.list_ctrl.SetItem(0, 1, _("Por favor, espera..."))
		
		left_vbox.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 0)
		main_hbox.Add(left_vbox, 1, wx.EXPAND | wx.RIGHT, 10)
		
		# RIGHT PANEL (Editor)
		self.right_panel = wx.ScrolledWindow(self, style=wx.VSCROLL)
		self.right_panel.SetScrollRate(0, 20)
		self.right_sizer = wx.BoxSizer(wx.VERTICAL)
		self.right_panel.SetSizer(self.right_sizer)
		
		self._clear_editor()
		main_hbox.Add(self.right_panel, 1, wx.EXPAND | wx.ALL, 0)
		
		settingsSizer.Add(main_hbox, 1, wx.EXPAND | wx.ALL, 5)
		
		# Forzar que el foco inicial vaya a la lista
		self.list_ctrl.SetFocus()
		
		# Load data
		threading.Thread(target=self._load_settings_thread, daemon=True).start()

	def _load_settings_thread(self):
		try:
			settings = self.backend.get_all_settings()
		except Exception as e:
			log.error(f"BIOS Manager: Error leyendo los ajustes de la BIOS: {e}", exc_info=True)
			wx.CallAfter(self._on_unsupported)
			return
		wx.CallAfter(self._on_settings_loaded, settings)

	def _on_unsupported(self):
		"""Avisa y cierra el diálogo cuando no se pudo leer ningún ajuste de la BIOS.

		Ocurre sobre todo si se cancela el aviso de permisos de administrador,
		o si el equipo no tiene una BIOS Lenovo accesible por WMI. Antes de esto
		el diálogo se quedaba con la lista vacía y sin decir nada.
		"""
		log.warning("BIOS Manager: No se obtuvo ningún ajuste de la BIOS. Cerrando el diálogo.")
		ui.message(_(
			"No se pudieron leer los ajustes de la BIOS. "
			"Puede que hayas cancelado el aviso de permisos de administrador, "
			"o que este equipo no sea compatible."
		))
		self.Destroy()

	def _on_settings_loaded(self, settings):
		if not settings:
			self._on_unsupported()
			return
		self._all_settings = settings
		self._apply_filter("")

	def _apply_filter(self, query):
		q = query.strip().lower()
		if not q:
			self._filtered_settings = list(self._all_settings)
		else:
			self._filtered_settings = [
				s for s in self._all_settings
				if q in s["name"].lower()
			]
		self._populate_list()

	def _populate_list(self):
		self.list_ctrl.DeleteAllItems()
		for idx, item in enumerate(self._filtered_settings):
			name = item["name"]
			val = item["value"]
			pending = self._pending_changes.get(name, "")

			if name == self.ORDEN_DE_ARRANQUE:
				# El orden de arranque se muestra distinto en cada columna, para poder
				# distinguirlas: a la izquierda el orden actual numerado, y a la
				# derecha solo lo que se movió.
				val = self._resumenOrden(val)
				if pending:
					pending = self._resumenOrdenPendiente(item["value"], pending)

			self.list_ctrl.InsertItem(idx, name)
			self.list_ctrl.SetItem(idx, 1, val)
			self.list_ctrl.SetItem(idx, 2, pending)
			
		if self.list_ctrl.GetItemCount() > 0:
			self.list_ctrl.Select(0)
			self.list_ctrl.Focus(0)
			
		self._clear_editor()

	def _clear_editor(self):
		self.right_sizer.Clear(True)
		lbl = wx.StaticText(self.right_panel, label=_("Selecciona un ajuste en la lista para editarlo."))
		self.right_sizer.Add(lbl, 0, wx.ALL, 10)
		self.right_panel.Layout()

	def _on_search(self, event):
		self._apply_filter(self.txt_search.GetValue())

	def _on_clear_search(self, event):
		self.txt_search.ChangeValue("")
		self._apply_filter("")
		self.txt_search.SetFocus()

	def _get_focused_setting(self):
		idx = self.list_ctrl.GetFirstSelected()
		if 0 <= idx < len(self._filtered_settings):
			return self._filtered_settings[idx]
		return None

	def _on_item_selected(self, event):
		item = self._get_focused_setting()
		if not item:
			return
		
		name = item["name"]
		val = item["value"]
		
		# Ya tenemos las opciones en caché, así que construimos directamente (sin lag para NVDA)
		opts = self.backend.get_selections(name)
		self._build_editor(name, val, opts)

	def _build_editor(self, name, val, opts):
		self.right_sizer.Clear(True)
		
		pending = self._pending_changes.get(name)
		display_val = pending if pending else val
		
		lbl_title = wx.StaticText(self.right_panel, label=f"{_('Ajuste:')} {name}")
		font = lbl_title.GetFont()
		font.MakeBold()
		lbl_title.SetFont(font)
		self.right_sizer.Add(lbl_title, 0, wx.ALL, 5)
		
		esOrdenDeArranque = (name == self.ORDEN_DE_ARRANQUE)
		textoActual = self._ordenLegible(val) if esOrdenDeArranque else val
		lbl_val = wx.StaticText(self.right_panel, label=f"{_('Valor actual en sistema:')} {textoActual}")
		self.right_sizer.Add(lbl_val, 0, wx.LEFT | wx.BOTTOM, 5)

		if pending:
			if esOrdenDeArranque:
				movidos = self._soloLoQueSeMovio(val, pending)
				textoPendiente = movidos if movidos else self._ordenLegible(pending)
			else:
				textoPendiente = pending
			lbl_pen = wx.StaticText(self.right_panel, label=f"({_('Cambio pendiente:')} {textoPendiente})")
			lbl_pen.SetForegroundColour(wx.Colour(0, 100, 0))
			self.right_sizer.Add(lbl_pen, 0, wx.LEFT | wx.BOTTOM, 5)
			if esOrdenDeArranque:
				lbl_nuevo = wx.StaticText(self.right_panel, label=f"{_('Quedaría así:')} {self._ordenConCambios(val, pending)}")
				self.right_sizer.Add(lbl_nuevo, 0, wx.LEFT | wx.BOTTOM, 5)
		
		self._current_edit_name = name
		self.editor_type = self._tipoDeEditor(name, display_val, opts)

		if self.editor_type == "bootorder_list":
			self._editorDeOrdenDeArranque(display_val)
		elif self.editor_type == "choice":
			self._editorDeOpciones(display_val, opts)
		elif self.editor_type == "date":
			self._editorDeFecha(display_val)
		elif self.editor_type == "time":
			self._editorDeHora(display_val)
		elif self.editor_type == "spin":
			self._editorDeNumero(display_val)
		else:
			self._editorDeTexto(display_val)


		self.btn_apply = wx.Button(self.right_panel, label=_("&Añadir a cambios pendientes"))
		self.btn_apply.Bind(wx.EVT_BUTTON, self._on_apply)
		self.right_sizer.Add(self.btn_apply, 0, wx.ALL | wx.ALIGN_RIGHT, 5)

		self.right_panel.Layout()

	def _tipoDeEditor(self, name, display_val, opts):
		"""Decide que clase de editor pide un ajuste, mirando como es su valor.

		Devuelve una de estas palabras: bootorder_list, choice, date, time, spin o
		text. Antes esta decision estaba mezclada con la construccion de cada
		editor, en una cascada de sesenta lineas.
		"""
		if name == self.ORDEN_DE_ARRANQUE:
			return "bootorder_list"
		if opts and len(opts) > 1:
			return "choice"
		texto = display_val.strip()
		if re.match(r'^\d{4}[/-]\d{2}[/-]\d{2}$', texto):
			return "date"
		if re.match(r'^\d{2}:\d{2}:\d{2}$', texto):
			return "time"
		if texto.isdigit():
			return "spin"
		return "text"

	def _editorDeOrdenDeArranque(self, display_val):
		"""Lista reordenable con los dispositivos de arranque."""
		# El orden de arranque no es "elegir un valor", es reordenar una lista.
		# Antes había un desplegable por posición, cada uno con todos los
		# dispositivos, sin relación entre ellos: se podía repetir uno y perder
		# otro sin que nada avisara. Con una sola lista que solo se reordena,
		# eso no puede pasar.
		self.editor_type = "bootorder_list"
		dispositivos = [d for d in display_val.split(":") if d.strip()]
		self._bootOriginal = list(dispositivos)

		lbl = wx.StaticText(self.right_panel, label=_(
			"&Orden de arranque. Usa Alt más flecha arriba o abajo para mover el dispositivo elegido:"
		))
		self.right_sizer.Add(lbl, 0, wx.TOP | wx.LEFT, 5)

		self.boot_list = wx.ListBox(self.right_panel, choices=dispositivos, style=wx.LB_SINGLE)
		if dispositivos:
			self.boot_list.SetSelection(0)
		self.boot_list.Bind(wx.EVT_KEY_DOWN, self._on_boot_key)
		self.right_sizer.Add(self.boot_list, 1, wx.EXPAND | wx.ALL, 5)

		fila = wx.BoxSizer(wx.HORIZONTAL)
		self.btn_subir = wx.Button(self.right_panel, label=_("S&ubir"))
		self.btn_subir.Bind(wx.EVT_BUTTON, lambda evt: self._moverArranque(-1))
		fila.Add(self.btn_subir, 0, wx.RIGHT, 5)
		self.btn_bajar = wx.Button(self.right_panel, label=_("Ba&jar"))
		self.btn_bajar.Bind(wx.EVT_BUTTON, lambda evt: self._moverArranque(1))
		fila.Add(self.btn_bajar, 0, 0)
		self.right_sizer.Add(fila, 0, wx.ALL, 5)

	def _editorDeOpciones(self, display_val, opts):
		"""Desplegable con los valores que admite el ajuste."""
		lbl = wx.StaticText(self.right_panel, label=_("Elige el nuevo valor:"))
		self.right_sizer.Add(lbl, 0, wx.TOP | wx.LEFT, 5)
		self.ctrl = wx.Choice(self.right_panel, choices=opts)
		if display_val in opts:
			self.ctrl.SetStringSelection(display_val)
		else:
			self.ctrl.SetSelection(0)
		self.right_sizer.Add(self.ctrl, 0, wx.EXPAND | wx.ALL, 5)

	def _editorDeFecha(self, display_val):
		"""Tres casillas numericas: ano, mes y dia."""
		lbl = wx.StaticText(self.right_panel, label=_("Fecha (Año, Mes, Día):"))
		self.right_sizer.Add(lbl, 0, wx.TOP | wx.LEFT, 5)
		parts = re.split(r'[/-]', display_val.strip())
		
		row = wx.BoxSizer(wx.HORIZONTAL)
		self.sp_year = wx.SpinCtrl(self.right_panel, value=parts[0], min=1980, max=2099, size=(60, -1))
		self.sp_month = wx.SpinCtrl(self.right_panel, value=parts[1], min=1, max=12, size=(50, -1))
		self.sp_day = wx.SpinCtrl(self.right_panel, value=parts[2], min=1, max=31, size=(50, -1))
		
		row.Add(self.sp_year, 0, wx.RIGHT, 5)
		row.Add(self.sp_month, 0, wx.RIGHT, 5)
		row.Add(self.sp_day, 0, 0)
		self.right_sizer.Add(row, 0, wx.ALL, 5)

	def _editorDeHora(self, display_val):
		"""Tres casillas numericas: hora, minuto y segundo."""
		lbl = wx.StaticText(self.right_panel, label=_("Hora (Hora, Minuto, Segundo):"))
		self.right_sizer.Add(lbl, 0, wx.TOP | wx.LEFT, 5)
		parts = display_val.strip().split(':')
		
		row = wx.BoxSizer(wx.HORIZONTAL)
		self.sp_h = wx.SpinCtrl(self.right_panel, value=parts[0], min=0, max=23, size=(50, -1))
		self.sp_m = wx.SpinCtrl(self.right_panel, value=parts[1], min=0, max=59, size=(50, -1))
		self.sp_s = wx.SpinCtrl(self.right_panel, value=parts[2], min=0, max=59, size=(50, -1))
		
		row.Add(self.sp_h, 0, wx.RIGHT, 5)
		row.Add(self.sp_m, 0, wx.RIGHT, 5)
		row.Add(self.sp_s, 0, 0)
		self.right_sizer.Add(row, 0, wx.ALL, 5)

	def _editorDeNumero(self, display_val):
		"""Una casilla numerica."""
		lbl = wx.StaticText(self.right_panel, label=_("Valor numérico:"))
		self.right_sizer.Add(lbl, 0, wx.TOP | wx.LEFT, 5)
		self.ctrl = wx.SpinCtrl(self.right_panel, value=display_val.strip(), min=0, max=999999)
		self.right_sizer.Add(self.ctrl, 0, wx.EXPAND | wx.ALL, 5)

	def _editorDeTexto(self, display_val):
		"""Un campo de texto libre, para cuando no encaja nada mas."""
		lbl = wx.StaticText(self.right_panel, label=_("Texto libre:"))
		self.right_sizer.Add(lbl, 0, wx.TOP | wx.LEFT, 5)
		self.ctrl = wx.TextCtrl(self.right_panel, value=display_val)
		self.right_sizer.Add(self.ctrl, 0, wx.EXPAND | wx.ALL, 5)


	ORDEN_DE_ARRANQUE = "BootOrder"

	@staticmethod
	def _ordenLegible(valor):
		"""Convierte 'A:B:C' en '1, A. 2, B. 3, C.', que con lector de pantalla se
		sigue sin perder la cuenta, en vez de seis nombres pegados con dos puntos.
		"""
		partes = [d.strip() for d in valor.split(":") if d.strip()]
		if not partes:
			return valor
		return ". ".join(f"{i + 1}, {d}" for i, d in enumerate(partes)) + "."

	@staticmethod
	def _resumenOrden(valor):
		"""Una línea corta para la lista de ajustes: qué arranca primero y cuántos hay.

		El orden completo se lee en el panel de la derecha; en la fila sería un
		chorizo de seis nombres que hay que escuchar entero cada vez que se pasa por
		encima del ajuste.
		"""
		partes = [d.strip() for d in valor.split(":") if d.strip()]
		if not partes:
			return valor
		if len(partes) == 1:
			return _("Solo {dispositivo}.").format(dispositivo=partes[0])
		return _("Primero {dispositivo}. {total} dispositivos.").format(
			dispositivo=partes[0], total=len(partes),
		)

	@staticmethod
	def _resumenOrdenPendiente(antes, despues):
		"""Lo mismo para la columna de lo pendiente, con palabras que la distinguen.

		Dice "Quedaría", que la columna de la BIOS nunca dice, así que las dos no se
		pueden confundir aunque nombren el mismo dispositivo.
		"""
		a = [d.strip() for d in antes.split(":") if d.strip()]
		b = [d.strip() for d in despues.split(":") if d.strip()]
		if not b:
			return despues
		texto = _("Quedaría primero {dispositivo}.").format(dispositivo=b[0])
		if sorted(a) == sorted(b):
			movidos = sum(1 for d in b if a.index(d) != b.index(d))
			if movidos:
				texto += " " + _("{total} cambian de puesto.").format(total=movidos)
		return texto

	@staticmethod
	def _ordenConCambios(antes, despues):
		"""El orden nuevo, numerado, marcando de dónde venía cada uno que se movió.

		Este es el distintivo: la columna de lo que hay hoy en la BIOS nunca lleva
		esas marcas de "antes", así que las dos columnas no se pueden confundir por
		mucho que tengan los mismos nombres.
		"""
		a = [d.strip() for d in antes.split(":") if d.strip()]
		b = [d.strip() for d in despues.split(":") if d.strip()]
		if not b:
			return despues
		partes = []
		for puesto, dispositivo in enumerate(b, start=1):
			if dispositivo in a and a.index(dispositivo) + 1 != puesto:
				partes.append(_("{puesto}, {dispositivo}, antes {anterior}").format(
					puesto=puesto, dispositivo=dispositivo, anterior=a.index(dispositivo) + 1,
				))
			else:
				partes.append(f"{puesto}, {dispositivo}")
		return ". ".join(partes) + "."

	@staticmethod
	def _soloLoQueSeMovio(antes, despues):
		"""Solo los dispositivos que cambiaron de puesto, para decirlo en voz alta.

		No intenta adivinar qué movimientos hiciste: dice, sin interpretar, cuáles
		quedaron en un puesto distinto y de dónde venían.
		"""
		a = [d.strip() for d in antes.split(":") if d.strip()]
		b = [d.strip() for d in despues.split(":") if d.strip()]
		if not a or sorted(a) != sorted(b):
			return ""
		return ". ".join(
			_("{dispositivo}, ahora {puesto}, antes {anterior}").format(
				dispositivo=d, puesto=b.index(d) + 1, anterior=a.index(d) + 1,
			)
			for d in b if a.index(d) != b.index(d)
		)

	def _on_boot_key(self, event):
		"""Alt+flecha arriba y Alt+flecha abajo mueven el dispositivo elegido."""
		if event.AltDown() and event.GetKeyCode() == wx.WXK_UP:
			self._moverArranque(-1)
		elif event.AltDown() and event.GetKeyCode() == wx.WXK_DOWN:
			self._moverArranque(1)
		else:
			event.Skip()

	def _moverArranque(self, desplazamiento):
		"""Sube o baja un puesto el dispositivo elegido y lo dice en voz alta."""
		try:
			lista = self.boot_list
			origen = lista.GetSelection()
			total = lista.GetCount()
		except (AttributeError, RuntimeError):
			return
		if origen == wx.NOT_FOUND:
			ui.message(_("Elige primero un dispositivo de la lista."))
			return
		destino = origen + desplazamiento
		nombre = lista.GetString(origen)
		if destino < 0 or destino >= total:
			ui.message(_("{dispositivo} ya está {extremo} de la lista.").format(
				dispositivo=nombre,
				extremo=_("al principio") if desplazamiento < 0 else _("al final"),
			))
			return
		lista.Delete(origen)
		lista.Insert(nombre, destino)
		lista.SetSelection(destino)
		lista.SetFocus()
		ui.message(_("{dispositivo}, posición {puesto} de {total}.").format(
			dispositivo=nombre, puesto=destino + 1, total=total,
		))

	def _problemaEnOrdenDeArranque(self, val):
		"""Última red antes de mandarle a la BIOS un orden de arranque estropeado.

		Con la lista de Subir y Bajar no debería fallar nunca, porque solo se
		reordena lo que ya había. Devuelve el texto del problema, o None si está bien.
		"""
		nuevos = [d for d in val.split(":") if d.strip()]
		originales = list(getattr(self, "_bootOriginal", []))
		if not originales or sorted(nuevos) == sorted(originales):
			return None
		repetidos = sorted({d for d in nuevos if nuevos.count(d) > 1})
		faltantes = sorted(set(originales) - set(nuevos))
		detalles = []
		if repetidos:
			detalles.append(_("aparecen dos veces: {}").format(", ".join(repetidos)))
		if faltantes:
			detalles.append(_("faltan: {}").format(", ".join(faltantes)))
		return _(
			"No se puede guardar este orden de arranque porque no coincide con los "
			"dispositivos del equipo ({})."
		).format("; ".join(detalles) or _("la lista quedó distinta"))

	def _valorDelEditor(self):
		"""Devuelve el valor que muestra ahora mismo el editor de la derecha.

		Devuelve None si no hay editor abierto o si sus controles ya se destruyeron
		(pasa cuando se recarga la lista).
		"""
		try:
			if self.editor_type == "choice":
				val = self.ctrl.GetStringSelection()
			elif self.editor_type == "bootorder_list":
				val = ":".join(
					self.boot_list.GetString(i) for i in range(self.boot_list.GetCount())
				)
			elif self.editor_type == "date":
				y = str(self.sp_year.GetValue()).zfill(4)
				m = str(self.sp_month.GetValue()).zfill(2)
				d = str(self.sp_day.GetValue()).zfill(2)
				val = f"{y}/{m}/{d}"
			elif self.editor_type == "time":
				h = str(self.sp_h.GetValue()).zfill(2)
				m = str(self.sp_m.GetValue()).zfill(2)
				s = str(self.sp_s.GetValue()).zfill(2)
				val = f"{h}:{m}:{s}"
			elif self.editor_type == "spin":
				val = str(self.ctrl.GetValue())
			else:
				val = self.ctrl.GetValue().strip()
		except (AttributeError, RuntimeError):
			return None
		return val

	def _cambioSinAnadir(self):
		"""Devuelve (nombre, valor) si el editor abierto tiene un valor distinto al que
		tiene el sistema y que todavía NO se añadió a los cambios pendientes.

		Sirve para no perder en silencio un cambio que se hizo en el desplegable pero
		sin pulsar el botón de añadir.
		"""
		name = getattr(self, "_current_edit_name", None)
		if not name:
			return None
		val = self._valorDelEditor()
		if not val:
			return None
		if self._pending_changes.get(name) == val:
			return None
		valorDelSistema = next((s["value"] for s in self._all_settings if s["name"] == name), None)
		if valorDelSistema is None or val == valorDelSistema:
			return None
		return name, val

	def _on_apply(self, event):
		name = self._current_edit_name
		val = self._valorDelEditor()

		if not val:
			return

		if self.editor_type == "bootorder_list":
			problema = self._problemaEnOrdenDeArranque(val)
			if problema:
				log.warning(f"BIOS Manager: Orden de arranque rechazado: {val}")
				ui.message(problema)
				return

		self._pending_changes[name] = val
		log.info(f"BIOS Manager: Ajuste marcado como pendiente: {name} = '{val}' (Total pendientes: {len(self._pending_changes)})")
		if name == self.ORDEN_DE_ARRANQUE:
			# Leer el orden entero pegado con dos puntos no se entiende. Se dice qué
			# se movió, que es lo que la usuaria acaba de hacer.
			actual = next((a["value"] for a in self._all_settings if a["name"] == name), "")
			movidos = self._soloLoQueSeMovio(actual, val)
			msg = _("Pendiente en el orden de arranque: {cambios}").format(
				cambios=movidos if movidos else self._ordenLegible(val)
			)
		else:
			msg = f"Pendiente: {name} a {val}"
		log.info(f"BIOS Manager: Anunciando al usuario: '{msg}'")
		ui.message(msg)
		
		# Update list
		idx = self.list_ctrl.GetFirstSelected()
		if idx != -1:
			# Escribir aquí el valor crudo se saltaba el formato de la lista y dejaba
			# el orden de arranque pegado con dos puntos.
			if name == self.ORDEN_DE_ARRANQUE:
				actualEnBios = next((a["value"] for a in self._all_settings if a["name"] == name), "")
				textoCelda = self._resumenOrdenPendiente(actualEnBios, val)
			else:
				textoCelda = val
			self.list_ctrl.SetItem(idx, 2, textoCelda)
		
		# Rehacer el editor para que muestre el cambio pendiente. Antes esto llamaba a
		# una función que no existe (_load_options_thread), así que fallaba siempre y
		# nunca se llegaba a devolver el foco a la lista.
		# Se pasa el valor del sistema, no el nuevo: el editor muestra los dos por
		# separado. Las opciones se toman de lo ya leído, para no consultar la BIOS.
		ajuste = next((a for a in self._all_settings if a["name"] == name), None)
		if ajuste is not None:
			self._build_editor(name, ajuste["value"], ajuste.get("options", []))
		self.list_ctrl.SetFocus()

	def onSave(self, event=None):
		if getattr(self, "_guardando", False):
			ui.message(_("Se están aplicando los cambios en la BIOS. Espera a que termine."))
			return

		# Si se cambió el valor en el editor pero no se pulsó "Añadir a cambios
		# pendientes", avisar y NO cerrar: antes ese cambio se descartaba en silencio.
		sinAnadir = self._cambioSinAnadir()
		if sinAnadir:
			name, val = sinAnadir
			log.info(f"BIOS Manager: Aceptar pulsado con un cambio sin añadir: {name} = '{val}'. No se cierra el diálogo.")
			ui.message(_(
				"Has cambiado {ajuste} a {valor}, pero todavía no lo has añadido a los cambios pendientes. "
				"Pulsa el botón Añadir a cambios pendientes, o Cancelar para descartarlo."
			).format(ajuste=name, valor=val))
			try:
				self.btn_apply.SetFocus()
			except (AttributeError, RuntimeError):
				pass
			return

		if not self._pending_changes:
			log.info("BIOS Manager: Diálogo cerrado con Aceptar sin cambios pendientes.")
			ui.message(_("No hay cambios que guardar."))
			self.Destroy()
			return
		
		# Guardar en la BIOS lanza PowerShell con permisos de administrador y después
		# vuelve a leer los ajustes: son varios segundos. Si eso ocurriera aquí mismo,
		# NVDA se quedaría trabado todo ese rato, así que se hace en segundo plano.
		cambios = dict(self._pending_changes)
		log.info(f"BIOS Manager: Guardando {len(cambios)} cambio(s) en BIOS (en segundo plano)...")
		self._guardando = True
		for boton in ("btn_ok", "btn_cancel"):
			try:
				getattr(self, boton).Disable()
			except (AttributeError, RuntimeError):
				pass
		ui.message(_("Aplicando los cambios en la BIOS. Puede tardar unos segundos; te aviso al terminar."))
		threading.Thread(target=self._guardarEnSegundoPlano, args=(cambios,), daemon=True).start()

	def _guardarEnSegundoPlano(self, cambios):
		"""Aplica los cambios sin bloquear NVDA. Corre en un hilo aparte."""
		try:
			ok, msg = self.backend.apply_settings(cambios)
		except Exception as e:
			log.error(f"BIOS Manager: Error inesperado al aplicar los cambios: {e}", exc_info=True)
			ok, msg = False, _("Hubo un error inesperado al aplicar los cambios. Revisa el registro de NVDA.")
		wx.CallAfter(self._alTerminarDeGuardar, ok, msg)

	def _alTerminarDeGuardar(self, ok, msg):
		"""Muestra el resultado y cierra. Vuelve al hilo de la ventana con CallAfter."""
		self._guardando = False
		# El informe trae una línea por ajuste, diciendo si la BIOS lo confirmó o por
		# qué no. Antes este mensaje solo contaba cuántos cambios se habían mandado.
		log.info(f"BIOS Manager: Informe de la BIOS: {msg}")
		if ok:
			wx.MessageBox(msg, _("Cambios aplicados"), wx.OK | wx.ICON_INFORMATION)
		else:
			wx.MessageBox(msg, _("La BIOS no aceptó todos los cambios"), wx.OK | wx.ICON_WARNING)

		self._pending_changes.clear()
		self.Destroy()

	def onCancel(self, event=None):
		if getattr(self, "_guardando", False):
			ui.message(_("Se están aplicando los cambios en la BIOS. Espera a que termine."))
			return
		if self._pending_changes:
			log.info(f"BIOS Manager: Cancelando diálogo y descartando {len(self._pending_changes)} cambio(s) pendientes.")
			# Descartar también habla con PowerShell, así que se lanza y no se espera:
			# el resultado no hace falta y así el diálogo cierra en el acto.
			threading.Thread(target=self._descartarEnSegundoPlano, daemon=True).start()
		else:
			log.info("BIOS Manager: Diálogo cerrado con Cancelar.")
		self.Destroy()

	def _descartarEnSegundoPlano(self):
		"""Le pide a la BIOS que olvide los cambios de la sesión. No bloquea la ventana."""
		try:
			self.backend.discard_settings()
		except Exception as e:
			log.error(f"BIOS Manager: Error al descartar los cambios pendientes: {e}", exc_info=True)
