# Calculadora de Honorarios — v12

Calculadora **estática** (una sola página `index.html`) optimizada para **GitHub Pages**.

## Demo (GitHub Pages)
1. Sube `index.html` a un nuevo repositorio.
2. Activa **Settings → Pages → Deploy from a branch → main / (root)**.
3. Tu calculadora quedará accesible públicamente.

## Características principales
- **Responsive** con `meta viewport` y *breakpoints* bien definidos.
- **“Tipo de procedimiento” + “Cuantía”** en la misma línea (desktop); **etiquetas arriba** en pantallas estrechas.
- **Cuantía compacta** (máx. 160px) y 100% en móvil.
- **Botonera** *Monitorios / Declarativos / Desahucios / Ejecuciones / Recursos* distribuida **a todo el ancho** (grid 5→3→2→1).
- Placeholder de **“Otros gastos” = 0,00**.

## Estructura
```
.
├─ index.html        # Aplicación completa (HTML+CSS+JS embebidos)
├─ README.md         # Este archivo
└─ LICENSE           # Licencia MIT
```

## Uso local
Basta con abrir `index.html` en tu navegador (doble clic). No requiere servidor ni dependencias.

## Despliegue en GitHub Pages
```bash
git init
git add index.html README.md LICENSE
git commit -m "Calculadora honorarios v11 (responsive + ajustes)"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
git push -u origin main
```
Luego, en **Settings → Pages**: *Deploy from a branch*, selecciona `main` y el directorio `/ (root)`.

## Personalización rápida
- **Breakpoints** y layout en el bloque `<style id="ajustes-20250924">`:
  - Tabs: `repeat(5, 1fr)` → 3 columnas a ≤1100px → 2 a ≤700px → 1 a ≤420px.
  - Fila superior: etiquetas sobre inputs a ≤980px.
  - `#cuantia`: `max-width: 160px` (ajústalo si necesitas más/menos compacto).
- **Placeholder “Otros gastos”**: atributo `placeholder="0,00"` en `#gastosExtras`.

## Cambios v12 (22/07/2026) — correcciones de cálculo

Auditoría + corrección de la app tras revisión solicitada por Adolfo. Todos los
casos se han verificado con pruebas automatizadas (Playwright) comparando
antes/después, incluida una batería de regresión de 9 escenarios de todos los
tipos de procedimiento que confirma que ningún otro cálculo ha cambiado.

- **[Bug] Recurso de apelación (completo):** la base se calculaba como el 50%
  de la cuantía en bruto (`ctx.cuantia*0.50`) en lugar del 50% de los
  honorarios de primera instancia (`escala*0.50`), como exige el propio art.
  50 y como ya hacía bien la variante "impugnación parcial". Con 30.000 € de
  cuantía esto daba 15.000 € de base en vez de 2.365 € — más de 6 veces el
  importe correcto.
- **[Función rota] Incrementos de Vista (+10%) y Prueba (+10%) del recurso de
  apelación (art. 50.2 y 50.3):** no existía ningún control en la interfaz
  para activarlos y, aunque se hubiera añadido, el código nunca los sumaba.
  Ahora hay dos botones (Vista / Prueba) y dos campos de sesión adicional
  (+150 €/sesión), cada incremento con su propio mínimo de 150 €.
- **[Cobertura incompleta] Allanamiento:** solo contemplaba el momento
  "antes de contestación" (actor 70% / allanado 30%), aplicado siempre sin
  preguntar la fase real. Ahora hay un selector de momento con las 4 fases
  del baremo (antes de contestación, tras contestación, tras audiencia
  previa, tras inicio del juicio), cada una con el % correcto por rol.
- **[Bug] Botón "Actualizar IPC" completamente inoperativo:** un comentario
  mal cerrado (`var ipcGuardado = //localStorage...`) provocaba un error de
  sintaxis que impedía cargar ese bloque de código entero — el botón no
  hacía nada al pulsarlo, sin ningún aviso visible. Corregido; el
  guardado en `localStorage` se mantiene deshabilitado (ya lo estaba).
- **[Bug menor] Error de JavaScript en cualquier clic fuera de un "chip":**
  el manejador global de clics subía por `parentNode` sin detenerse en
  `<html>`, llegando hasta `document` (que no tiene `classList`) y lanzando
  una excepción no controlada en la consola en casi cualquier clic normal
  (selector de tipo de procedimiento, botones de grupo, etc.). No afectaba
  a los importes calculados, pero ensuciaba la consola y podía enmascarar
  otros errores reales. Corregido.
- **Nota (no corregida, pendiente de decisión):** la app no aplica el paso
  de "redondeo a cifra natural" (múltiplo de 50/100) antes de sumar el IVA,
  a diferencia de la práctica real del despacho. Ejemplo: Ordinario 30.000 €
  completo da aquí 7.526,14 € en vez de los 7.562,50 € que resultan de
  redondear 6.219,95 € a 6.250 € antes del IVA. Es una decisión de diseño,
  no un bug — hay que decidir si se automatiza o se deja al criterio manual
  del letrado antes de emitir la minuta.

## Cambios v11
- Placeholder **“Otros gastos” = 0,00**.
- **Alineación** de “Tipo de procedimiento” + **Cuantía** en una sola línea (grid `1fr auto`).
- **Responsividad** mejorada (etiquetas sobre inputs en estrecho, botones fluidos).
- **Botonera** de procesos **a todo el ancho** con **grid** adaptable.
- Añadido **meta viewport**.

## Licencia
Este proyecto se publica bajo licencia **MIT**. Consulta el archivo `LICENSE`.
