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
		super().__init__(parent, title="Configuración de la BIOS / UEFI", size=(800, 600))
		
		main_sizer = wx.BoxSizer(wx.VERTICAL)
		self.makeSettings(main_sizer)
		
		# Standard Dialog Buttons
		btn_sizer = wx.StdDialogButtonSizer()
		self.btn_ok = wx.Button(self, wx.ID_OK, label="&Aceptar")
		self.btn_ok.Bind(wx.EVT_BUTTON, self.onSave)
		btn_sizer.AddButton(self.btn_ok)
		
		self.btn_cancel = wx.Button(self, wx.ID_CANCEL, label="&Cancelar")
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
		
		btn_clear = wx.Button(self, label="L&impiar")
		btn_clear.Bind(wx.EVT_BUTTON, self._on_clear_search)
		search_hbox.Add(btn_clear, 0, wx.EXPAND)
		
		left_vbox.Add(search_hbox, 0, wx.EXPAND | wx.BOTTOM, 10)
		
		lbl_list = wx.StaticText(self, label="&Lista de Ajustes:")
		left_vbox.Add(lbl_list, 0, wx.BOTTOM, 4)
		
		self.list_ctrl = wx.ListCtrl(
			self,
			style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN
		)
		self.list_ctrl.InsertColumn(0, "Ajuste", width=200)
		self.list_ctrl.InsertColumn(1, "Valor Actual", width=150)
		self.list_ctrl.InsertColumn(2, "Pendiente de guardar", width=140)
		self.list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_item_selected)
		
		# Placeholder temporal
		self.list_ctrl.InsertItem(0, "Cargando opciones de BIOS...")
		self.list_ctrl.SetItem(0, 1, "Por favor, espera...")
		
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
			wx.CallAfter(self._on_settings_loaded, settings)
		except Exception as e:
			log.error(f"Error loading settings: {e}")

	def _on_unsupported(self):
		ui.message("No se encontró soporte de WMI BIOS.")
		self.Destroy()
		
	def _on_settings_loaded(self, settings):
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
			
			self.list_ctrl.InsertItem(idx, name)
			self.list_ctrl.SetItem(idx, 1, val)
			self.list_ctrl.SetItem(idx, 2, pending)
			
		if self.list_ctrl.GetItemCount() > 0:
			self.list_ctrl.Select(0)
			self.list_ctrl.Focus(0)
			
		self._clear_editor()

	def _clear_editor(self):
		self.right_sizer.Clear(True)
		lbl = wx.StaticText(self.right_panel, label="Selecciona un ajuste en la lista para editarlo.")
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
		
		lbl_val = wx.StaticText(self.right_panel, label=f"{_('Valor actual en sistema:')} {val}")
		self.right_sizer.Add(lbl_val, 0, wx.LEFT | wx.BOTTOM, 5)
		
		if pending:
			lbl_pen = wx.StaticText(self.right_panel, label=f"({_('Cambio pendiente:')} {pending})")
			lbl_pen.SetForegroundColour(wx.Colour(0, 100, 0))
			self.right_sizer.Add(lbl_pen, 0, wx.LEFT | wx.BOTTOM, 5)
		
		self.editor_type = "text"
		self._current_edit_name = name
			
		if name == "BootOrder":
			self.editor_type = "bootorder_combos"
			devices = display_val.split(":")
			choices = opts if (opts and len(opts) > 0) else devices
			self.boot_combos = []
			
			for i, dev in enumerate(devices):
				lbl = wx.StaticText(self.right_panel, label=f"{_('Dispositivo de arranque')} {i+1}:")
				self.right_sizer.Add(lbl, 0, wx.TOP | wx.LEFT, 5)
				
				combo = wx.Choice(self.right_panel, choices=choices)
				if dev in choices:
					combo.SetStringSelection(dev)
				else:
					combo.Append(dev)
					combo.SetStringSelection(dev)
					
				self.right_sizer.Add(combo, 0, wx.EXPAND | wx.ALL, 5)
				self.boot_combos.append(combo)
		elif opts and len(opts) > 1:
			self.editor_type = "choice"
			lbl = wx.StaticText(self.right_panel, label=_("Elige el nuevo valor:"))
			self.right_sizer.Add(lbl, 0, wx.TOP | wx.LEFT, 5)
			self.ctrl = wx.Choice(self.right_panel, choices=opts)
			if display_val in opts:
				self.ctrl.SetStringSelection(display_val)
			else:
				self.ctrl.SetSelection(0)
			self.right_sizer.Add(self.ctrl, 0, wx.EXPAND | wx.ALL, 5)
		else:
			if re.match(r'^\d{4}[/-]\d{2}[/-]\d{2}$', display_val.strip()):
				self.editor_type = "date"
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
			elif re.match(r'^\d{2}:\d{2}:\d{2}$', display_val.strip()):
				self.editor_type = "time"
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
			elif display_val.strip().isdigit():
				self.editor_type = "spin"
				lbl = wx.StaticText(self.right_panel, label=_("Valor numérico:"))
				self.right_sizer.Add(lbl, 0, wx.TOP | wx.LEFT, 5)
				self.ctrl = wx.SpinCtrl(self.right_panel, value=display_val.strip(), min=0, max=999999)
				self.right_sizer.Add(self.ctrl, 0, wx.EXPAND | wx.ALL, 5)
			else:
				self.editor_type = "text"
				lbl = wx.StaticText(self.right_panel, label=_("Texto libre:"))
				self.right_sizer.Add(lbl, 0, wx.TOP | wx.LEFT, 5)
				self.ctrl = wx.TextCtrl(self.right_panel, value=display_val)
				self.right_sizer.Add(self.ctrl, 0, wx.EXPAND | wx.ALL, 5)

		self.btn_apply = wx.Button(self.right_panel, label=_("&Añadir a cambios pendientes"))
		self.btn_apply.Bind(wx.EVT_BUTTON, self._on_apply)
		self.right_sizer.Add(self.btn_apply, 0, wx.ALL | wx.ALIGN_RIGHT, 5)

		self.right_panel.Layout()

	def _on_apply(self, event):
		name = self._current_edit_name
		
		if self.editor_type == "choice":
			val = self.ctrl.GetStringSelection()
		elif self.editor_type == "bootorder_combos":
			selected_devices = []
			for combo in self.boot_combos:
				selected_devices.append(combo.GetStringSelection())
			val = ":".join(selected_devices)
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

		if not val:
			return

		self._pending_changes[name] = val
		log.info(f"BIOS Manager: Ajuste marcado como pendiente: {name} = '{val}' (Total pendientes: {len(self._pending_changes)})")
		msg = f"Pendiente: {name} a {val}"
		log.info(f"BIOS Manager: Anunciando al usuario: '{msg}'")
		ui.message(msg)
		
		# Update list
		idx = self.list_ctrl.GetFirstSelected()
		if idx != -1:
			self.list_ctrl.SetItem(idx, 2, val)
		
		# Refresh UI to show the green text
		threading.Thread(target=self._load_options_thread, args=(name, val), daemon=True).start()
		self.list_ctrl.SetFocus()

	def onSave(self, event=None):
		if not self._pending_changes:
			log.info("BIOS Manager: Diálogo cerrado con Aceptar sin cambios pendientes.")
			self.Destroy()
			return
		
		log.info(f"BIOS Manager: Guardando {len(self._pending_changes)} cambio(s) en BIOS...")
		ok, msg = self.backend.apply_settings(self._pending_changes)
		
		if ok:
			wx.MessageBox(f"Se han guardado {len(self._pending_changes)} cambios en la BIOS. Reinicia para aplicarlos.", _("Éxito"), wx.OK | wx.ICON_INFORMATION)
		else:
			wx.MessageBox(f"Hubo un error al guardar: {msg}", _("Error"), wx.OK | wx.ICON_ERROR)
			
		self._pending_changes.clear()
		self.Destroy()

	def onCancel(self, event=None):
		if self._pending_changes:
			log.info(f"BIOS Manager: Cancelando diálogo y descartando {len(self._pending_changes)} cambio(s) pendientes.")
			self.backend.discard_settings()
		else:
			log.info("BIOS Manager: Diálogo cerrado con Cancelar.")
		self.Destroy()
