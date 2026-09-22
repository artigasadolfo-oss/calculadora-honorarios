/*
 * Ejecuta el MOTOR PURO de index.html (de «var ESCALA» a «/*@FIN-MOTOR@*\/») en Node, sin DOM,
 * sobre una lista de casos. Cada caso es un ctx como el que devuelve leer() en la página.
 *
 * Uso:  node scripts/motor_web.js casos.json      (o los casos por stdin)
 * Salida: JSON con las cifras de calcularHonorarios() para cada caso.
 */
const fs = require('fs'), path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const i = html.indexOf('var ESCALA'), j = html.indexOf('/*@FIN-MOTOR@*/');
if (i < 0 || j < 0) { console.error('No encuentro el motor en index.html'); process.exit(2); }
const q = () => null;   // el motor no toca el DOM; refreshSubopts() se define pero no se llama
const M = new Function('q', html.slice(i, j) + '\nreturn {calcularHonorarios, computeEscalaBreakdown};')(q);
module.exports = M;
if (require.main === module) {
  const casos = JSON.parse(process.argv[2] ? fs.readFileSync(process.argv[2], 'utf8') : fs.readFileSync(0, 'utf8'));
  const out = casos.map(c => {
    const R = M.calcularHonorarios(c);
    if (R.sinFases) return {sinFases: true};
    const r2 = x => Math.round(x * 100) / 100;
    return {sinFases: false, nucleo: r2(R.nucleo.total), nucleoCostas: r2(R.nucleoCostas.total),
      totalCliente: r2(R.totalCliente), totalCostas: r2(R.totalCostas), clienteIPC: r2(R.clienteIPC),
      baseCliente: r2(R.baseCliente), costasRed: r2(R.costasRed), lim: r2(R.lim), baseCostas: r2(R.baseCostas),
      muerde: R.muerde, suplidos: r2(R.suplidos), conIvaCliente: r2(R.conIvaCliente), conIvaCostas: r2(R.conIvaCostas),
      preceptiva: R.prec.preceptiva};
  });
  process.stdout.write(JSON.stringify(out));
}
