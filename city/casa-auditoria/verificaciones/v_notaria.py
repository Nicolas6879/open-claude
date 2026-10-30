"""Auditor: verificador INDEPENDIENTE de la cadena de casa-notaria (escrito desde el README, sin importar notaria.py).
Comprueba: enlaces, hash (sha256(json canonico sin hash/nonce || '|' || nonce)), 4 ceros, genesis,
raices Merkle de cada casa y de casas (hoja = sha256(0x00||ruta||sha_raw32), nodo = sha256(0x01||i||d), impar promocionada),
y que los archivos de las casas selladas siguen coincidiendo con el ULTIMO bloque que las contiene.
Uso: python v_notaria.py <city_dir> ; sale 1 si encuentra discrepancia."""
import hashlib, json, os, sys, unicodedata
city = sys.argv[1]
chain = json.load(open(os.path.join(city, "casa-notaria", "ledger", "chain.json"), encoding="utf-8"))
S = lambda b: hashlib.sha256(b).digest()
def leaf(name, hexv): return S(b"\x00" + name.encode() + bytes.fromhex(hexv))
def root(leaves):
    if not leaves: return S(b"\x02vacio")
    lv = list(leaves)
    while len(lv) > 1:
        nx = [S(b"\x01" + lv[i] + lv[i + 1]) for i in range(0, len(lv) - 1, 2)]
        if len(lv) % 2: nx.append(lv[-1])
        lv = nx
    return lv[0]
bad = []
canon = lambda o: json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
prev = "0" * 64
for i, b in enumerate(chain):
    h = hashlib.sha256(canon({k: v for k, v in b.items() if k not in ("hash", "nonce")}).encode() + b"|" + str(b["nonce"]).encode()).hexdigest()
    if h != b["hash"]: bad.append(f"bloque {i}: hash recomputado {h[:12]} != {b['hash'][:12]}")
    if not b["hash"].startswith("0000"): bad.append(f"bloque {i}: sin 4 ceros")
    if b["anterior"] != prev: bad.append(f"bloque {i}: enlace roto")
    prev = b["hash"]
    for c in b["casas"]:
        r = root([leaf(a["ruta"], a["sha256"]) for a in c["archivos"]]).hex()
        if r != c["raiz"]: bad.append(f"bloque {i} {c['casa']}: raiz Merkle recomputada {r[:12]} != {c['raiz'][:12]}")
    rc = root([leaf(c["casa"], c["raiz"]) for c in b["casas"]]).hex()
    if rc != b["raiz_casas"]: bad.append(f"bloque {i}: raiz_casas {rc[:12]} != {b['raiz_casas'][:12]}")
print("bloques", len(chain), "| problemas internos de la cadena:", len(bad))
# archivos en disco vs ultimo bloque que contiene la casa
ultimo = {}
for b in chain:
    for c in b["casas"]: ultimo[c["casa"]] = (b["indice"], c)
def scan(d):
    out = {}
    for dp, dn, fn in os.walk(d):
        dn[:] = [x for x in dn if not x.startswith(".") and x != "__pycache__"]
        for f in fn:
            if f.startswith(".") or f.endswith(".pyc"): continue
            p = os.path.join(dp, f); rel = unicodedata.normalize("NFC", os.path.relpath(p, d).replace(os.sep, "/"))
            out[rel] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out
for casa in sorted(d for d in os.listdir(city) if os.path.isdir(os.path.join(city, d)) and d != "casa-notaria" and not d.startswith(".")):
    if casa not in ultimo: print(f"{casa}: SIN SELLAR (no esta en ningun bloque)"); continue
    idx, c = ultimo[casa]; sel = {a["ruta"]: a["sha256"] for a in c["archivos"]}; now = scan(os.path.join(city, casa))
    diff = [("desaparecido", r) for r in sel if r not in now] + [("anadido", r) for r in now if r not in sel] + [("modificado", r) for r in sel if r in now and sel[r] != now[r]]
    if diff:
        print(f"{casa}: DIFIERE del bloque {idx}:", diff); bad.append(f"{casa} difiere de su sello")
    else: print(f"{casa}: coincide con el bloque {idx} ({len(now)} archivos)")
for m in bad: print("PROBLEMA:", m)
sys.exit(1 if bad else 0)
