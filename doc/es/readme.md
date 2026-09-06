# BIOS / UEFI Manager para NVDA

* Autora: Daliana
* Versión: 1.5
* Compatibilidad con NVDA: 2023.1 en adelante

Un complemento avanzado para NVDA que permite consultar y modificar la configuración de la BIOS/UEFI de tu ordenador directamente desde Windows.

**El problema que resuelve:** Los menús tradicionales de la BIOS/UEFI se ejecutan antes de que arranque el sistema operativo y son interfaces puramente visuales, lo que los hace 100% inaccesibles para los usuarios de lectores de pantalla. Este complemento derriba esa barrera, trayendo toda la configuración de la BIOS al entorno de Windows, donde NVDA puede leer e interactuar con ella sin problemas.

## ¿Para quién está hecho este complemento? (Compatibilidad)
Manipular la BIOS desde Windows no es algo estándar; depende enteramente de que el fabricante del ordenador exponga las herramientas necesarias.

* **SÍ FUNCIONA EN:** Ordenadores de la marca **Lenovo** de gama profesional (portátiles **ThinkPad**, sobremesas **ThinkCentre**, estaciones **ThinkStation**). El complemento fue programado específicamente para hablar el idioma interno de Lenovo.
* **NO FUNCIONA EN:** Marcas como **HP, Dell, Asus, Acer**, ordenadores portátiles de consumo baratos (algunos IdeaPad genéricos) o PCs de sobremesa armados por piezas (clónicos). Si intentas abrirlo en estos equipos, el complemento simplemente te dirá que no se encontró soporte.
* **¿Se podría hacer que funcione en otras marcas?** **Sí.** Marcas como HP y Dell también tienen sus propios protocolos de comunicación. Este complemento está diseñado de forma modular. Si en un futuro se quiere compartir con más comunidad, se le podrían programar fácilmente traductores extra para añadir soporte completo a otras marcas empresariales.

## Detalles Técnicos y Funcionamiento Interno
Para los usuarios avanzados que quieran saber cómo funciona por debajo:
1. **WMI (Windows Management Instrumentation):** El complemento no interfiere directamente con el hardware a bajo nivel. Utiliza el proveedor oficial de WMI de Lenovo (`root\wmi`).
2. **Lectura y JSON:** Al abrir el complemento, se genera un script temporal en PowerShell que consulta las clases `Lenovo_BiosSetting` y `Lenovo_GetBiosSelections`. Este script extrae toda la topología de la BIOS y la guarda en un archivo JSON temporal comprimido.
3. **Escritura y Seguridad:** Para modificar la configuración, el complemento invoca el método `SetBiosSetting` a través de WMI. Esto interactúa únicamente con la memoria NVRAM de la placa base a través del controlador oficial del fabricante. Cualquier valor malformado es rechazado por la propia placa base, haciendo que sea imposible romper o corromper el firmware por software a través de este método.

## ¿Es seguro utilizarlo?
**Totalmente seguro**. 
* Al utilizar la API oficial de Lenovo y los protocolos WMI de Microsoft, no hay riesgo de corromper la placa base.
* **Sobrevive a los formateos:** Tu configuración está a salvo de instalaciones del sistema operativo. La BIOS vive en un chip físico soldado a la placa base (CMOS/NVRAM), totalmente separado de tu disco duro. Si configuras el arranque por USB aquí, y luego formateas tu disco duro y pones un Windows limpio, la placa base seguirá recordando tu configuración de arranque.

## ¿Por qué tarda unos 15 segundos en cargar al abrirlo?
Al abrir el complemento, escucharás "Cargando opciones de BIOS". **Es normal que tarde.**
Para poder obtener el 100% de las opciones avanzadas reales (muchas de las cuales están bloqueadas para usuarios normales), el complemento lanza su motor de PowerShell de forma invisible pidiendo permisos administrativos en segundo plano. Windows y el motor WMI tardan unos 15 segundos en procesar esta petición de alta seguridad, extraer el árbol completo de la BIOS y devolvérselo a NVDA.

## Cómo usar la Interfaz
La ventana tiene una lista a la izquierda con todos los ajustes de la BIOS (pueden ser hasta 80 distintos), y a la derecha un panel que se adapta dinámicamente:

### 1. Cuadros Combinados (Activación y Desactivación)
Para ajustes estándar (ej. WakeOnLAN, SecureBoot), te aparecerá un cuadro combinado nativo con las opciones disponibles (ej. Enable / Disable) para seleccionar con flechas.

### 2. Orden de Arranque (BootOrder)
Para determinar qué disco arranca primero, verás una **lista dinámica de cuadros combinados**.
El programa generará automáticamente un cuadro para el Dispositivo de arranque 1, otro para el Dispositivo de arranque 2, etc. (tantos como discos o USBs tenga tu PC). Simplemente presiona Tabulador para saltar de uno a otro, y usa las flechas para elegir qué disco va en cada posición.

### 3. Fechas, Horas y Texto Libre
Para contraseñas, etiquetas, o alarmas del sistema, se te presentarán cuadros numéricos (ruedas giratorias) para las fechas, o simples cuadros de edición para escribir texto.

## Guardar y Aplicar los Cambios
Pulsa el botón **Añadir a cambios pendientes** para dejar un cambio en la cola (la lista te marcará cuáles están listos para guardar).
Al terminar, pulsa el botón **Aceptar** de la ventana. Solo en este momento te saltará el Control de Cuentas de Usuario (UAC) de Windows. Al decirle que **Sí**, el complemento inyectará todos tus cambios de golpe en la BIOS. Los cambios tendrán efecto real la próxima vez que reinicies el ordenador.

## Declaración sobre el uso de inteligencia artificial
He utilizado herramientas de inteligencia artificial como ayuda para escribir y ordenar el código de este complemento.
Como autora (**Daliana**), he guiado todo el desarrollo, decidido qué opciones incluir y probado cada una de ellas en mi ordenador Lenovo para asegurarme de que funcione bien, sea accesible con NVDA y no dé errores.

## Uso de servicios y APIs (Criterio 1.6 y Seguridad 2.5)
Este complemento no se conecta a ningún servicio externo en Internet. Todas las consultas se realizan localmente en el equipo mediante las interfaces WMI oficiales provistas por el fabricante (Lenovo) bajo la arquitectura de seguridad del sistema operativo Windows. La elevación de privilegios se solicita únicamente al aplicar cambios confirmados por el usuario mediante el Control de Cuentas de Usuario (UAC).

## Menú en Herramientas de NVDA
Puedes acceder a todas las opciones del complemento desde el menú **NVDA ➔ Herramientas ➔ Gestor de BIOS y UEFI**:
* **Configuración de la BIOS / UEFI...**: Abre la interfaz accesible para consultar y modificar los parámetros del sistema.
* **Comprobar conflictos con otros complementos...**: Realiza una auditoría inmediata sobre posibles colisiones con otros complementos o atajos de teclado.
* **Documentación**: Abre esta guía de usuario.

## Historial de cambios

### Versión 1.5
* **Submenú organizado en Herramientas**: Integración limpia de un único submenú `Gestor de BIOS y UEFI` en el menú Herramientas con todas las funciones del complemento.
* **Auditoría de conflictos**: Detección de complementos de BIOS duplicados y comprobación de colisiones de atajos.
* **Sistema de registro (log) exhaustivo**: Diagnóstico completo en `nvda.log` con parámetros WMI/PowerShell, códigos de retorno y transcripción exacta de cada mensaje anunciado al usuario.
* **Trazas completas de excepciones**: Integración de `exc_info=True` en todas las operaciones del backend.

### Versión 1.4
* Incorporada la declaración formal de uso de inteligencia artificial (Criterio 4.5) y documentación de seguridad WMI (Criterio 1.6).
* Actualizada la compatibilidad probada con NVDA 2026.2.

### Versión 1.3
* Soporte para orden de arranque dinámico y selección por listas combinadas.
