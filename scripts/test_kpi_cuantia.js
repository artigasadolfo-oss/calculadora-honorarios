/*
 * Verifica en un navegador REAL (Chrome headless) que el input de cuantía del
 * KPI no recorta el número ni queda tapado por el símbolo €.
 *
 * Comprueba, para varios importes:
 *   1. El texto NO se recorta: scrollWidth <= clientWidth del input.
 *   2. El € va DESPUÉS del número y no lo solapa: left del € >= right del texto.
 *   3. El conjunto número + € cabe dentro de la tarjeta.
 *
 * Uso:  node scripts/test_kpi_cuantia.js
 * Requiere: npx puppeteer (se descarga solo la primera vez).
 */
const path = require('path');

const IMPORTES = [
  '0,00', '1000', '1.000,47', '15.000', '150.000,55',
  '1.234.567,89', '12.345.678,90',
];

(async () => {
  let puppeteer;
  try {
    puppeteer = require('puppeteer');
  } catch (e) {
    console.error('Falta puppeteer. Instálalo con:  npm i -D puppeteer');
    process.exit(2);
  }

  const file = 'file://' + path.join(__dirname, '..', 'index.html');
  const browser = await puppeteer.launch({args: ['--no-sandbox']});
  const page = await browser.newPage();
  await page.setViewport({width: 1280, height: 900});
  await page.goto(file, {waitUntil: 'load'});

  let fallos = 0;
  console.log('KPI Cuantía — medición en Chrome real');
  console.log('─'.repeat(92));
  console.log('  importe          fuente  inputW  textoW  €.left  texto.right  recorta  solapa  desborda');

  for (const imp of IMPORTES) {
    const r = await page.evaluate((valor) => {
      const el = document.getElementById('cuantia');
      const wrap = el.parentNode;
      const cur = wrap.querySelector('.cur');
      // Simula tecleo real: dispara los mismos eventos que el usuario
      el.focus();
      el.value = valor;
      el.dispatchEvent(new Event('input', {bubbles: true}));
      el.blur();
      el.dispatchEvent(new Event('blur', {bubbles: true}));

      const cs = getComputedStyle(el);
      /* Ancho REAL del texto según el navegador. NO se usa canvas
         measureText: ignora letter-spacing y kerning y da medidas desviadas
         (se comprobó el 28/08/2026: 154 px frente a 160 px reales). Se mide
         guardando el ancho, poniendo el input a 0 y leyendo su scrollWidth. */
      const wGuardado = el.style.width;
      el.style.width = '0px';
      const textoW = el.scrollWidth;
      el.style.width = wGuardado;

      const rIn = el.getBoundingClientRect();
      const rCur = cur.getBoundingClientRect();
      const rWrap = wrap.getBoundingClientRect();
      return {
        valorFinal: el.value,
        fuente: cs.fontSize,
        inputW: rIn.width,
        textoW,
        scrollW: el.scrollWidth,
        clientW: el.clientWidth,
        curLeft: rCur.left,
        textoRight: rIn.left + textoW,
        wrapRight: rWrap.right,
        curRight: rCur.right,
      };
    }, imp);

    // 1. ¿Se recorta el contenido del input?
    const recorta = r.scrollW > r.clientW + 1;
    // 2. ¿El € pisa al número? Se tolera 1 px de redondeo subpíxel.
    const solapa = r.curLeft < r.textoRight - 1;
    // 3. ¿El conjunto se sale de la tarjeta?
    const desborda = r.curRight > r.wrapRight + 1;

    if (recorta || solapa || desborda) fallos++;
    const m = (b) => (b ? '❌ SÍ' : '✅ no');
    console.log(
      `  ${r.valorFinal.padEnd(16)}${String(r.fuente).padStart(6)}` +
      `${r.inputW.toFixed(0).padStart(8)}${r.textoW.toFixed(0).padStart(8)}` +
      `${r.curLeft.toFixed(0).padStart(8)}${r.textoRight.toFixed(0).padStart(13)}` +
      `   ${m(recorta)}   ${m(solapa)}  ${m(desborda)}`);
  }

  console.log('─'.repeat(92));
  console.log(`  ${IMPORTES.length - fallos}/${IMPORTES.length} importes se muestran correctamente`);

  await browser.close();
  process.exit(fallos ? 1 : 0);
})();
