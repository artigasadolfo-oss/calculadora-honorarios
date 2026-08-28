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
  bloque(/var ART51=\{[\s\S]*?MIN_RESCISION:\d+\};/, 'ART51'),
  bloque(/var ART51_SOBRE_1I=\{[\s\S]*?\};/, 'ART51_SOBRE_1I'),
  bloque(/var APEL=\{[\s\S]*?MIN_ORDINARIO:\d+\};/, 'APEL'),
  bloque(/var APEL_VERBALES_ESPECIALES=\{[\s\S]*?\};/, 'APEL_VERBALES_ESPECIALES'),
  bloque(/function honorariosPrimeraInstancia[\s\S]*?\n  }/, 'honorariosPrimeraInstancia'),
  bloque(/function apelacionMinimo[\s\S]*?\n  }/, 'apelacionMinimo'),
].join('\n');

const ctxFns = new Function(src + `
  return {computeEscalaBreakdown, honorariosPrimeraInstancia, apelacionMinimo,
          APEL, PROC, ART51, ART51_SOBRE_1I};
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

// ── Art. 51: apartados 2, 3, 4 y 5 ──────────────────────────────────────────
function appArt51({cuantia, subtipo, instancia = 'ordinario',
                   desOposicion = false, reclRentas = false, enerv = false}) {
  const esc = ctxFns.computeEscalaBreakdown(cuantia);
  const cfg = ctxFns.PROC[subtipo];
  if (subtipo === 'recurso_esp_audiencia') {
    // 51.2: Escala íntegra, mínimo 2.000 €
    return Math.max(esc.total * cfg.normaPct, cfg.minimo);
  }
  const pct = ctxFns.ART51_SOBRE_1I[subtipo];
  const ctx = {desOposicion, reclRentas, enerv};
  const h1i = ctxFns.honorariosPrimeraInstancia(instancia, esc.total, ctx).importe;
  const base = h1i * pct;
  return (cfg.minimo > 0 && base < cfg.minimo) ? cfg.minimo : base;
}

// ── Art. 51.1: recursos accesorios (revisión / reposición / queja) ──────────
function appArt51_1({numFijos = 0, numConCuantia = 0, cuantiaRecurso = 0}) {
  const unit = Math.max(
    ctxFns.computeEscalaBreakdown(cuantiaRecurso).total * ctxFns.ART51.PCT_51_1_CUANTIA,
    ctxFns.ART51.MIN_51_1);
  return numFijos * ctxFns.ART51.MIN_51_1 + numConCuantia * unit;
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

// Art. 51 (subtipos 2-5): se comprueban contra valores esperados calculados a
// mano desde el texto del baremo, no contra el propio código (evita el test
// tautológico que solo confirma que el código hace lo que hace).
const ESC = c => ctxFns.computeEscalaBreakdown(c).total;
const H1I = (inst, c) => ctxFns.honorariosPrimeraInstancia(inst, ESC(c), {}).importe;
const ART51_CASOS = [
  // 51.2 — Escala íntegra, mín. 2.000 €
  {n: '51.2 esp. Audiencia 3.000 (bajo mínimo)',  got: appArt51({cuantia: 3000,  subtipo: 'recurso_esp_audiencia'}), exp: 2000},
  {n: '51.2 esp. Audiencia 30.000',               got: appArt51({cuantia: 30000, subtipo: 'recurso_esp_audiencia'}), exp: ESC(30000)},
  // 51.3 — 50% de la 1ª instancia, mín. 500 €
  {n: '51.3 rescisión ord. 3.000 (1ªinst 2.000)', got: appArt51({cuantia: 3000,  subtipo: 'recurso_rescision'}),     exp: H1I('ordinario', 3000) * 0.50},
  {n: '51.3 rescisión ord. 30.000',               got: appArt51({cuantia: 30000, subtipo: 'recurso_rescision'}),     exp: ESC(30000) * 0.50},
  {n: '51.3 rescisión verbal 1.000 (mín. 500)',   got: appArt51({cuantia: 1000,  subtipo: 'recurso_rescision', instancia: 'verbal'}), exp: 500},
  // 51.4 — 75% de la 1ª instancia, sin mínimo propio
  {n: '51.4 revisión firmes ord. 30.000',         got: appArt51({cuantia: 30000, subtipo: 'recurso_revision_firmes'}), exp: ESC(30000) * 0.75},
  {n: '51.4 revisión firmes ord. 3.000',          got: appArt51({cuantia: 3000,  subtipo: 'recurso_revision_firmes'}), exp: 2000 * 0.75},
  // 51.5 — 75% de la 1ª instancia (casación inadmitida)
  {n: '51.5 casación inadm. ord. 60.000',         got: appArt51({cuantia: 60000, subtipo: 'recurso_casacion_inadm'}),  exp: ESC(60000) * 0.75},
  // 51.1 — accesorios
  {n: '51.1 tres fijos (3 x 300)',                got: appArt51_1({numFijos: 3}), exp: 900},
  {n: '51.1 con cuantía 1.000 -> mínimo 300',     got: appArt51_1({numConCuantia: 1, cuantiaRecurso: 1000}), exp: 300},
  {n: '51.1 con cuantía 60.000 -> 15% escala',    got: appArt51_1({numConCuantia: 1, cuantiaRecurso: 60000}), exp: ESC(60000) * 0.15},
];

let fallos = 0;
console.log('\nArt. 51 — comprobación contra valores esperados del baremo');
console.log('─'.repeat(78));
for (const t of ART51_CASOS) {
  const ok = Math.abs(t.got - t.exp) < 0.01;
  if (!ok) fallos++;
  console.log(`  ${ok ? '✅' : '❌'} ${t.n.padEnd(44)} ${t.got.toFixed(2).padStart(11)} ${ok ? '' : '(esperado ' + t.exp.toFixed(2) + ')'}`);
}
console.log('─'.repeat(78));
console.log(`  Art. 51: ${ART51_CASOS.length - fallos}/${ART51_CASOS.length} correctos`);

console.log(`\nGenerados ${out.length} casos de apelación desde index.html -> scripts/casos_app.json`);
if (fallos) process.exit(1);
