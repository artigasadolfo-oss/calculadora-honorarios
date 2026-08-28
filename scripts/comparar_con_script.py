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
    return 1 if (div or err) else 0


if __name__ == "__main__":
    sys.exit(main())
