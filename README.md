# Calculadora de Honorarios — v11

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

## Cambios v11
- Placeholder **“Otros gastos” = 0,00**.
- **Alineación** de “Tipo de procedimiento” + **Cuantía** en una sola línea (grid `1fr auto`).
- **Responsividad** mejorada (etiquetas sobre inputs en estrecho, botones fluidos).
- **Botonera** de procesos **a todo el ancho** con **grid** adaptable.
- Añadido **meta viewport**.

## Licencia
Este proyecto se publica bajo licencia **MIT**. Consulta el archivo `LICENSE`.
