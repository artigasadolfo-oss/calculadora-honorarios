#!/usr/bin/env python3
"""
Contrasta el cálculo del art. 50 (apelación) de index.html contra calc_icali.py.

Lee scripts/casos_app.json (generado por test_apelacion_art50.js extrayendo las
funciones REALES del HTML) y ejecuta el mismo caso con calc_icali.py, comparando
el importe base antes de IPC y redondeo.

Uso:  python3 scripts/comparar_con_script.py
Salida: tabla de divergencias; exit 1 si hay alguna.
"""
import json, subprocess, re, sys, os

AQUI = os.path.dirname(os.path.abspath(__file__))
CASOS = os.path.join(AQUI, "casos_app.json")
CALC = os.path.expanduser(
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

    return 1 if (div or err or div51 or div511 or div511s) else 0


if __name__ == "__main__":
    sys.exit(main())
