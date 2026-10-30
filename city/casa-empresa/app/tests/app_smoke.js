// Prueba de humo de la app: nacer, aprender, recargar, laboratorio y final de vida.
// Uso: NODE_PATH=$(npm root -g) node app/tests/app_smoke.js   (requiere Playwright y Chromium)
const { chromium } = require('playwright');
const path = require('path');
const APP = 'file://' + path.resolve(__dirname, '..', 'index.html');
let fallos = 0;
function ok(cond, msg) { console.log((cond ? 'OK   ' : 'FALLO') + ' ' + msg); if (!cond) fallos++; }
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 844 } });
  const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto(APP + '?speed=3&hora=15');
  await p.fill('#nombreIntro', 'Prueba');
  await p.click('#btnNacer');
  await p.waitForTimeout(400);
  const rasgos = await p.evaluate(() => __mosquita.A.rasgos);
  ok(rasgos && rasgos.kcPorcentaje > 1 && rasgos.kcPorcentaje < 10, 'rasgos medidos: KC activas ' + (rasgos && rasgos.kcPorcentaje) + ' %');
  // laboratorio bloqueado por defecto
  ok(await p.evaluate(() => document.querySelector('#lab').classList.contains('bloqueado')), 'laboratorio bloqueado al nacer');
  ok(await p.isHidden('#btnLabOff'), 'boton ocultar laboratorio oculto mientras esta bloqueado');
  await p.click('#btnLab');
  ok(await p.evaluate(() => !document.querySelector('#lab').classList.contains('bloqueado')), 'laboratorio se desbloquea (demo)');
  // aprendizaje con un par: azucar + plátano
  await p.evaluate(() => { const M = __mosquita; M.setFuentes([{tipo:'olor', o:'menta', x:0.5, y:0.5, fuerza:1, vida:110000, vidaMax:110000}]); });
  await p.waitForTimeout(1500);
  const w1 = await p.evaluate(() => Array.from(__mosquita.cer.W).join(','));
  await p.evaluate(() => __mosquita.recompensa('azucar'));
  const w2 = await p.evaluate(() => Array.from(__mosquita.cer.W).join(','));
  ok(w1 !== w2, 'la recompensa cambia los pesos');
  await p.waitForTimeout(4500); // deja que guarde
  const antesRecarga = await p.evaluate(() => ({ nombre: __mosquita.A.nombre, seed: __mosquita.A.seed, edad: __mosquita.A.edadMs, pares: JSON.stringify(__mosquita.A.pares) }));
  await p.reload();
  await p.waitForTimeout(400);
  const despues = await p.evaluate(() => ({ nombre: __mosquita.A.nombre, seed: __mosquita.A.seed, edad: __mosquita.A.edadMs, pares: JSON.stringify(__mosquita.A.pares) }));
  ok(antesRecarga.nombre === despues.nombre && antesRecarga.seed === despues.seed, 'nombre y semilla persisten tras recargar');
  ok(despues.edad >= antesRecarga.edad, 'la edad avanza (tiempo fuera contado)');
  ok(antesRecarga.pares === despues.pares, 'los pares aprendidos persisten');
  // final de vida
  await p.evaluate(() => { __mosquita.A.edadMs = 45 * 86400000 + 1; });
  await p.waitForTimeout(300);
  ok(await p.isVisible('#fin'), 'al cumplir 45 dias aparece el final de vida');
  const txtFin = await p.textContent('#finTxt');
  ok(txtFin.indexOf('Prueba') >= 0, 'el final menciona su nombre');
  // cableado: estadisticas del conectoma (casa-conectoma/out/audit.json)
  const est = await p.evaluate(() => window.__mosquita.estadisticasCableado(4242));
  ok(est.mediana === 6 && est.p10 === 4 && est.p90 === 9, 'PN por KC: mediana 6, p10 4, p90 9 (audit.json)');
  ok(est.media > 5.7 && est.media < 6.1, 'PN por KC: media ' + est.media.toFixed(2) + ' (audit 5,92)');
  ok(est.frac4a8 > 0.75 && est.frac4a8 < 0.85, 'KC con 4-8 PN: ' + (est.frac4a8 * 100).toFixed(1) + ' % (audit 80,4 %)');
  ok(est.fracMenos4 > 0.05 && est.fracMenos4 < 0.15, 'KC con menos de 4 PN: ' + (est.fracMenos4 * 100).toFixed(1) + ' % (audit ~9,6 %)');
  ok(est.sinapsisMediana === 16 && est.sinapsisP10 === 4 && est.sinapsisP90 > 28 && est.sinapsisP90 < 36, 'sinapsis por arista: mediana 16, p10 4, p90 ' + est.sinapsisP90 + ' (audit 31)');
  // premio junto a un olor: cuenta como par y mueve la valencia del olor
  const pares0 = await p.evaluate(() => __mosquita.A.pares.menta || 0);
  await p.evaluate(() => { const M = __mosquita; M.setFuentes([]); M.F.enfriar = 1e12; M.F.olfato = null; });
  const v0 = await p.evaluate(() => { const M = __mosquita; M.setFuentes([{tipo:'olor', o:'menta', x:M.F.x, y:M.F.y, fuerza:1, vida:110000, vidaMax:110000}]); M.iniciaOlfateo('menta', {platano:0,levadura:0,vinagre:0,menta:1}); M.tickMosca(1300); return M.F.ultimoV.menta; });
  for (let i = 0; i < 3; i++) await p.evaluate(() => { const M = __mosquita; M.setFuentes([{tipo:'olor', o:'menta', x:M.F.x, y:M.F.y, fuerza:1, vida:110000, vidaMax:110000}]); M.iniciaOlfateo('menta', {platano:0,levadura:0,vinagre:0,menta:1}); M.tickMosca(1300); M.recompensa('azucar'); });
  const pm = await p.evaluate(() => __mosquita.A.pares.menta || 0);
  const v1 = await p.evaluate(() => { const M = __mosquita; M.setFuentes([{tipo:'olor', o:'menta', x:M.F.x, y:M.F.y, fuerza:1, vida:110000, vidaMax:110000}]); M.iniciaOlfateo('menta', {platano:0,levadura:0,vinagre:0,menta:1}); M.tickMosca(1300); return M.F.ultimoV.menta; });
  ok(pm - pares0 === 3, 'tres premios junto a la menta cuentan como tres pares (+' + (pm - pares0) + ')');
  ok(v1 > v0 + 0.3, 'la menta pasa de evitada a apetecible tras los pares (' + v0.toFixed(2) + ' -> ' + v1.toFixed(2) + ')');
  // linaje: la hija nace de la madre, con cableado heredado y sin recuerdos
  await p.fill('#nombreHija', 'Hija');
  await p.click('#btnHija');
  await p.waitForTimeout(400);
  const hija = await p.evaluate(() => ({ nombre: __mosquita.A.nombre, gen: __mosquita.A.gen, madre: __mosquita.A.madreNombre, comp: __mosquita.A.compartido, pares: JSON.stringify(__mosquita.A.pares), linaje: __mosquita.A.linaje.length, w: __mosquita.cer.W[0] }));
  ok(hija.nombre === 'Hija' && hija.gen === 2 && hija.madre === 'Prueba', 'la hija nace con generacion 2 y madre registrada');
  ok(hija.comp > 0.5 && hija.comp < 0.66, 'comparte ' + Math.round(hija.comp * 100) + ' % de conexiones con la madre (esperado 56-60 %: mitad copiada mas coincidencias por azar)');
  ok(hija.linaje === 1, 'el linaje guarda a la madre (' + hija.linaje + ' entrada)');
  ok(hija.pares === '{}', 'la hija no hereda pares aprendidos');
  ok(await p.evaluate(() => !!localStorage.getItem('mosquita.v1')), 'el estado queda guardado en localStorage');
  // sin desbordamiento horizontal en movil
  const over = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  ok(over <= 0, 'sin scroll horizontal a 390 px (exceso ' + over + ')');
  ok(errs.length === 0, 'sin errores de consola (' + errs.length + ')');
  if (errs.length) console.log(errs.join('\n'));
  await b.close();
  console.log(fallos ? fallos + ' fallo(s)' : 'todas las comprobaciones pasan');
  process.exit(fallos ? 1 : 0);
})();
