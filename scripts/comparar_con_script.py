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
    "noMaterializa": False, "legislacionEspecial": False, "materiaPH": False,
    "tituloVerbalPH": False,
    "coincidenciaTitulos": "distintos", "numClientesDistintos": 1, "cuantiaDiscutida": 0,
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
        titulos_clientes=c["coincidenciaTitulos"], clientes_distintos=c["numClientesDistintos"],
        cuantia_discutida=float(c["cuantiaDiscutida"] or 0),
        allanamiento=(c["finalizacion"] == "allanamiento"), parte=c["allanParte"], momento=c["allanMomento"],
        renuncia=(c["finalizacion"] == "renuncia"), transaccion=(c["finalizacion"] == "transaccion"),
        legislacion_especial=c["legislacionEspecial"], no_materializa=c["noMaterializa"],
        materia_ph=c.get("materiaPH", False), titulo_verbal_ph=c.get("tituloVerbalPH", False),
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
            "conIvaCliente": r["minuta_iva"], "conIvaCostas": r["costas_iva"], "preceptiva": r["preceptiva"],
            "ivaCliente": r["iva_minuta"], "ivaCostas": r["iva_costas"], "totalClienteMayoria": r["minuta_mayoria"],
            "precTexto": r["preceptividad"]}


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
    # 31/10/2026 (D1, D2, D4, D5, céntimo): más casos en rejilla
    for cu in (3000, 30000, 60000):
        for n_cli in (2, 3, 4):
            for mod in ("distintos", "parcial", "identicos"):
                for k in (1, 2, 3, 9):
                    caso(subtipo="ordinario", cuantia=cu, numClientes=n_cli, coincidenciaTitulos=mod, numClientesDistintos=k,
                         aplicarIPC=True, aplicarRedondeo=(k % 2 == 0), gastosExtras=100)
        for cd in (0, 1000, 5000, 20000, 50000, 90000):
            for fases in ((False, True, False, False), (True, True, False, False), (True, True, True, True)):
                caso(subtipo="ejecucion", cuantia=cu, ejPre=fases[0], ejOpo=fases[1], ejEmb=fases[2], ejSub=fases[3],
                     cuantiaDiscutida=cd, aplicarIPC=(cd > 5000), aplicarRedondeo=(cd > 20000), legislacionEspecial=(cd == 50000))
        for st in subt:
            caso(subtipo=st, cuantia=cu, ejPre=(st == "ejecucion"), faseAleg=True, faseAP=True, faseVista=True,
                 finalizacion="transaccion", aplicarIPC=True, aplicarRedondeo=True)
            caso(subtipo=st, cuantia=cu, ejPre=(st == "ejecucion"), faseAleg=True, finalizacion="transaccion", legislacionEspecial=True)
        caso(subtipo="ordinario", cuantia=cu, medidaCautelar=True, cautelarCuantia=cu, sesionesExtra=2, recConCuantia=1,
             recCuantiaImporte=cu, derivaMonitorio=True, legislacionEspecial=True, faseAleg=True, faseAP=True, faseVista=True)
        caso(subtipo="ordinario", cuantia=cu, aplicarIPC=True, ipcManual=33.4, faseAleg=True, sentenciaCuantia=cu / 3, plurVencedores=2)
    for cu in cuantias + [2001, 5000, 12000]:    # verbal por materia (cuotas LPH, art. 250.1.15.º LEC), 13/10/2026
        for ind in (False, True):
            caso(subtipo="verbal", cuantia=cu, indeterminada=ind, materiaPH=True)
            caso(subtipo="verbal", cuantia=cu, indeterminada=ind, materiaPH=True, aplicarIPC=True, aplicarRedondeo=True,
                 plurVencedores=2, numClientes=2, gastosExtras=100)
    for cu in cuantias + [2001, 5000, 12000]:    # ejecución de lo resuelto en un verbal de cuotas (art. 539.1 LEC), 13/10/2026
        for ind in (False, True):
            caso(subtipo="ejecucion", cuantia=cu, indeterminada=ind, ejPre=True, tituloVerbalPH=True)
            caso(subtipo="ejecucion", cuantia=cu, indeterminada=ind, ejPre=True, ejOpo=True, ejEmb=True, ejSub=True,
                 tituloVerbalPH=True, aplicarIPC=True, aplicarRedondeo=True, plurVencedores=2, numClientes=2, gastosExtras=100)
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
    rnd2 = random.Random(31102026)
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
        # campos nuevos con su propio generador: la secuencia anterior de casos al azar no cambia
        c.update(coincidenciaTitulos=rnd2.choice(["distintos", "parcial", "identicos"]), numClientesDistintos=rnd2.randint(1, 5),
                 cuantiaDiscutida=rnd2.choice([0, 0, rnd2.randint(1, 3000), rnd2.randint(1, 90000)]))
        casos.append(c)
    return casos


CAMPOS = ["totalCliente", "totalCostas", "clienteIPC", "baseCliente", "costasRed", "lim", "baseCostas",
          "muerde", "suplidos", "conIvaCliente", "conIvaCostas", "preceptiva", "ivaCliente", "ivaCostas"]
# 31/10/2026: «al céntimo» (antes 0,01, que dejaba pasar 164,47 frente a 164,46) en bases, IVA y totales con IVA,
# que son importes en céntimos. Los intermedios en bruto (importe base, IPC, costasRed, lim) salen de motor_web.js
# ya redondeados a 2 decimales y del script en bruto: ahí la tolerancia sigue siendo de medio céntimo más el redondeo.
TOL = 0.005
TOL_CRUDO = 0.0101
CAMPOS_CENTIMO = ("baseCliente", "baseCostas", "conIvaCliente", "conIvaCostas", "ivaCliente", "ivaCostas")


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
        malos = [k for k in CAMPOS if (w[k] != s[k] if isinstance(s[k], bool) else abs(w[k] - s[k]) > (TOL if k in CAMPOS_CENTIMO else TOL_CRUDO))]
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


# ── Verbal por materia (cuotas de la LPH, art. 250.1.15.º LEC) · 13/10/2026 ─
# Lo que se comprueba, en la web (motor_web.js) y en el script (--materia-ph):
#  · con la opción, preceptiva a cualquier cuantía y con el MISMO texto en los dos;
#  · sin ella, el comportamiento por defecto no cambia (verbal ≤ 2.000 € no preceptiva; > 2.000 €, sí;
#    ordinario, siempre sí);
#  · las cifras (minuta, costas, tercio, IVA) son idénticas con y sin la opción, en cada motor;
#  · la opción no afecta a otros subtipos (sin efecto fuera del verbal).
CUANTIAS_PH = [1500, 2000, 2001, 5000, 12000]
CAMPOS_CIFRAS = ["totalCliente", "totalCostas", "clienteIPC", "baseCliente", "costasRed", "lim", "baseCostas",
                 "muerde", "suplidos", "conIvaCliente", "conIvaCostas"]


def comprobar_materia_ph():
    C = _modulo_calc()
    ipc = dict(aplicarIPC=True, aplicarRedondeo=True)
    ctxs, claves = [], []
    for cu in CUANTIAS_PH:
        for st in ("verbal", "ordinario"):
            for ph in (False, True):
                ctxs.append(dict(CTX_BASE, subtipo=st, cuantia=cu, materiaPH=ph, **ipc))
                claves.append((st, cu, ph))
    web = _web(ctxs)
    res = {}
    for k, c, w in zip(claves, ctxs, web):
        res[k] = (w, _script(C, c))
    div, n = [], 0
    def chk(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            div.append(msg)
    for cu in CUANTIAS_PH:
        for st in ("verbal", "ordinario"):
            sin_w, sin_s = res[(st, cu, False)]
            con_w, con_s = res[(st, cu, True)]
            # 1) cifras iguales con y sin la opción, y web = script
            for k in CAMPOS_CIFRAS:
                chk(sin_w[k] == con_w[k], f"{st} {cu}: web cambia {k} con la opción ({sin_w[k]} → {con_w[k]})")
                chk(sin_s[k] == con_s[k], f"{st} {cu}: script cambia {k} con la opción ({sin_s[k]} → {con_s[k]})")
                chk(abs(con_w[k] - con_s[k]) < 0.01 if not isinstance(con_s[k], bool) else con_w[k] == con_s[k],
                    f"{st} {cu}: con la opción {k} web {con_w[k]} / script {con_s[k]}")
            # 2) preceptividad por defecto (sin la opción) y con ella
            esp_sin = False if (st == "verbal" and cu <= 2000) else True
            chk(sin_w["preceptiva"] is esp_sin and sin_s["preceptiva"] is esp_sin,
                f"{st} {cu} sin opción: web {sin_w['preceptiva']} / script {sin_s['preceptiva']} / esperado {esp_sin}")
            chk(sin_w["precDesglose"] != "" and sin_w["precDesglose"] == res[(st, cu, False)][0]["precDesglose"], "sin opción: texto web vacío")
            if st == "verbal":
                chk(con_w["preceptiva"] is True and con_s["preceptiva"] is True,
                    f"verbal {cu} con opción: web {con_w['preceptiva']} / script {con_s['preceptiva']}")
                chk(con_w["precDesglose"] == con_s["precTexto"], f"verbal {cu} con opción: el texto difiere")
                chk("250.1.15.º" in con_w["precDesglose"] and "sin jurisprudencia leída" in con_w["precDesglose"],
                    f"verbal {cu} con opción: falta cita o aviso")
            else:   # ordinario: la opción no hace nada
                chk(con_w["preceptiva"] is True and con_s["preceptiva"] is True and con_w["precDesglose"] == sin_w["precDesglose"],
                    f"ordinario {cu}: la opción lo altera")
                chk(con_s["precTexto"] == sin_s["precTexto"], f"ordinario {cu}: el script cambia el texto con la opción")
    # 3) la opción no toca otros subtipos (monitorio_sin sigue no preceptivo; ar_fp sigue preceptivo)
    for st, esp in (("monitorio_sin", False), ("ar_fp", True), ("ejecucion", False)):
        c = dict(CTX_BASE, subtipo=st, cuantia=1500, materiaPH=True, ejPre=(st == "ejecucion"))
        w = _web([c])[0]; s_ = _script(C, c)
        chk(w["preceptiva"] is esp and s_["preceptiva"] is esp, f"{st} 1500 con opción: web {w['preceptiva']} / script {s_['preceptiva']} / esperado {esp}")
    return n, div, res


# ── Ejecución de lo resuelto en un verbal de cuotas (art. 539.1, párr. 1.º LEC) · 13/10/2026 ─
# Lo que se comprueba, en la web (motor_web.js) y en el script (--titulo-verbal-ph):
#  · con la opción, la ejecución sale preceptiva a cualquier cuantía y con el MISMO texto en los dos;
#  · sin ella, el comportamiento por defecto no cambia (ejecución ≤ 2.000 € no preceptiva; > 2.000 €, sí);
#  · las cifras son idénticas con y sin la opción, en cada motor (solo cambia la mención de preceptividad);
#  · la opción no afecta a otros subtipos (verbal, monitorio_sin, ordinario).
def comprobar_titulo_verbal_ph():
    C = _modulo_calc()
    ipc = dict(aplicarIPC=True, aplicarRedondeo=True)
    fases = dict(ejPre=True, ejOpo=True, ejEmb=True, ejSub=True)
    ctxs, claves = [], []
    for cu in CUANTIAS_PH:
        for ind in (False, True):
            for tv in (False, True):
                ctxs.append(dict(CTX_BASE, subtipo="ejecucion", cuantia=cu, indeterminada=ind, tituloVerbalPH=tv, **fases, **ipc))
                claves.append((cu, ind, tv))
    web = _web(ctxs)
    res = {k: (w, _script(C, c)) for k, c, w in zip(claves, ctxs, web)}
    div, n = [], 0
    def chk(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            div.append(msg)
    for cu in CUANTIAS_PH:
        for ind in (False, True):
            sin_w, sin_s = res[(cu, ind, False)]
            con_w, con_s = res[(cu, ind, True)]
            et = f"ejecución {cu}{' indet.' if ind else ''}"
            for k in CAMPOS_CIFRAS:
                chk(sin_w[k] == con_w[k], f"{et}: web cambia {k} con la opción ({sin_w[k]} → {con_w[k]})")
                chk(sin_s[k] == con_s[k], f"{et}: script cambia {k} con la opción ({sin_s[k]} → {con_s[k]})")
                chk(abs(con_w[k] - con_s[k]) < 0.01 if not isinstance(con_s[k], bool) else con_w[k] == con_s[k],
                    f"{et}: con la opción {k} web {con_w[k]} / script {con_s[k]}")
            # sin la opción: no preceptiva si cef <= 2.000 €; preceptiva si no
            esp_sin = not ((24000 if ind else cu) <= 2000)
            chk(sin_w["preceptiva"] is esp_sin and sin_s["preceptiva"] is esp_sin,
                f"{et} sin opción: web {sin_w['preceptiva']} / script {sin_s['preceptiva']} / esperado {esp_sin}")
            # con la opción: preceptiva siempre, mismo texto, con cita y aviso
            chk(con_w["preceptiva"] is True and con_s["preceptiva"] is True,
                f"{et} con opción: web {con_w['preceptiva']} / script {con_s['preceptiva']}")
            chk(con_w["precDesglose"] == con_s["precTexto"], f"{et} con opción: el texto difiere")
            chk("539.1" in con_w["precDesglose"] and "250.1.15.º" in con_w["precDesglose"]
                and "sin jurisprudencia leída" in con_w["precDesglose"] and "párrafo 4.º" in con_w["precDesglose"],
                f"{et} con opción: falta cita, aviso o exclusión del monitorio")
    # la opción no toca otros subtipos: mismo resultado y texto con y sin ella, en los dos motores
    for st in ("verbal", "ordinario", "monitorio_sin", "ar_fp"):
        for cu in (1500, 5000):
            c0 = dict(CTX_BASE, subtipo=st, cuantia=cu, **ipc)
            c1 = dict(c0, tituloVerbalPH=True)
            w0, w1 = _web([c0, c1])
            s0, s1 = _script(C, c0), _script(C, c1)
            chk(w0["preceptiva"] == w1["preceptiva"] and w0["precDesglose"] == w1["precDesglose"]
                and s0["preceptiva"] == s1["preceptiva"] and s0["precTexto"] == s1["precTexto"]
                and all(w0[k] == w1[k] and s0[k] == s1[k] for k in CAMPOS_CIFRAS),
                f"{st} {cu}: la opción altera algo fuera de la ejecución")
    return n, div, res


# ── Reparación del motor 31/10/2026: D1, D2, D4, D5 y céntimo ──────────────
# Importes calculados A MANO desde el texto del PDF (icali-texto-pdf.txt), sin IPC ni redondeo salvo indicación.
# Se comprueban en los TRES cálculos: index.html (motor_web.js), fac-motor.js (generado, motor_fac.js) y calc_icali.py.
FAC_MOTOR = os.environ.get("FAC_MOTOR") or os.path.expanduser("~/Programación/LexArt/MAQUETA/dev-facturar/capa/fac-motor.js")
ORD30 = dict(subtipo="ordinario", cuantia=30000)
CASOS_REPARACION = [
    # D1 · DG 2.ª G · Escala de 30.000 = 4.730,00; tres clientes
    ("D1 distintos (defecto): +40 % /3", dict(ORD30, numClientes=3), "totalCliente", ESC[30000] * 1.4 / 3),
    ("D1 distintos explícito: igual que el defecto", dict(ORD30, numClientes=3, coincidenciaTitulos="distintos"), "totalCliente", ESC[30000] * 1.4 / 3),
    ("D1 idénticos: sin incremento, /3", dict(ORD30, numClientes=3, coincidenciaTitulos="identicos"), "totalCliente", ESC[30000] / 3),
    ("D1 idénticos con 2 clientes: /2", dict(ORD30, numClientes=2, coincidenciaTitulos="identicos"), "totalCliente", ESC[30000] / 2),
    ("D1 parcial, 2 distintos de 3: cada distinto 1,2 × 4.730 / 3", dict(ORD30, numClientes=3, coincidenciaTitulos="parcial", numClientesDistintos=2), "totalCliente", ESC[30000] * 1.2 / 3),
    ("D1 parcial, 2 distintos de 3: cada uno de la mayoría 4.730 / 3", dict(ORD30, numClientes=3, coincidenciaTitulos="parcial", numClientesDistintos=2), "totalClienteMayoria", ESC[30000] / 3),
    ("D1 parcial, 1 distinto de 3: sin incremento (no se cuenta al primero)", dict(ORD30, numClientes=3, coincidenciaTitulos="parcial", numClientesDistintos=1), "totalCliente", ESC[30000] / 3),
    ("D1 parcial, 3 distintos de 3: igual que distintos", dict(ORD30, numClientes=3, coincidenciaTitulos="parcial", numClientesDistintos=3), "totalCliente", ESC[30000] * 1.4 / 3),
    ("D1 parcial con k mayor que n: se limita a n", dict(ORD30, numClientes=3, coincidenciaTitulos="parcial", numClientesDistintos=9), "totalCliente", ESC[30000] * 1.4 / 3),
    ("D1 con un solo cliente la coincidencia no cuenta", dict(ORD30, numClientes=1, coincidenciaTitulos="identicos"), "totalCliente", ESC[30000]),
    ("D1 idénticos: la tasación de costas no cambia", dict(ORD30, numClientes=3, coincidenciaTitulos="identicos"), "totalCostas", ESC[30000]),
    # D2 · DG 3.ª · +50 % sobre el total (núcleo + cautelar + sesiones)
    ("D2 ordinario 30.000 + cautelar 734 (30.000) + 2 sesiones, +50 % sobre el total: minuta",
     dict(ORD30, medidaCautelar=True, cautelarTramite="734", cautelarCuantia=30000, sesionesExtra=2, legislacionEspecial=True), "totalCliente", (ESC[30000] + 0.30 * ESC[30000] + 300) * 1.5),
    ("D2 ídem: costas", dict(ORD30, medidaCautelar=True, cautelarTramite="734", cautelarCuantia=30000, sesionesExtra=2, legislacionEspecial=True), "totalCostas", 9673.50),
    ("D2 sin DG 3.ª: 6.449,00", dict(ORD30, medidaCautelar=True, cautelarTramite="734", cautelarCuantia=30000, sesionesExtra=2), "totalCliente", 6449.00),
    ("D2 verbal 3.000 tras monitorio (48.1) con DG 3.ª: (810 + 150) × 1,5",
     dict(subtipo="verbal", cuantia=3000, derivaMonitorio=True, legislacionEspecial=True, faseAleg=True, faseVista=True), "totalCliente", None),
    # D4 · art. 27.2 · 20 % de la Escala sobre la cuantía discutida, mín. 300
    ("D4 ejecución 30.000, oposición por 5.000: 20 % de 1.190 = 238 → mín. 300", dict(subtipo="ejecucion", cuantia=30000, ejOpo=True, cuantiaDiscutida=5000), "totalCliente", 300.00),
    ("D4 ejecución 30.000, oposición por 20.000: 20 % de 3.590", dict(subtipo="ejecucion", cuantia=30000, ejOpo=True, cuantiaDiscutida=20000), "totalCliente", ESC[20000] * 0.20),
    ("D4 sin cuantía discutida: toda la cuantía (20 % de 4.730)", dict(subtipo="ejecucion", cuantia=30000, ejOpo=True), "totalCliente", ESC[30000] * 0.20),
    ("D4 cuantía discutida 0: toda la cuantía", dict(subtipo="ejecucion", cuantia=30000, ejOpo=True, cuantiaDiscutida=0), "totalCliente", ESC[30000] * 0.20),
    ("D4 con diligencias (27.1 sobre 30.000) + oposición por 5.000", dict(subtipo="ejecucion", cuantia=30000, ejPre=True, ejOpo=True, cuantiaDiscutida=5000), "totalCliente", ESC[30000] * 0.20 + 300),
    ("D4 cuantía discutida sin marcar la oposición: no pesa", dict(subtipo="ejecucion", cuantia=30000, ejPre=True, cuantiaDiscutida=5000), "totalCliente", ESC[30000] * 0.20),
    ("D4 cuantía discutida mayor que la ejecución (intereses y costas): 20 % de 50.000 = 6.630", dict(subtipo="ejecucion", cuantia=30000, ejOpo=True, cuantiaDiscutida=50000), "totalCliente", 6630.00 * 0.20),
    ("D4 la cuantía discutida no cambia el tope del tercio (cuantía 30.000)", dict(subtipo="ejecucion", cuantia=30000, ejOpo=True, cuantiaDiscutida=5000), "lim", 10000.00),
    # D5 · DG 2.ª E · +25 % en todos los subtipos salvo recursos
    ("D5 monitorio sin oposición 10.000 con transacción: 1.025 × 1,25", dict(subtipo="monitorio_sin", cuantia=10000, finalizacion="transaccion"), "totalCliente", 1281.25),
    ("D5 monitorio sin oposición 10.000 sin transacción: 1.025", dict(subtipo="monitorio_sin", cuantia=10000), "totalCliente", 1025.00),
    ("D5 ejecución 30.000 diligencias con transacción: 946 × 1,25", dict(subtipo="ejecucion", cuantia=30000, ejPre=True, finalizacion="transaccion"), "totalCliente", ESC[30000] * 0.20 * 1.25),
    ("D5 en un recurso (apelación) no se aplica", dict(subtipo="recurso_apelacion", cuantia=30000, apelInstancia="ordinario", finalizacion="transaccion"), "totalCliente", None),
    ("D5 ordinario 30.000 completo con transacción (como antes): 4.730 × 1,25", dict(ORD30, faseAleg=True, faseAP=True, faseVista=True, finalizacion="transaccion"), "totalCliente", ESC[30000] * 1.25),
    # Céntimo · cuantía 2.349,50, IPC manual 33,40 %, sin redondeo: costas 889,63 topan en el tercio (783,1666…)
    ("CÉNTIMO base de costas topada a 2 decimales: 783,17", dict(subtipo="verbal", cuantia=2349.5, aplicarIPC=True, ipcManual=33.4), "baseCostas", 783.17),
    ("CÉNTIMO IVA de costas 21 % de 783,17 = 164,4657 → 164,47", dict(subtipo="verbal", cuantia=2349.5, aplicarIPC=True, ipcManual=33.4), "ivaCostas", 164.47),
    ("CÉNTIMO total costas con IVA: 783,17 + 164,47", dict(subtipo="verbal", cuantia=2349.5, aplicarIPC=True, ipcManual=33.4), "conIvaCostas", 947.64),
    ("CÉNTIMO total costas con suplidos 437,50 (sin IVA)", dict(subtipo="verbal", cuantia=2349.5, aplicarIPC=True, ipcManual=33.4, gastosExtras=437.5), "conIvaCostas", 1385.14),
    ("CÉNTIMO IVA de la minuta sin topar: 21 % de 666,89 = 140,0469 → 140,05", dict(subtipo="verbal", cuantia=2349.5), "ivaCliente", 140.05),
]
# Valores que dependen de otro cálculo del mismo motor (se comprueban por diferencia, no por cifra a mano)
CASOS_RELATIVOS = [
    ("D2 verbal 3.000 tras monitorio con DG 3.ª = 1,5 × sin DG 3.ª",
     dict(subtipo="verbal", cuantia=3000, derivaMonitorio=True, faseAleg=True, faseVista=True), dict(legislacionEspecial=True), 1.5),
    ("D2 ejecución con DG 3.ª = 1,5 × sin", dict(subtipo="ejecucion", cuantia=9600, ejPre=True, ejOpo=True, cuantiaDiscutida=3000), dict(legislacionEspecial=True), 1.5),
    ("D5 apelación: la transacción no altera la cifra", dict(subtipo="recurso_apelacion", cuantia=30000, apelInstancia="ordinario"), dict(finalizacion="transaccion"), 1.0),
    ("D5 casación inadmisión: la transacción no altera la cifra", dict(subtipo="recurso_casacion_inadm", cuantia=30000), dict(finalizacion="transaccion"), 1.0),
]
SUBT_TRANSACCION = ["monitorio_lph", "monitorio_sin", "monitorio_con", "verbal", "ordinario", "ar_fp", "ar_precario", "ejecucion"]


def _fac(casos):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(casos, fh)
        ruta = fh.name
    try:
        r = subprocess.run(["node", os.path.join(AQUI, "motor_fac.js"), ruta], capture_output=True, text=True,
                           env=dict(os.environ, FAC_MOTOR=FAC_MOTOR))
        if r.returncode != 0:
            raise RuntimeError(r.stderr[:400])
        return json.loads(r.stdout)
    finally:
        os.remove(ruta)


def comprobar_reparacion():
    """Casos del texto en las tres copias + relaciones (D2, D5) + r2() del script."""
    C = _modulo_calc()
    div, n = [], 0
    ctxs = [dict(CTX_BASE, **k) for _, k, _, _ in CASOS_REPARACION]
    web, fac = _web(ctxs), _fac(ctxs)
    for (nom, _, campo, esp), c, w, f in zip(CASOS_REPARACION, ctxs, web, fac):
        s = _script(C, c)
        vs = {"web": w[campo], "fac-motor": f[campo], "script": s[campo]}
        if esp is None:      # sin cifra a mano: solo paridad entre las tres
            n += 1
            if not (vs["web"] == vs["fac-motor"] and abs(vs["web"] - vs["script"]) < TOL_CRUDO):
                div.append(f"{nom}: {vs}")
            continue
        for quien, v in vs.items():
            n += 1
            if abs(v - esp) >= (TOL if campo in CAMPOS_CENTIMO else TOL_CRUDO):
                div.append(f"{nom}: {quien} da {v}, el texto {esp:.2f}")
    # relaciones
    for nom, base, extra, factor in CASOS_RELATIVOS:
        a, b = dict(CTX_BASE, **base), dict(CTX_BASE, **base, **extra)
        for quien, (ra, rb) in (("web", _web([a, b])), ("fac-motor", _fac([a, b])),
                                ("script", (_script(C, a), _script(C, b)))):
            n += 1
            if abs(rb["totalCliente"] - ra["totalCliente"] * factor) >= TOL_CRUDO:
                div.append(f"{nom}: {quien} {ra['totalCliente']} → {rb['totalCliente']} (factor {factor})")
    # D5 en todos los subtipos del motor salvo recursos: +25 % exacto sobre la cifra sin transacción
    for st in SUBT_TRANSACCION:
        a = dict(CTX_BASE, subtipo=st, cuantia=9600, ejPre=(st == "ejecucion"), faseAleg=True, faseAP=True, faseVista=True)
        b = dict(a, finalizacion="transaccion")
        for quien, (ra, rb) in (("web", _web([a, b])), ("fac-motor", _fac([a, b])), ("script", (_script(C, a), _script(C, b)))):
            n += 1
            if abs(rb["totalCliente"] - ra["totalCliente"] * 1.25) >= TOL_CRUDO:
                div.append(f"D5 {st}: {quien} {ra['totalCliente']} → {rb['totalCliente']} (esperado ×1,25)")
    # r2() del script: mitad hacia arriba sin ruido de coma flotante
    for x, esp in ((164.465, 164.47), (164.535, 164.54), (0.105, 0.11), (1.005, 1.01), (783.1666666666666, 783.17), (2.675, 2.68), (0.1 + 0.2, 0.30)):
        n += 1
        if C.r2(x) != esp:
            div.append(f"script r2({x}) = {C.r2(x)}, esperado {esp}")
    # tercera copia contra la web en TODO el contraste general: igualdad exacta de las cifras
    casos = casos_generales()
    w_all, f_all = _web(casos), _fac(casos)
    for c, w, f in zip(casos, w_all, f_all):
        n += 1
        if w != f:
            malos = [k for k in w if w.get(k) != f.get(k)]
            div.append(f"web/fac-motor {c['subtipo']} {c['cuantia']}: " + ", ".join(f"{k} {w.get(k)}/{f.get(k)}" for k in malos[:3]))
    return n, div


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
    nph, divph, _ = comprobar_materia_ph()
    print(f"\nVerbal por materia (cuotas LPH) — comprobaciones: {nph}  ·  correctas: {nph - len(divph)}  ·  fallan: {len(divph)}")
    for d in divph:
        print("  ", d)
    ntv, divtv, _ = comprobar_titulo_verbal_ph()
    print(f"\nEjecución de un verbal de cuotas (--titulo-verbal-ph) — comprobaciones: {ntv}  ·  correctas: {ntv - len(divtv)}  ·  fallan: {len(divtv)}")
    for d in divtv:
        print("  ", d)
    nr, divr = comprobar_reparacion()
    print(f"\nReparación 31/10/2026 (D1, D2, D4, D5, céntimo; web = fac-motor = script) — comprobaciones: {nr}  ·  correctas: {nr - len(divr)}  ·  fallan: {len(divr)}")
    for d in divr:
        print("  ", d)
    total = len(casos) + n51 + len(CASOS_51_1) + n511s + ng + nt + nph + ntv + nr
    malos = len(div) + len(err) + len(div51) + len(div511) + len(div511s) + len(divg) + len(divt) + len(divph) + len(divtv) + len(divr)
    print(f"\nTOTAL: {total} casos · {total - malos} coinciden · {malos} divergen")

    return 1 if (div or err or div51 or div511 or div511s or divg or divt or divph or divtv or divr) else 0


if __name__ == "__main__":
    sys.exit(main())
