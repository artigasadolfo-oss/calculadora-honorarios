#!/usr/bin/env python3
"""
Contrasta index.html contra calc_icali.py.

  1) Art. 50 (apelación), art. 51 y 51.1, como hasta ahora.
  2) CONTRASTE GENERAL (23/09/2026): el motor puro de index.html
     (scripts/motor_web.js, sin DOM) y calcular() de calc_icali.py, con los mismos
     datos, en una rejilla de casos de todos los procedimientos y todas las
     opciones, más casos al azar. Se comparan las cifras de la minuta y de la
     tasación, antes y después de IPC, redondeo, tope e IVA.
  3) CASOS DEL TEXTO: un caso por cada corrección H1-H12 con el importe que da el
     texto literal del ICALI calculado a mano (no el código), en los dos motores.

(Lo que sigue es la nota original del contraste del art. 50.)

Lee scripts/casos_app.json (generado por test_apelacion_art50.js extrayendo las
funciones REALES del HTML) y ejecuta el mismo caso con calc_icali.py, comparando
el importe base antes de IPC y redondeo.

Uso:  python3 scripts/comparar_con_script.py
Salida: tabla de divergencias; exit 1 si hay alguna.
"""
import json, subprocess, re, sys, os

AQUI = os.path.dirname(os.path.abspath(__file__))
CASOS = os.path.join(AQUI, "casos_app.json")
# calc_icali.py: la copia que se indique en CALC_ICALI o, si no, la de Hermes (que el
# sync diario trae del .skill canónico). Las tres copias (Hermes, plugin instalado y
# .skill) son el mismo fichero.
CALC = os.environ.get("CALC_ICALI") or os.path.expanduser(
    "~/.hermes/skills/legal-esp/honorarios-icali/scripts/calc_icali.py"
)


def script_apelacion(c):
    args = [sys.executable, CALC, "--subtipo", "apelacion",
            "--cuantia", str(c["cuantia"]), "--instancia", c["instancia"]]
    if c.get("parcial"):  args.append("--parcial")
    if c.get("vista"):    args.append("--vista")
    if c.get("prueba"):   args.append("--prueba")
    if c.get("sesVista"): args += ["--sesiones-vista", str(c["sesVista"])]
    if c.get("sesPrueba"):args += ["--sesiones-prueba", str(c["sesPrueba"])]
    if c.get("desOposicion"): args.append("--oposicion")
    if c.get("reclRentas"):   args.append("--rentas")
    if c.get("enerv"):        args.append("--enervacion")
    if c.get("desOrdinario"): args.append("--por-ordinario")
    r = subprocess.run(args, capture_output=True, text=True,
                       cwd=os.path.dirname(CALC))
    m = re.search(r"Importe base:\s+([\d.,]+)", r.stdout)
    if not m:
        return None, r.stdout + r.stderr
    return float(m.group(1).replace(".", "").replace(",", ".")), None


# ── Art. 51: la app y el script deben dar lo mismo ──────────────────────────
# Nombres de subtipo: la app usa 'recurso_*', el script el sufijo a secas.
ART51_MAP = {
    "recurso_esp_audiencia":   "esp_audiencia",
    "recurso_rescision":       "rescision",
    "recurso_revision_firmes": "revision_firmes",
    "recurso_casacion_inadm":  "casacion_inadm",
}


def script_art51(subtipo, cuantia, instancia="ordinario"):
    args = [sys.executable, CALC, "--subtipo", subtipo, "--cuantia", str(cuantia)]
    if subtipo != "esp_audiencia":
        args += ["--instancia", instancia]
    r = subprocess.run(args, capture_output=True, text=True, cwd=os.path.dirname(CALC))
    m = re.search(r"Importe base:\s+([\d.,]+)", r.stdout)
    if not m:
        return None, r.stdout + r.stderr
    return float(m.group(1).replace(".", "").replace(",", ".")), None


def comparar_art51():
    """Contrasta el art. 51 del script contra los valores de la app (index.html),
    leídos del propio HTML con node. Devuelve (ok, divergencias[])."""
    js = r"""
const fs=require('fs'),path=require('path');
const html=fs.readFileSync(path.join(process.argv[2],'index.html'),'utf8');
const B=(re)=>{const m=html.match(re); if(!m){console.error('falta '+re);process.exit(2);} return m[0];};
const src=[B(/var ESCALA\s*=\s*\[[\s\S]*?\];/),B(/function computeEscalaBreakdown[\s\S]*?\n  }/),
 B(/var PROC=\{[\s\S]*?\n  \};/),B(/var ART51=\{[\s\S]*?MIN_RESCISION:\d+\};/),
 B(/var ART51_SOBRE_1I=\{[\s\S]*?\};/),B(/var APEL=\{[\s\S]*?MIN_ORDINARIO:\d+\};/),
 B(/var APEL_VERBALES_ESPECIALES=\{[\s\S]*?\};/),
 B(/function honorariosPrimeraInstancia[\s\S]*?\n  }/),B(/function apelacionMinimo[\s\S]*?\n  }/)].join('\n');
const F=new Function(src+'return {computeEscalaBreakdown,honorariosPrimeraInstancia,PROC,ART51,ART51_SOBRE_1I};')();
const casos=JSON.parse(process.argv[3]);
const out=casos.map(c=>{
  const esc=F.computeEscalaBreakdown(c.cuantia).total, cfg=F.PROC[c.subtipo];
  let v;
  if(c.subtipo==='recurso_esp_audiencia'){ v=Math.max(esc*cfg.normaPct,cfg.minimo); }
  else { const h=F.honorariosPrimeraInstancia(c.instancia,esc,{}).importe;
         const b=h*F.ART51_SOBRE_1I[c.subtipo];
         v=(cfg.minimo>0&&b<cfg.minimo)?cfg.minimo:b; }
  return {...c, app:+v.toFixed(2)};
});
console.log(JSON.stringify(out));
"""
    casos = []
    for sub_app in ART51_MAP:
        for cuantia in [1000, 3000, 8000, 30000, 60000, 150000]:
            for inst in (["ordinario"] if sub_app == "recurso_esp_audiencia"
                         else ["ordinario", "verbal", "ar_precario"]):
                casos.append({"subtipo": sub_app, "cuantia": cuantia, "instancia": inst})
    repo = os.path.dirname(AQUI)
    js_path = os.path.join(AQUI, "_art51_tmp.js")
    with open(js_path, "w", encoding="utf-8") as fh:
        fh.write(js)
    try:
        r = subprocess.run(["node", js_path, repo, json.dumps(casos)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return False, [("ERROR node", "-", 0, r.stderr[:200])], 0
        con_app = json.loads(r.stdout)
    finally:
        os.remove(js_path)

    div = []
    for c in con_app:
        s, e = script_art51(ART51_MAP[c["subtipo"]], c["cuantia"], c["instancia"])
        if s is None:
            div.append((c["subtipo"], c["instancia"], c["cuantia"], f"ERROR: {e[:80]}"))
        elif abs(s - c["app"]) > 0.01:
            div.append((c["subtipo"], c["instancia"], c["cuantia"],
                        f"app {c['app']:.2f} vs script {s:.2f}"))
    return len(div) == 0, div, len(con_app)


# ── Art. 51.1: recursos accesorios (revisión / reposición / queja) ─────────
# Fórmula del baremo: 300 € por recurso; si el acto recurrido tiene cuantía
# propia, 15 % de la Escala de ESA cuantía «con el mismo criterio anterior»
# (mismo mínimo de 300 €). Los valores esperados se derivan del TEXTO, no del
# código, para que el test no sea tautológico.
CASOS_51_1 = [
    # (n_fijos, n_con_cuantia, cuantia_recurso, esperado)
    (1, 0, 0,      300.0),
    (3, 0, 0,      900.0),
    (0, 1, 1000,   300.0),     # 15 % de 354 = 53,10 -> mínimo 300
    (0, 1, 3000,   300.0),     # 15 % de 810 = 121,50 -> mínimo 300
    (0, 2, 1000,   600.0),     # dos recursos, cada uno con su mínimo
    (2, 1, 60000,  600.0 + 1114.50),
]


def comparar_art51_1():
    """El script debe dar los importes del art. 51.1 que exige el texto."""
    div = []
    for n_fijos, n_cuant, cuantia_rec, esperado in CASOS_51_1:
        args = [sys.executable, CALC, "--subtipo", "ordinario", "--cuantia", "30000"]
        if n_fijos:
            args += ["--rec-revision", str(n_fijos)]
        if n_cuant:
            args += ["--rec-con-cuantia", str(n_cuant),
                     "--cuantia-recurso", str(cuantia_rec)]
        r = subprocess.run(args, capture_output=True, text=True, cwd=os.path.dirname(CALC))
        # Importe base del ordinario 30.000 sin accesorios = 4.730,00
        m = re.search(r"Importe base:\s+([\d.,]+)", r.stdout)
        if not m:
            div.append(f"{n_fijos}f/{n_cuant}c/{cuantia_rec}: ERROR {r.stderr[:80]}")
            continue
        total = float(m.group(1).replace(".", "").replace(",", "."))
        obtenido = round(total - 4730.00, 2)
        if abs(obtenido - esperado) > 0.01:
            div.append(f"{n_fijos} fijos + {n_cuant} c/cuantía {cuantia_rec}: "
                       f"script {obtenido:.2f} vs esperado {esperado:.2f}")
    return div


def comparar_art51_1_subtipo():
    """El subtipo rec_51_1 (art. 51.1 como procedimiento) debe dar en el script
    lo mismo que en la app. Valores esperados derivados del texto del baremo."""
    # (cuantia, con_cuantia_propia, n, esperado)
    casos = [
        (0,      False, 1, 300.0),
        (0,      False, 3, 900.0),
        (1000,   True,  1, 300.0),      # 15% de 354 = 53,10 -> mínimo 300
        (3000,   True,  1, 300.0),      # 15% de 810 = 121,50 -> mínimo 300
        (30000,  True,  1, 709.50),     # 15% de 4.730
        (60000,  True,  1, 1114.50),    # 15% de 7.430
        (60000,  True,  2, 2229.00),
    ]
    div = []
    for cuantia, propia, n, esperado in casos:
        args = [sys.executable, CALC, "--subtipo", "rec_51_1",
                "--cuantia", str(cuantia), "--rec-num", str(n)]
        if propia:
            args.append("--rec-cuantia-propia")
        r = subprocess.run(args, capture_output=True, text=True, cwd=os.path.dirname(CALC))
        m = re.search(r"Importe base:\s+([\d.,]+)", r.stdout)
        if not m:
            div.append(f"cuantia={cuantia} propia={propia} n={n}: ERROR {r.stderr[:80]}")
            continue
        got = float(m.group(1).replace(".", "").replace(",", "."))
        if abs(got - esperado) > 0.01:
            div.append(f"cuantia={cuantia} propia={propia} n={n}: "
                       f"script {got:.2f} vs esperado {esperado:.2f}")
    return div, len(casos)


# ── Contraste general web ↔ script (23/09/2026) ────────────────────────────
# El caso se escribe una vez, con los nombres de campo de la web (los del ctx de
# leer()), y se traduce a los argumentos de calc_icali.py.
import argparse, importlib.util, random, tempfile

WEB_A_SCRIPT_SUBTIPO = {
    "recurso_apelacion": "apelacion", "recurso_apelacion_parcial": "apelacion",
    "recurso_51_1": "rec_51_1", "recurso_esp_audiencia": "esp_audiencia",
    "recurso_rescision": "rescision", "recurso_revision_firmes": "revision_firmes",
    "recurso_casacion_inadm": "casacion_inadm",
}

CTX_BASE = {
    "subtipo": "verbal", "cuantia": 0, "indeterminada": False,
    "numSalidasMedio": 0, "numSalidasDia": 0, "numSalidasExtranjero": 0, "gastosExtras": 0,
    "numClientes": 1, "plurVencedores": 1, "plurContrarios": 1,
    "recRev": 0, "recRepo": 0, "recQueja": 0, "recConCuantia": 0, "recCuantiaImporte": 0,
    "aplicarIPC": False, "ipcManual": 32.97, "aplicarRedondeo": False,
    "desOposicion": False, "reclRentas": False, "enerv": False, "desOrdinario": False,
    "ejPre": False, "ejOpo": False, "ejEmb": False, "ejSub": False,
    "apelVista": False, "apelPrueba": False, "apelInstancia": "ordinario",
    "rec511Cuantia": False, "rec511Num": 1, "apelSesVista": 0, "apelSesPrueba": 0,
    "faseAleg": False, "faseAP": False, "faseVista": False, "sesionesExtra": 0,
    "finalizacion": "", "allanParte": "demandante", "allanMomento": "antes_contestacion",
    "derivaMonitorio": False, "reconvencion": False, "medidaCautelar": False,
    "reconvModo": "indet", "reconvCuantia": 0,
    "cautelarModo": "cuantia", "cautelarCuantia": 0, "cautelarTramite": "734", "sentenciaCuantia": 0,
    "noMaterializa": False, "legislacionEspecial": False,
}


def a_script(c):
    """ctx de la web -> Namespace de calc_icali.py."""
    st = c["subtipo"]
    decl = st in ("verbal", "ordinario")
    fases = [k for k, f in (("aleg", "faseAleg"), ("ap", "faseAP"), ("vista", "faseVista")) if c[f]]
    fej = [k for k, f in (("diligencias", "ejPre"), ("oposicion", "ejOpo"), ("apremio", "ejEmb"), ("subasta", "ejSub")) if c[f]]
    return argparse.Namespace(
        subtipo=WEB_A_SCRIPT_SUBTIPO.get(st, st), cuantia=float(c["cuantia"]), indeterminada=c["indeterminada"],
        fases=",".join(fases), fases_ejecucion=",".join(fej),
        instancia=c["apelInstancia"], vista=c["apelVista"], prueba=c["apelPrueba"],
        sesiones_vista=c["apelSesVista"], sesiones_prueba=c["apelSesPrueba"],
        parcial=(st == "recurso_apelacion_parcial"), sin_minimo_1i=False,
        oposicion=c["desOposicion"], rentas=c["reclRentas"], enervacion=c["enerv"], por_ordinario=c["desOrdinario"],
        sesiones=c["sesionesExtra"],
        reconvencion_indet=bool(c["reconvencion"] and c["reconvModo"] != "cuantia"),
        reconvencion_cuantia=(float(c["reconvCuantia"]) if (c["reconvencion"] and c["reconvModo"] == "cuantia") else None),
        deriva_monitorio=c["derivaMonitorio"],
        cautelar=(c["cautelarTramite"] if c["medidaCautelar"] else None),
        cautelar_caucion=float(c["cautelarCuantia"]), cautelar_indet=(c["cautelarModo"] == "indet"),
        sentencia=float(c["sentenciaCuantia"]),
        vencedores=c["plurVencedores"], contrarios=c["plurContrarios"], clientes=c["numClientes"],
        allanamiento=(c["finalizacion"] == "allanamiento"), parte=c["allanParte"], momento=c["allanMomento"],
        renuncia=(c["finalizacion"] == "renuncia"), transaccion=(c["finalizacion"] == "transaccion"),
        legislacion_especial=c["legislacionEspecial"], no_materializa=c["noMaterializa"],
        salidas_medio=c["numSalidasMedio"], salidas_dia=c["numSalidasDia"], salidas_extranjero=c["numSalidasExtranjero"],
        suplidos=float(c["gastosExtras"]),
        rec_revision=c["recRev"], rec_reposicion=c["recRepo"], rec_queja=c["recQueja"],
        rec_con_cuantia=c["recConCuantia"], cuantia_recurso=float(c["recCuantiaImporte"]),
        rec_num=c["rec511Num"], rec_cuantia_propia=c["rec511Cuantia"],
        ipc=(c["ipcManual"] if c["aplicarIPC"] else 0.0), sin_redondeo=not c["aplicarRedondeo"], json=False)


def _modulo_calc():
    spec = importlib.util.spec_from_file_location("calc_icali_contraste", CALC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _web(casos):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(casos, fh)
        ruta = fh.name
    try:
        r = subprocess.run(["node", os.path.join(AQUI, "motor_web.js"), ruta], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr[:400])
        return json.loads(r.stdout)
    finally:
        os.remove(ruta)


def _script(C, c):
    r = C.calcular(a_script(c))
    return {"totalCliente": r["importe_base"], "totalCostas": r["importe_base_costas"],
            "clienteIPC": r["con_ipc"], "baseCliente": r["minuta"], "costasRed": r["costas_redondeo"],
            "lim": r["tercio"], "baseCostas": r["costas"], "muerde": r["topa"], "suplidos": r["suplidos"],
            "conIvaCliente": r["minuta_iva"], "conIvaCostas": r["costas_iva"], "preceptiva": r["preceptiva"]}


def casos_generales():
    """Rejilla determinista de todos los procedimientos y opciones + 600 casos al azar."""
    casos = []
    def caso(**k):
        c = dict(CTX_BASE); c.update(k); casos.append(c)
    cuantias = [0, 900, 1500, 2000, 3000, 9600, 30000, 60000, 186420.55, 1200000]
    subt = ["monitorio_lph", "monitorio_sin", "monitorio_con", "verbal", "ordinario", "ar_fp", "ar_precario",
            "ejecucion", "recurso_apelacion", "recurso_apelacion_parcial", "recurso_51_1", "recurso_esp_audiencia",
            "recurso_rescision", "recurso_revision_firmes", "recurso_casacion_inadm"]
    for st in subt:
        for cu in cuantias:
            for indet in (False, True):
                base = dict(subtipo=st, cuantia=cu, indeterminada=indet, ejPre=(st == "ejecucion"))
                caso(**base)
                caso(**base, aplicarIPC=True, aplicarRedondeo=True)
                caso(**base, legislacionEspecial=True, noMaterializa=(cu > 50000))
                caso(**base, plurVencedores=3, plurContrarios=2, numClientes=2, aplicarIPC=True, aplicarRedondeo=True)
                caso(**base, gastosExtras=437.5, numSalidasMedio=1, numSalidasDia=1, numSalidasExtranjero=2, aplicarIPC=True)
    for cu in cuantias:
        for st in ("verbal", "ordinario"):
            for fin in ("", "allanamiento", "renuncia", "transaccion"):
                for fases in ((False, False, False), (True, False, False), (True, True, False), (True, True, True), (True, False, True)):
                    caso(subtipo=st, cuantia=cu, finalizacion=fin, faseAleg=fases[0], faseAP=fases[1], faseVista=fases[2],
                         allanParte="demandado" if cu % 2 else "demandante", allanMomento="tras_ap" if cu > 5000 else "antes_contestacion")
            caso(subtipo=st, cuantia=cu, derivaMonitorio=True)
            caso(subtipo=st, cuantia=cu, reconvencion=True, reconvModo="indet")
            caso(subtipo=st, cuantia=cu, reconvencion=True, reconvModo="cuantia", reconvCuantia=cu / 2)
            caso(subtipo=st, cuantia=cu, indeterminada=True, reconvencion=True, reconvModo="indet")
            for tr in ("733", "734", "739"):
                caso(subtipo=st, cuantia=cu, medidaCautelar=True, cautelarTramite=tr, cautelarCuantia=cu / 10)
                caso(subtipo=st, cuantia=cu, medidaCautelar=True, cautelarTramite=tr, cautelarCuantia=cu / 3)
            caso(subtipo=st, cuantia=cu, medidaCautelar=True, cautelarModo="indet")
            caso(subtipo=st, cuantia=cu, sentenciaCuantia=cu / 3, plurVencedores=2, aplicarIPC=True, aplicarRedondeo=True)
            caso(subtipo=st, cuantia=cu, sesionesExtra=2, recRepo=1, recConCuantia=1, recCuantiaImporte=cu)
    for cu in cuantias:
        for opo in (False, True):
            for ren in (False, True):
                for ene in (False, True):
                    for ordi in (False, True):
                        caso(subtipo="ar_fp", cuantia=cu, desOposicion=opo, reclRentas=ren, enerv=ene, desOrdinario=ordi)
                        caso(subtipo="ar_fp", cuantia=cu, desOposicion=opo, reclRentas=ren, enerv=ene, desOrdinario=ordi,
                             faseAleg=True, faseAP=ordi, finalizacion="renuncia" if ren else "")
        for inst in ("ordinario", "verbal", "ar_fp", "ar_precario"):
            for st in ("recurso_apelacion", "recurso_apelacion_parcial", "recurso_rescision"):
                caso(subtipo=st, cuantia=cu, apelInstancia=inst, apelVista=True, apelPrueba=cu > 5000, apelSesVista=1,
                     desOposicion=True, enerv=cu > 20000, desOrdinario=cu < 3000)
        for bits in range(1, 16):   # sin ninguna fase, la web no da importe: se prueba aparte
            caso(subtipo="ejecucion", cuantia=cu, ejPre=bool(bits & 1), ejOpo=bool(bits & 2), ejEmb=bool(bits & 4), ejSub=bool(bits & 8))
    rnd = random.Random(23092026)
    for _ in range(600):
        st = rnd.choice(subt)
        c = dict(CTX_BASE)
        c.update(subtipo=st, cuantia=rnd.choice([rnd.randint(0, 3000), rnd.randint(0, 80000), round(rnd.uniform(0, 2e6), 2)]),
                 indeterminada=rnd.random() < 0.12, aplicarIPC=rnd.random() < 0.7, ipcManual=rnd.choice([32.97, 30.17, 0, 35.5]),
                 aplicarRedondeo=rnd.random() < 0.6, numSalidasMedio=rnd.randint(0, 2), numSalidasDia=rnd.randint(0, 1),
                 numSalidasExtranjero=rnd.randint(0, 1), gastosExtras=rnd.choice([0, 0, 125.4, 900]),
                 numClientes=rnd.randint(1, 4), plurVencedores=rnd.randint(1, 6), plurContrarios=rnd.randint(1, 6),
                 recRev=rnd.randint(0, 1), recRepo=rnd.randint(0, 1), recConCuantia=rnd.randint(0, 2), recCuantiaImporte=rnd.randint(0, 40000),
                 desOposicion=rnd.random() < 0.5, reclRentas=rnd.random() < 0.5, enerv=rnd.random() < 0.3, desOrdinario=rnd.random() < 0.2,
                 ejPre=rnd.random() < 0.8, ejOpo=rnd.random() < 0.4, ejEmb=rnd.random() < 0.5, ejSub=rnd.random() < 0.4,
                 apelVista=rnd.random() < 0.5, apelPrueba=rnd.random() < 0.4, apelInstancia=rnd.choice(["ordinario", "verbal", "ar_fp", "ar_precario"]),
                 rec511Cuantia=rnd.random() < 0.5, rec511Num=rnd.randint(1, 3), apelSesVista=rnd.randint(0, 2), apelSesPrueba=rnd.randint(0, 2),
                 faseAleg=rnd.random() < 0.5, faseAP=rnd.random() < 0.4, faseVista=rnd.random() < 0.4, sesionesExtra=rnd.randint(0, 2),
                 finalizacion=rnd.choice(["", "", "allanamiento", "renuncia", "transaccion"]),
                 allanParte=rnd.choice(["demandante", "demandado"]),
                 allanMomento=rnd.choice(["antes_contestacion", "tras_contestacion", "tras_ap", "tras_juicio"]),
                 derivaMonitorio=rnd.random() < 0.3, reconvencion=rnd.random() < 0.3, medidaCautelar=rnd.random() < 0.3,
                 reconvModo=rnd.choice(["indet", "cuantia"]), reconvCuantia=rnd.randint(0, 50000),
                 cautelarModo=rnd.choice(["cuantia", "cuantia", "indet"]), cautelarCuantia=rnd.randint(0, 60000),
                 cautelarTramite=rnd.choice(["733", "734", "739"]),
                 sentenciaCuantia=rnd.choice([0, 0, rnd.randint(0, 60000)]),
                 noMaterializa=rnd.random() < 0.15, legislacionEspecial=rnd.random() < 0.2)
        if st == "ejecucion" and not (c["ejPre"] or c["ejOpo"] or c["ejEmb"] or c["ejSub"]):
            c["ejPre"] = True   # sin fases, la web no da importe (y el script toma 27.1): se prueba aparte
        casos.append(c)
    return casos


CAMPOS = ["totalCliente", "totalCostas", "clienteIPC", "baseCliente", "costasRed", "lim", "baseCostas",
          "muerde", "suplidos", "conIvaCliente", "conIvaCostas", "preceptiva"]


def comparar_general():
    C = _modulo_calc()
    casos = casos_generales()
    web = _web(casos)
    div = []
    for c, w in zip(casos, web):
        if w.get("sinFases"):
            div.append(f"{c['subtipo']} {c['cuantia']}: la web no da importe (sin fases)")
            continue
        s = _script(C, c)
        malos = [k for k in CAMPOS if (w[k] != s[k] if isinstance(s[k], bool) else abs(w[k] - s[k]) > 0.01)]
        if malos:
            div.append(f"{c['subtipo']} {c['cuantia']}: " + ", ".join(f"{k} web {w[k]} / script {s[k]}" for k in malos[:3]))
    # ejecución sin ninguna fase: la web enseña un guion, no 0,00 €
    sin = _web([dict(CTX_BASE, subtipo="ejecucion", cuantia=5000)])[0]
    if not sin.get("sinFases"):
        div.append("ejecución sin fases: la web da un importe en vez del guion")
    return len(casos) + 1, div


# Importes calculados A MANO desde el texto literal (sin IPC ni redondeo), no desde el código.
ESC = {3000: 810.00, 5000: 1190.00, 9000: 1880.00, 9600: 1982.00, 10000: 2050.00, 20000: 3590.00,
       30000: 4730.00, 60000: 7430.00, 100000: 10230.00}
CASOS_TEXTO = [
    ("H1 verbal indeterminado: 500 € (art. 13)", dict(subtipo="verbal", indeterminada=True), "totalCliente", 500.00),
    ("H1 ordinario indeterminado: 2.000 € (art. 15.C)", dict(subtipo="ordinario", indeterminada=True), "totalCliente", 2000.00),
    ("H1 tope del tercio indeterminado: 24.000/3 (art. 394.3 LEC)", dict(subtipo="ordinario", indeterminada=True), "lim", 8000.00),
    ("H1 ordinario 20.000 + reconvención indeterminada: escala + 2.000 (art. 15.D)",
     dict(subtipo="ordinario", cuantia=20000, reconvencion=True, reconvModo="indet"), "totalCliente", ESC[20000] + 2000),
    ("H1 verbal indeterminado + reconvención indeterminada: 500 + 500 (art. 13)",
     dict(subtipo="verbal", indeterminada=True, reconvencion=True, reconvModo="indet"), "totalCliente", 1000.00),
    ("H1 apelación de ordinario indeterminado: 50 % de 2.000 → mín. 1.000 (art. 50)",
     dict(subtipo="recurso_apelacion", indeterminada=True, apelInstancia="ordinario"), "totalCliente", 1000.00),
    ("H2 cautelar art. 734, caución 9.000: 30 % de la Escala (art. 33.B)",
     dict(subtipo="ordinario", cuantia=60000, medidaCautelar=True, cautelarTramite="734", cautelarCuantia=9000), "totalCliente", ESC[60000] + 0.30 * ESC[9000]),
    ("H2 cautelar art. 733.2: 20 % (art. 33.A)",
     dict(subtipo="ordinario", cuantia=60000, medidaCautelar=True, cautelarTramite="733", cautelarCuantia=9000), "totalCliente", ESC[60000] + 0.20 * ESC[9000]),
    ("H2 cautelar arts. 739-741: 40 % (art. 33.C)",
     dict(subtipo="ordinario", cuantia=60000, medidaCautelar=True, cautelarTramite="739", cautelarCuantia=9000), "totalCliente", ESC[60000] + 0.40 * ESC[9000]),
    ("H2 cautelar con caución de 1.000: suelo del 15 % de 60.000 = 9.000 (art. 33)",
     dict(subtipo="ordinario", cuantia=60000, medidaCautelar=True, cautelarTramite="734", cautelarCuantia=1000), "totalCliente", ESC[60000] + 0.30 * ESC[9000]),
    ("H2 cautelar indeterminada: 400 € (art. 33)",
     dict(subtipo="ordinario", cuantia=60000, medidaCautelar=True, cautelarModo="indet"), "totalCliente", ESC[60000] + 400),
    ("H3 verbal 1.500 tras monitorio: 500 + 150 (arts. 13 y 48)",
     dict(subtipo="verbal", cuantia=1500, derivaMonitorio=True), "totalCliente", 650.00),
    ("H3 ordinario 100.000 tras monitorio: escala + 10 % de la escala (art. 48.1)",
     dict(subtipo="ordinario", cuantia=100000, derivaMonitorio=True), "totalCliente", ESC[100000] * 1.10),
    ("H4 desahucio 9.600 con oposición y enervación: 75 % del apartado A (art. 18)",
     dict(subtipo="ar_fp", cuantia=9600, desOposicion=True, enerv=True), "totalCliente", ESC[9600] * 0.75 * 0.75),
    ("H5 desahucio 3.000 por el cauce del ordinario: mín. 2.000 (art. 18)",
     dict(subtipo="ar_fp", cuantia=3000, desOrdinario=True), "totalCliente", 2000.00),
    ("H6 ordinario 30.000, desistimiento tras la AP: 60 + 10 % (DG 2.ª D)",
     dict(subtipo="ordinario", cuantia=30000, faseAleg=True, faseAP=True, finalizacion="renuncia"), "totalCliente", ESC[30000] * 0.70),
    ("H6 verbal 5.000, desistimiento: 60 % (DG 2.ª D)",
     dict(subtipo="verbal", cuantia=5000, finalizacion="renuncia", faseAleg=True, faseVista=True), "totalCliente", ESC[5000] * 0.60),
    ("H7 tres clientes: +40 % /3 solo en la minuta (DG 2.ª G)",
     dict(subtipo="ordinario", cuantia=30000, numClientes=3), "totalCliente", ESC[30000] * 1.4 / 3),
    ("H7 tres clientes: la tasación no cambia (DG 2.ª G)",
     dict(subtipo="ordinario", cuantia=30000, numClientes=3), "totalCostas", ESC[30000]),
    ("H7 tres vencedores: +40 % /3 solo en costas (DG 2.ª F)",
     dict(subtipo="ordinario", cuantia=30000, plurVencedores=3), "totalCostas", ESC[30000] * 1.4 / 3),
    ("H7 tres vencedores: la minuta no cambia (DG 2.ª F)",
     dict(subtipo="ordinario", cuantia=30000, plurVencedores=3), "totalCliente", ESC[30000]),
    ("H7 dos contrarios: +10 % solo en costas (DG 2.ª F)",
     dict(subtipo="ordinario", cuantia=30000, plurContrarios=2), "totalCostas", ESC[30000] * 1.10),
    ("H8 suplidos 400 € sin IPC ni IVA (DG 2.ª A)",
     dict(subtipo="verbal", cuantia=5000, gastosExtras=400, aplicarIPC=True, ipcManual=32.97), "conIvaCliente", ESC[5000] * 1.3297 * 1.21 + 400),
    ("H8 dos días en el extranjero: 600 €/día (DG 2.ª A)",
     dict(subtipo="verbal", cuantia=5000, numSalidasExtranjero=2), "totalCliente", ESC[5000] + 1200),
    ("H9 legislación especial en una ejecución: +50 % (DG 3.ª)",
     dict(subtipo="ejecucion", cuantia=5000, ejPre=True, legislacionEspecial=True), "totalCliente", ESC[5000] * 0.20 * 1.5),
    ("H10 sentencia de 10.000 sobre 30.000 pedidos: costas sobre 10.000 (art. 15.B)",
     dict(subtipo="ordinario", cuantia=30000, sentenciaCuantia=10000), "totalCostas", ESC[10000]),
    ("H10 la minuta sigue sobre lo pedido",
     dict(subtipo="ordinario", cuantia=30000, sentenciaCuantia=10000), "totalCliente", ESC[30000]),
    ("H11 ordinario 3.000 con 2 vencedores: tope de 1.000 € por cada uno (art. 394.3 LEC)",
     dict(subtipo="ordinario", cuantia=3000, plurVencedores=2), "baseCostas", 1000.00),
    ("H12 monitorio de 8.000: petición inicial no preceptiva (art. 814.2 LEC)", dict(subtipo="monitorio_sin", cuantia=8000), "preceptiva", False),
    ("H12 monitorio de comunidad: honorarios a cargo del deudor (art. 21.5 LPH)", dict(subtipo="monitorio_lph", cuantia=1200), "preceptiva", True),
    ("H12 desahucio de 1.500: preceptiva (art. 31.2.1.º LEC)", dict(subtipo="ar_fp", cuantia=1500), "preceptiva", True),
    ("H12 ordinario de 1.500: preceptiva (art. 31.2.1.º LEC)", dict(subtipo="ordinario", cuantia=1500), "preceptiva", True),
    ("H12 verbal de 1.500: no preceptiva (art. 31.2.1.º LEC)", dict(subtipo="verbal", cuantia=1500), "preceptiva", False),
]


def comprobar_casos_texto():
    C = _modulo_calc()
    ctxs = [dict(CTX_BASE, **k) for _, k, _, _ in CASOS_TEXTO]
    web = _web(ctxs)
    div = []
    for (n, _, campo, esp), c, w in zip(CASOS_TEXTO, ctxs, web):
        s = _script(C, c)
        for quien, v in (("web", w[campo]), ("script", s[campo])):
            ok = (v == esp) if isinstance(esp, bool) else abs(v - esp) < 0.01
            if not ok:
                div.append(f"{n}: {quien} da {v}, el texto {esp}")
    return len(CASOS_TEXTO), div


def main():
    casos = json.load(open(CASOS, encoding="utf-8"))
    div, err, ok = [], [], 0
    for c in casos:
        s, e = script_apelacion(c)
        if s is None:
            err.append((c, e)); continue
        if abs(s - c["app"]) > 0.01:
            div.append((c, c["app"], s))
        else:
            ok += 1

    print(f"Casos comparados: {len(casos)}  ·  coinciden: {ok}  ·  divergen: {len(div)}  ·  errores: {len(err)}")
    if div:
        print("\nDIVERGENCIAS (app vs script):")
        print(f"  {'instancia':<13}{'cuantía':>9}{'V':>2}{'P':>2}{'par':>4}{'APP':>11}{'SCRIPT':>11}{'dif':>10}")
        for c, a, s in div:
            print(f"  {c['instancia']:<13}{c['cuantia']:>9}"
                  f"{'V' if c.get('vista') else '-':>2}{'P' if c.get('prueba') else '-':>2}"
                  f"{'sí' if c.get('parcial') else '-':>4}{a:>11.2f}{s:>11.2f}{a-s:>+10.2f}")
    if err:
        print("\nERRORES DE EJECUCIÓN:")
        for c, e in err[:3]:
            print(" ", c, "->", (e or "")[:200])

    # ── Art. 51 ────────────────────────────────────────────────────────────
    ok51, div51, n51 = comparar_art51()
    print(f"\nArt. 51 — casos comparados: {n51}  ·  coinciden: {n51 - len(div51)}  ·  divergen: {len(div51)}")
    if div51:
        print("DIVERGENCIAS art. 51:")
        for sub, inst, c, msg in div51:
            print(f"  {sub:<26}{inst:<13}{c:>9}   {msg}")

    # ── Art. 51.1 (recursos accesorios) ────────────────────────────────────
    div511 = comparar_art51_1()
    print(f"\nArt. 51.1 — casos comparados: {len(CASOS_51_1)}  ·  "
          f"coinciden: {len(CASOS_51_1) - len(div511)}  ·  divergen: {len(div511)}")
    if div511:
        print("DIVERGENCIAS art. 51.1:")
        for msg in div511:
            print(f"  {msg}")

    # ── Art. 51.1 como SUBTIPO propio (rec_51_1) ───────────────────────────
    div511s, n511s = comparar_art51_1_subtipo()
    print(f"\nArt. 51.1 subtipo — casos comparados: {n511s}  ·  "
          f"coinciden: {n511s - len(div511s)}  ·  divergen: {len(div511s)}")
    if div511s:
        print("DIVERGENCIAS art. 51.1 (subtipo):")
        for msg in div511s:
            print(f"  {msg}")

    # ── Contraste general y casos del texto ────────────────────────────────
    ng, divg = comparar_general()
    print(f"\nContraste general web-script — casos: {ng}  ·  coinciden: {ng - len(divg)}  ·  divergen: {len(divg)}")
    for d in divg[:15]:
        print("  ", d)
    nt, divt = comprobar_casos_texto()
    print(f"\nCasos del texto (H1-H12) — casos: {nt}  ·  correctos en los dos motores: {nt - len(divt)}  ·  fallan: {len(divt)}")
    for d in divt:
        print("  ", d)
    total = len(casos) + n51 + len(CASOS_51_1) + n511s + ng + nt
    malos = len(div) + len(err) + len(div51) + len(div511) + len(div511s) + len(divg) + len(divt)
    print(f"\nTOTAL: {total} casos · {total - malos} coinciden · {malos} divergen")

    return 1 if (div or err or div51 or div511 or div511s or divg or divt) else 0


if __name__ == "__main__":
    sys.exit(main())
