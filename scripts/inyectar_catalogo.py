#!/usr/bin/env python3
"""Inyecta datos/catalogo_icali.json (arts. 1-68 del baremo civil ICALI) en:
  - index.html  entre /*@CATALOGO@*/ y /*@FIN-CATALOGO@*/  (con «literal», para la ficha del artículo)
  - calc_icali.py entre # @CATALOGO@ y # @FIN-CATALOGO@     (sin «literal»)
Fuente única de datos: el JSON. No edite el bloque a mano: edite el JSON y vuelva a ejecutar esto.
Después: generar_motor.py y las pruebas de paridad (comparar_con_script.py)."""
import json, os, re, sys
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON = os.path.join(RAIZ, 'datos', 'catalogo_icali.json')
WEB = os.path.join(RAIZ, 'index.html')
PY = os.path.expanduser('~/.hermes/skills/legal-esp/honorarios-icali/scripts/calc_icali.py')

def main():
    cat = json.load(open(JSON, encoding='utf-8'))
    ids = [e['id'] for e in cat]
    assert len(ids) == len(set(ids)), 'ids duplicados en el catálogo'
    for e in cat:
        if e.get('remite') and e['remite'] not in ids and not e['remite'].startswith('sub:'):
            pass  # remisión a un subtipo existente de la calculadora (verbal, ejecucion…)
    web_js = 'var CATALOGO = ' + json.dumps(cat, ensure_ascii=False, separators=(',', ':')) + ';'
    sin_lit = [{k: v for k, v in e.items() if k != 'literal'} for e in cat]
    py_txt = 'CATALOGO = json.loads(' + repr(json.dumps(sin_lit, ensure_ascii=False, separators=(',', ':'))) + ')'
    for ruta, ini, fin, cuerpo in ((WEB, '/*@CATALOGO@*/', '/*@FIN-CATALOGO@*/', web_js),
                                   (PY, '# @CATALOGO@', '# @FIN-CATALOGO@', py_txt)):
        s = open(ruta, encoding='utf-8').read()
        assert s.count(ini) == 1 and s.count(fin) == 1, f'marcadores ausentes o repetidos en {ruta}'
        a = s.index(ini) + len(ini); b = s.index(fin)
        s2 = s[:a] + '\n' + cuerpo + '\n' + s[b:]
        if s2 != s:
            open(ruta, 'w', encoding='utf-8').write(s2)
        print(f'{os.path.basename(ruta)}: {len(cat)} entradas inyectadas')

if __name__ == '__main__':
    main()
