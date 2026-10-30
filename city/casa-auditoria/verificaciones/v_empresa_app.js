// Auditor: mide en Chromium (sobre una COPIA de la app) las cifras del cerebro de Mosquita citadas en el README:
// KC activas en reposo y con olor, solapamiento platano-vinagre (Jaccard), efecto de 1 par y de 3 pares sobre la valencia.
// Uso: NODE_PATH=$(npm root -g) node v_empresa_app.js <ruta/index.html> [n_nacimientos]
const { chromium } = require('playwright'); const path = require('path');
const APP = 'file://' + path.resolve(process.argv[2]); const N = parseInt(process.argv[3] || '12');
(async () => {
  const b = await chromium.launch(); const rows = [];
  for (let i = 0; i < N; i++) {
    const ctx = await b.newContext({ viewport: { width: 390, height: 844 } }); const p = await ctx.newPage();
    await p.goto(APP + '?hora=15'); await p.fill('#nombreIntro', 'A' + i); await p.click('#btnNacer'); await p.waitForTimeout(300);
    const r = await p.evaluate(() => {
      const M = __mosquita, cer = M.cer, out = {};
      out.kcPct = M.A.rasgos.kcPorcentaje; out.solap = M.A.rasgos.solapamiento; out.aprende1 = M.A.rasgos.aprendeMedido;
      // reposo: 4 s sin estimulo con pesos de nacimiento
      cer.W = cer.W0.slice(); cer.elig.fill(0); cer.setEstimulo(null); cer.cnt.fill(0); cer.apl = 0;
      for (let s = 0; s < 4000 / 0.5; s++) cer.paso(0.5);
      let n5 = 0, n1 = 0; for (let k = 0; k < 2000; k++) { if (cer.cnt[k] >= 5 * 4) n5++; if (cer.cnt[k] >= 1) n1++; }
      out.reposo_pct_ge5Hz = 100 * n5 / 2000; out.reposo_pct_ge1spike = 100 * n1 / 2000;
      // valencia del platano antes/despues de 1 y 3 pares (olfateo 1.2 s + refuerzo) medida con valencia media de 2 s
      const conc = { platano: 1, levadura: 0, vinagre: 0, menta: 0 };
      function val() { cer.setEstimulo(conc); let a = 0, n = 0; for (let s = 0; s < 4000; s++) { cer.paso(0.5); a += cer.valencia(); n++; } cer.setEstimulo(null); return a / n; }
      function par() { cer.setEstimulo(conc); cer.aprendiendo = true; for (let s = 0; s < 2400; s++) cer.paso(0.5); cer.aprendiendo = false; cer.setEstimulo(null); cer.refuerzo(1); }
      cer.W = cer.W0.slice(); const v0 = val(); par(); const v1 = val(); par(); par(); const v3 = val();
      out.v0 = v0; out.d1 = v1 - v0; out.d3 = v3 - v0; return out;
    });
    rows.push(r); await ctx.close();
  }
  await b.close();
  const m = k => rows.reduce((a, r) => a + r[k], 0) / rows.length, mn = k => Math.min(...rows.map(r => r[k])), mx = k => Math.max(...rows.map(r => r[k]));
  for (const k of ['kcPct', 'solap', 'aprende1', 'reposo_pct_ge5Hz', 'reposo_pct_ge1spike', 'v0', 'd1', 'd3'])
    console.log(k.padEnd(22), 'media', m(k).toFixed(3), 'min', mn(k).toFixed(3), 'max', mx(k).toFixed(3));
})();
