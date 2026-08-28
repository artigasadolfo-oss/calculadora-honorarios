/*
 * Compara el cálculo del art. 50 (apelación) de index.html con calc_icali.py.
 * Extrae las funciones reales del HTML y las ejecuta en Node, sin duplicar lógica.
 *
 * Uso:  node scripts/test_apelacion_art50.js
 * Salida: tabla de casos y código de salida 1 si alguno diverge.
 */
const fs = require('fs');
const path = require('path');

const HTML = path.join(__dirname, '..', 'index.html');
const html = fs.readFileSync(HTML, 'utf8');

// ── Extraer del HTML solo lo que necesitamos, sin tocar el DOM ──────────────
function bloque(re, nombre) {
  const m = html.match(re);
  if (!m) { console.error(`NO ENCONTRADO en index.html: ${nombre}`); process.exit(2); }
  return m[0];
}

const src = [
  bloque(/var ESCALA\s*=\s*\[[\s\S]*?\];/, 'ESCALA'),
  bloque(/function computeEscalaBreakdown[\s\S]*?\n  }/, 'computeEscalaBreakdown'),
  bloque(/var PROC=\{[\s\S]*?\n  \};/, 'PROC'),
  bloque(/var APEL=\{[\s\S]*?MIN_ORDINARIO:\d+\};/, 'APEL'),
  bloque(/var APEL_VERBALES_ESPECIALES=\{[\s\S]*?\};/, 'APEL_VERBALES_ESPECIALES'),
  bloque(/function honorariosPrimeraInstancia[\s\S]*?\n  }/, 'honorariosPrimeraInstancia'),
  bloque(/function apelacionMinimo[\s\S]*?\n  }/, 'apelacionMinimo'),
].join('\n');

const ctxFns = new Function(src + `
  return {computeEscalaBreakdown, honorariosPrimeraInstancia, apelacionMinimo, APEL, PROC};
`)();

// ── Réplica del flujo de cálculo de la app para apelación ───────────────────
function appApelacion({cuantia, instancia, parcial, vista, prueba, sesVista = 0, sesPrueba = 0,
                       desOposicion = false, reclRentas = false, enerv = false}) {
  const esc = ctxFns.computeEscalaBreakdown(cuantia);
  const ctx = {desOposicion, reclRentas, enerv};
  const h1i = ctxFns.honorariosPrimeraInstancia(instancia, esc.total, ctx).importe;
  let total = h1i * ctxFns.APEL.PCT_TRAM;
  if (vista) {
    total += Math.max(h1i * ctxFns.APEL.PCT_VISTA, ctxFns.APEL.MIN_INCREMENTO);
    total += sesVista * ctxFns.APEL.SESION;
  }
  if (prueba) {
    total += Math.max(h1i * ctxFns.APEL.PCT_PRUEBA, ctxFns.APEL.MIN_INCREMENTO);
    total += sesPrueba * ctxFns.APEL.SESION;
  }
  const min50 = ctxFns.apelacionMinimo(instancia, parcial);
  if (total < min50.valor) total = min50.valor;
  return total;
}

// ── Casos de prueba ─────────────────────────────────────────────────────────
const CASOS = [];
for (const inst of ['ordinario', 'verbal', 'ar_precario', 'ar_fp']) {
  for (const c of [1000, 3000, 8000, 15000, 30000, 60000, 150000]) {
    CASOS.push({cuantia: c, instancia: inst, parcial: false, vista: false, prueba: false});
    CASOS.push({cuantia: c, instancia: inst, parcial: false, vista: true,  prueba: false});
    CASOS.push({cuantia: c, instancia: inst, parcial: false, vista: true,  prueba: true});
  }
}
CASOS.push({cuantia: 30000, instancia: 'ordinario', parcial: false, vista: true, prueba: true, sesVista: 2, sesPrueba: 1});
CASOS.push({cuantia: 20000, instancia: 'ordinario', parcial: true,  vista: false, prueba: false});
CASOS.push({cuantia: 12000, instancia: 'ar_fp', parcial: false, vista: false, prueba: false, desOposicion: true});
CASOS.push({cuantia: 12000, instancia: 'ar_fp', parcial: false, vista: false, prueba: false, reclRentas: true});
CASOS.push({cuantia: 12000, instancia: 'ar_fp', parcial: false, vista: false, prueba: false, enerv: true});

const out = CASOS.map(c => ({...c, app: +appApelacion(c).toFixed(2)}));
fs.writeFileSync(path.join(__dirname, 'casos_app.json'), JSON.stringify(out, null, 1));
console.log(`Generados ${out.length} casos desde index.html -> scripts/casos_app.json`);
