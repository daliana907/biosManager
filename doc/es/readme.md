# Gestor de BIOS y UEFI para NVDA (BIOS / UEFI Manager)

Autora: Daliana
Versión: 1.5
Compatibilidad: NVDA 2023.1 en adelante
Licencia: GNU GPL v2

[Read in English below](#english-version)

---

## Versión en Español

Este complemento permite consultar y modificar la configuración de la BIOS y UEFI de tu ordenador directamente desde el escritorio de Windows con NVDA, de forma totalmente accesible.

### ¿Para qué sirve?
Normalmente, para cambiar algo en la BIOS (como el orden de arranque para formatear con un pendrive o activar la virtualización) hay que reiniciar la computadora y pulsar teclas a ciegas en una pantalla visual que no tiene sonido ni lector de pantalla.

Con este complemento no necesitas ayuda visual: abres la ventana dentro de Windows, buscas la opción que quieras con el teclado, haces el cambio y al reiniciar el ordenador la placa base ya tendrá tu configuración guardada.

### Compatibilidad de computadoras
Por la forma en que funciona la comunicación con la placa base en Windows:
- Funciona en: Equipos Lenovo de gama profesional (portátiles ThinkPad, computadoras de escritorio ThinkCentre y estaciones de trabajo ThinkStation).
- No funciona en: Equipos armados por piezas (clónicos) o computadoras portátiles domésticas que no traen el sistema de comunicación WMI del fabricante. Si lo abres en un equipo no compatible, simplemente te avisará de que no se encontró soporte.

### ¿Es seguro cambiar cosas aquí?
Sí, es totalmente seguro:
- El complemento no toca el chip de la placa base directamente, sino que se comunica con el sistema oficial de Lenovo (WMI).
- Si un valor no es válido, la propia placa base lo rechaza automáticamente, impidiendo que el equipo se desconfigure.
- Los cambios quedan guardados en la memoria física de la placa base (NVRAM/CMOS). Esto significa que aunque formatees el disco duro, la configuración de la BIOS seguirá guardada.
- Windows solo pedirá permisos de administrador (la pantalla de Control de cuentas de usuario) cuando le des al botón Guardar para aplicar los cambios que hayas elegido.

### Cómo se usa
1. Ve al menú de NVDA con NVDA + N, baja a Herramientas, entra a Gestor de BIOS y UEFI y pulsa en Configuración de la BIOS / UEFI (o presiona directamente el atajo NVDA + Shift + B).
2. A la izquierda verás la lista con todas las opciones disponibles de tu máquina. Puedes escribir en el cuadro de búsqueda para encontrar una rápido.
3. A la derecha verás el valor actual. Si es una opción de Sí/No (como Secure Boot), podrás cambiarlo con las flechas en una lista desplegable. Si es el orden de arranque, tendrás listas para elegir qué disco va primero, segundo, etc.
4. Pulsa en Añadir a cambios pendientes.
5. Cuando termines, dale al botón Aceptar, confirma el aviso de Windows y listo. Los cambios se aplicarán la próxima vez que reinicies el equipo.

---