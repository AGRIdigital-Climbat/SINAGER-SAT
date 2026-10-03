#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Importa el historico legacy 'BD EDAN 2002-2025Limpia.xlsx' al sistema EDAN.

Cada fila compatible del Excel se importa como UN EDAN consolidado:
  - cabecera edan.edan: estado 'Aprobado ajuste' (5), id_usuario_ugr NULL,
    procedencia='excel_legacy', codigo_edan = {codigo_ine}/{anio}/{seq}
  - UNA localidad vinculada (id_edan = cabecera) con las secciones de danos y
    los flags imp_* coherentes (solo se crea fila de seccion si hay dato).
  - idempotente: si origen_id (BD_EDAN-{ID}) ya fue importado, se omite.

Filtros de compatibilidad (solo_compatibles=True, default):
  sin geografia  -> el codigo INE no esta en la jerarquia geografica
  sin evento homologado -> el evento crudo no tiene mapeo a tipo_evento
  lugar vacio    -> LUGAR en blanco
  lugar generico -> LUGAR en {VARIAS COMUNIDADES, OTROS, SIN DATOS, ...}
  sin fecha ni anio -> sin anio numerico ni fecha parseable

Uso:
  python3 scripts/importar_bdlimpia.py [ruta_excel] [--simular|--importar]
       [--completos]      # importar tambien filas incompatibles (no recomendado)

  DATABASE_URL=postgresql://... python3 scripts/importar_bdlimpia.py ...  # BD alternativa
"""
import argparse
import os
import sys

EXCEL_DEFAULT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "BD EDAN 2002-2025Limpia.xlsx")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sinagersat:12345678@127.0.0.1:5432/db_sinagersat",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("excel", nargs="?", default=EXCEL_DEFAULT,
                        help="Ruta al archivo .xlsx (default: repo/BD EDAN 2002-2025Limpia.xlsx)")
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--simular", action="store_true",
                      help="Solo contar lo que se importaria (no escribe en BD)")
    modo.add_argument("--importar", action="store_true",
                      help="Importar de verdad (default)")
    parser.add_argument("--completos", action="store_true",
                        help="Importar tambien filas incompatibles")
    args = parser.parse_args()

    if not os.path.isfile(args.excel):
        sys.exit("No existe el archivo: %s" % args.excel)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from api.edan.service_importar import importar_excel

    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    try:
        res = importar_excel(
            db, args.excel,
            solo_compatibles=not args.completos,
            modo="importar" if args.importar and not args.simular else "simular",
            id_usuario=None,
        )
        print("=" * 60)
        for k in ("archivo", "procesadas", "insertadas", "omitidas", "errores",
                  "id_importacion"):
            print("  %-15s %s" % (k + ":", res[k]))
        if res["por_motivo"]:
            print("  omitidas_por_motivo:")
            for m, n in res["por_motivo"].items():
                print("    %-22s %d" % (m, n))
        if res["secciones_insertadas"]:
            print("  secciones_insertadas:")
            for m, n in res["secciones_insertadas"].items():
                print("    %-45s %d" % (m, n))
    finally:
        db.close()


if __name__ == "__main__":
    main()