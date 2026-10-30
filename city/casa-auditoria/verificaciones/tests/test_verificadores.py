"""Auditor: pruebas de que MIS verificadores detectan un error inyectado (en copias, nunca en las casas).
Uso: python tests/test_verificadores.py <city_copia>   (carpeta con las casas copiadas; se hace otra copia de lo que se toca)"""
import json, os, shutil, subprocess, sys, tempfile
AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); CITY = sys.argv[1]; PY = sys.executable
FALLOS = []
def run(script, *args):
    p = subprocess.run([PY, "-I", os.path.join(AQUI, script), *args], capture_output=True, text=True); return p.returncode, p.stdout + p.stderr
def n_disc(txt): return sum(1 for l in txt.splitlines() if l.startswith("[DISCREPANTE]"))
def prueba(nombre, cond, detalle=""):
    print(("OK    " if cond else "FALLO ") + nombre + (" | " + detalle if detalle else ""), flush=True)
    if not cond: FALLOS.append(nombre)
tmp = tempfile.mkdtemp(prefix="aud_test_")
try:
    # 1. mosca: borrar la mitad de las espigas MBON de post_A y anadir 100 espigas KC falsas
    base_rc, base = run("v_mosca.py", os.path.join(CITY, "casa-mosca"))
    m = os.path.join(tmp, "casa-mosca"); os.makedirs(os.path.join(m, "out")); d = json.load(open(os.path.join(CITY, "casa-mosca/out/activity.json")))
    mb = {n["id"] for n in d["neurons"] if n["type"] == "MBON"}; st = {s["name"]: s for s in d["stimuli"]}["post_A"]
    k = 0; nuevo = []
    for t, i in d["spikes"]:
        if i in mb and st["t_start"] <= t < st["t_end"]:
            k += 1
            if k % 2 == 0: continue
        nuevo.append([t, i])
    d["spikes"] = nuevo; json.dump(d, open(os.path.join(m, "out/activity.json"), "w"))
    rc, txt = run("v_mosca.py", m)
    prueba("mosca: espigas MBON de post_A borradas -> se marca 'cambio A' y 'MBON post A'", "[DISCREPANTE] cambio A" in txt and "[DISCREPANTE] MBON post A" in txt and rc == 1, f"discrepantes base {n_disc(base)} -> {n_disc(txt)}")
    kcs = [n["id"] for n in d["neurons"] if n["type"] == "KC"]
    d["spikes"] += [[1000.0 + j * 0.1, kcs[j]] for j in range(100)]; json.dump(d, open(os.path.join(m, "out/activity.json"), "w"))
    rc, txt = run("v_mosca.py", m); prueba("mosca: 100 espigas KC anadidas -> se marca 'espigas totales'", "[DISCREPANTE] espigas totales" in txt)
    # 2. taller: alterar la reserva final del pool (k)
    c = os.path.join(tmp, "city2"); os.makedirs(c)
    for casa, f in (("casa-mosca", "out/activity.json"), ("casa-agora", "out/results.json")):
        os.makedirs(os.path.join(c, casa, os.path.dirname(f))); shutil.copy(os.path.join(CITY, casa, f), os.path.join(c, casa, f))
    rc0, t0 = run("v_taller.py", c)
    r = json.load(open(os.path.join(c, "casa-agora/out/results.json"))); r["pool_path"]["reserve_y"][-1] *= 1.01; json.dump(r, open(os.path.join(c, "casa-agora/out/results.json"), "w"))
    rc, txt = run("v_taller.py", c); prueba("taller: reserva Y final +1% -> se marca 'k final' y 'crecimiento de k'", "[DISCREPANTE] k final" in txt and "[DISCREPANTE] crecimiento k" in txt, f"discrepantes base {n_disc(t0)} -> {n_disc(txt)}")
    # 3. notaria: ciudad mini con la cadena real
    c3 = os.path.join(tmp, "city3"); os.makedirs(c3)
    for casa in ("casa-agora", "casa-mosca", "casa-taller", "casa-notaria"): shutil.copytree(os.path.join(CITY, casa), os.path.join(c3, casa), ignore=shutil.ignore_patterns("__pycache__"))
    rc, txt = run("v_notaria.py", c3); prueba("notaria: copia intacta -> exit 0", rc == 0, txt.strip().splitlines()[-1] if txt.strip() else "")
    p = os.path.join(c3, "casa-mosca/README.md"); b = bytearray(open(p, "rb").read()); b[100] ^= 1; open(p, "wb").write(bytes(b))
    rc, txt = run("v_notaria.py", c3); prueba("notaria: 1 bit cambiado en casa-mosca/README.md -> exit 1 y nombra el archivo", rc == 1 and "README.md" in txt and "casa-mosca" in txt)
    shutil.copy(os.path.join(CITY, "casa-mosca/README.md"), p)
    cp = os.path.join(c3, "casa-notaria/ledger/chain.json"); ch = json.load(open(cp)); ch[1]["casas"][0]["archivos"][0]["sha256"] = "0" * 64; json.dump(ch, open(cp, "w"), indent=2, sort_keys=True)
    rc, txt = run("v_notaria.py", c3); prueba("notaria: sha256 de un archivo alterado DENTRO de la cadena -> exit 1 (hash/raiz no cuadran)", rc == 1 and "PROBLEMA" in txt)
    ch = json.load(open(os.path.join(CITY, "casa-notaria/ledger/chain.json"))); ch[2]["nonce"] += 1; json.dump(ch, open(cp, "w"), indent=2, sort_keys=True)
    rc, txt = run("v_notaria.py", c3); prueba("notaria: nonce del ultimo bloque alterado -> exit 1", rc == 1 and "hash recomputado" in txt)
    # 4. agora: comision distinta NO reproduce la cifra declarada; el comparador lo marca
    sys.path.insert(0, AQUI); sys.argv = ["x", "100"]
    import v_agora as A, veredicto as V
    m1, _ = A.resumen("fee 0.0035", 0.6, 0.0035, seeds=range(500)); prueba("agora: con fee 0,35% en vez de 0,30% el LP-HODL deja de ser -181", abs(m1 + 181) > 0.6, f"{m1:.1f}")
    prueba("veredicto.check marca DISCREPANTE fuera de tolerancia y CONFIRMADA dentro", (not V.check("x", -150, -181, 0.6)) and V.check("y", -181.3, -181, 0.6)); V.RES.clear()
    # 5. empresa: reponer el salto x7,5 de ventas de aula (la objecion del Alcalde) debe cambiar el escenario C
    e = os.path.join(tmp, "casa-empresa"); shutil.copytree(os.path.join(CITY, "casa-empresa/sim"), os.path.join(e, "sim"), ignore=shutil.ignore_patterns("__pycache__", "out"))
    sp = os.path.join(e, "sim/supuestos.json"); s = json.load(open(sp)); s["parametros"]["aula_ventas_semana"].update(min=0.1, moda=0.3, max=0.6); s["parametros"]["aula_precio_anio"].update(moda=129); json.dump(s, open(sp, "w"))
    rc, txt = run("v_empresa_sim.py", e); prueba("empresa: aulas x7,5 y precio 129 -> se marca 'C_aula_regalo margen mediano'", "[DISCREPANTE] C_aula_regalo margen mediano" in txt)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("RESUMEN:", "todas las pruebas pasan" if not FALLOS else f"FALLAN {FALLOS}")
sys.exit(1 if FALLOS else 0)
