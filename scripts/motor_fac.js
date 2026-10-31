/*
 * Igual que motor_web.js pero con la copia GENERADA del motor para LexArt (fac-motor.js, window.LEXICALI).
 * Sirve para comprobar que la tercera copia del cálculo da lo mismo que index.html.
 * Uso:  node scripts/motor_fac.js casos.json     (FAC_MOTOR=ruta para otra copia)
 */
const fs = require('fs'), path = require('path'), os = require('os');
const ruta = process.env.FAC_MOTOR || path.join(os.homedir(), 'Programación/LexArt/MAQUETA/dev-facturar/capa/fac-motor.js');
global.window = {};
new Function('window', fs.readFileSync(ruta, 'utf8'))(global.window);
const L = global.window.LEXICALI;
const casos = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const r2 = x => Math.round(x * 100) / 100;
process.stdout.write(JSON.stringify(casos.map(c => {
  const R = L.calcular(c);
  if (R.sinFases) return {sinFases: true};
  return {sinFases: false, nucleo: r2(R.nucleo.total), nucleoCostas: r2(R.nucleoCostas.total),
    totalCliente: r2(R.totalCliente), totalCostas: r2(R.totalCostas), clienteIPC: r2(R.clienteIPC),
    baseCliente: r2(R.baseCliente), costasRed: r2(R.costasRed), lim: r2(R.lim), baseCostas: r2(R.baseCostas),
    muerde: R.muerde, suplidos: r2(R.suplidos), conIvaCliente: r2(R.conIvaCliente), conIvaCostas: r2(R.conIvaCostas),
    ivaCliente: r2(R.ivaCliente), ivaCostas: r2(R.ivaCostas), totalClienteMayoria: (R.totalClienteMayoria == null ? null : r2(R.totalClienteMayoria)),
    preceptiva: R.prec.preceptiva, precDesglose: R.prec.desglose};
})));
