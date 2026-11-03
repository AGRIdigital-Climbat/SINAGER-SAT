#!/usr/bin/env python3
"""
Migración de datos relacionales para pronóstico de largo plazo:
1. Poblar catálogos: categoria_pronostico, escenario, recomendacion
2. Migrar tablas relacionales: pronostico_largo_item, escenario_estacional, pronostico_largo_recomendacion

Desde MariaDB (t_observacion_pronostico, t_pronostico_estacional, t_escenario_estacional, t_recomendacion_local)
Hacia PostgreSQL (sinb.pronostico_largo_item, sinb.escenario_estacional, sinb.pronostico_largo_recomendacion)
"""

import re
import psycopg2
from collections import defaultdict

PG_CONFIG = {
    'host': '127.0.0.1',
    'port': 5432,
    'database': 'db_sinagersat',
    'user': 'sinagersat',
    'password': '12345678'
}


def parse_row_fields(row_str):
    """Parsea una fila de VALUES de SQL separando por comas fuera de strings"""
    fields = []
    current = ''
    in_string = False
    
    for i, char in enumerate(row_str):
        if char == "'" and (i == 0 or row_str[i-1] != '\\'):
            in_string = not in_string
            current += char
        elif char == ',' and not in_string:
            fields.append(current.strip().strip("'"))
            current = ''
        else:
            current += char
    
    if current:
        fields.append(current.strip().strip("'"))
    
    return fields


def parse_insert_values(content, table_name):
    """Extrae todos los VALUES de un INSERT INTO table_name"""
    pattern = rf"INSERT INTO `{table_name}` VALUES (.+?);"
    matches = re.findall(pattern, content, re.DOTALL)
    
    all_rows = []
    for match in matches:
        match = match.strip()
        current_row = ''
        paren_depth = 0
        in_string = False
        rows = []
        
        i = 0
        while i < len(match):
            char = match[i]
            
            if char == "'" and (i == 0 or match[i-1] != '\\'):
                in_string = not in_string
                current_row += char
            elif char == '(' and not in_string:
                paren_depth += 1
                current_row += char
            elif char == ')' and not in_string:
                paren_depth -= 1
                current_row += char
                if paren_depth == 0:
                    rows.append(current_row.strip('(), '))
                    current_row = ''
            elif char == ',' and not in_string and paren_depth == 0:
                current_row = current_row.strip()
                if current_row:
                    rows.append(current_row)
                current_row = ''
            else:
                current_row += char
            
            i += 1
        
        if current_row.strip():
            rows.append(current_row.strip('(), '))
        
        for row in rows:
            fields = parse_row_fields(row)
            if fields:
                all_rows.append(fields)
    
    return all_rows


def load_mdb_tables(filepath):
    """Carga las tablas necesarias desde el dump de MariaDB"""
    print(f"Leyendo dump MariaDB: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    data = {}
    tables = [
        't_pronostico_estacional',
        't_escenario_estacional', 
        't_recomendacion_local',
        't_observacion_pronostico',
        't_observacion_recomendacion',
    ]
    
    for table in tables:
        print(f"  Parseando {table}...", end=' ')
        data[table] = parse_insert_values(content, table)
        print(f"→ {len(data[table])} registros")
    
    return data


def build_catalog_mappings(pg_conn, mdb_data):
    """
    Crea mapeos entre MariaDB y PostgreSQL para catálogos.
    Retorna:
    - mdb_to_pg_categoria: dict id_mdb -> id_pg (UUID)
    - mdb_to_pg_escenario: dict id_mdb -> id_pg (UUID)
    - mdb_to_pg_recomendacion: dict id_mdb -> id_pg (UUID)
    """
    print("\nConstruyendo mapeos de catálogos...")
    
    mdb_to_pg_categoria = {}
    mdb_to_pg_escenario = {}
    mdb_to_pg_recomendacion = {}
    
    with pg_conn.cursor() as cur:
        # =====================================================================
        # CATEGORIAS: t_pronostico_estacional -> sinb.categoria_pronostico
        # =====================================================================
        print("\n1. CATEGORIAS (t_pronostico_estacional -> categoria_pronostico)")
        
        # Obtener categorías únicas de MariaDB
        categorias_mdb = {}
        for row in mdb_data['t_pronostico_estacional']:
            id_mdb = int(row[0])
            nombre = row[1]
            estado = row[2] if len(row) > 2 else 'ACTIVO'
            if estado == 'ACTIVO':
                categorias_mdb[id_mdb] = nombre
        
        nombres_unicos = set(categorias_mdb.values())
        print(f"  Categorías únicas en MariaDB: {len(nombres_unicos)} ({', '.join(sorted(nombres_unicos))})")
        
        # Obtener categorías existentes en PostgreSQL
        cur.execute("SELECT id, nombre FROM sinb.categoria_pronostico")
        pg_categorias = {row[1]: row[0] for row in cur.fetchall()}
        print(f"  Categorías existentes en PostgreSQL: {len(pg_categorias)}")
        
        # Insertar categorías faltantes
        for nombre in nombres_unicos:
            if nombre not in pg_categorias:
                cur.execute("""
                    INSERT INTO sinb.categoria_pronostico (nombre)
                    VALUES (%s) RETURNING id
                """, (nombre,))
                pg_categorias[nombre] = cur.fetchone()[0]
                print(f"    + Insertada: {nombre}")
        
        pg_conn.commit()
        
        # Crear mapeo id_mdb -> id_pg
        for id_mdb, nombre in categorias_mdb.items():
            mdb_to_pg_categoria[id_mdb] = pg_categorias[nombre]
        
        print(f"  ✓ Mapeo completado: {len(mdb_to_pg_categoria)} registros")
        
        # =====================================================================
        # ESCENARIOS: t_escenario_estacional -> sinb.escenario
        # =====================================================================
        print("\n2. ESCENARIOS (t_escenario_estacional -> escenario)")
        
        # Obtener escenarios únicos de MariaDB
        escenarios_mdb = {}
        for row in mdb_data['t_escenario_estacional']:
            id_mdb = int(row[0])
            nombre = row[1]
            estado = row[2] if len(row) > 2 else 'ACTIVO'
            if estado == 'ACTIVO':
                escenarios_mdb[id_mdb] = nombre
        
        nombres_unicos_esc = set(escenarios_mdb.values())
        print(f"  Escenarios únicos en MariaDB: {len(nombres_unicos_esc)}")
        print(f"    Ejemplos: {list(nombres_unicos_esc)[:10]}")
        
        # Obtener escenarios existentes en PostgreSQL
        cur.execute("SELECT id, nombre FROM sinb.escenario")
        pg_escenarios = {row[1]: row[0] for row in cur.fetchall()}
        print(f"  Escenarios existentes en PostgreSQL: {len(pg_escenarios)}")
        
        # Insertar escenarios faltantes
        insertados_esc = 0
        for nombre in nombres_unicos_esc:
            if nombre not in pg_escenarios:
                cur.execute("""
                    INSERT INTO sinb.escenario (nombre)
                    VALUES (%s) RETURNING id
                """, (nombre,))
                pg_escenarios[nombre] = cur.fetchone()[0]
                insertados_esc += 1
        
        pg_conn.commit()
        print(f"    + Insertados: {insertados_esc} escenarios nuevos")
        
        # Crear mapeo id_mdb -> id_pg
        for id_mdb, nombre in escenarios_mdb.items():
            mdb_to_pg_escenario[id_mdb] = pg_escenarios[nombre]
        
        print(f"  ✓ Mapeo completado: {len(mdb_to_pg_escenario)} registros")
        
        # =====================================================================
        # RECOMENDACIONES: t_recomendacion_local -> sinb.recomendacion
        # =====================================================================
        print("\n3. RECOMENDACIONES (t_recomendacion_local -> recomendacion)")
        
        # Obtener recomendaciones únicas de MariaDB
        recomendaciones_mdb = {}
        for row in mdb_data['t_recomendacion_local']:
            id_mdb = int(row[0])
            nombre = row[1]
            estado = row[2] if len(row) > 2 else 'ACTIVO'
            if estado == 'ACTIVO':
                recomendaciones_mdb[id_mdb] = nombre
        
        nombres_unicos_rec = set(recomendaciones_mdb.values())
        print(f"  Recomendaciones únicas en MariaDB: {len(nombres_unicos_rec)} ({', '.join(sorted(nombres_unicos_rec))})")
        
        # Obtener recomendaciones existentes en PostgreSQL
        cur.execute("SELECT id, nombre FROM sinb.recomendacion")
        pg_recomendaciones = {row[1]: row[0] for row in cur.fetchall()}
        print(f"  Recomendaciones existentes en PostgreSQL: {len(pg_recomendaciones)}")
        
        # Insertar recomendaciones faltantes
        insertados_rec = 0
        for nombre in nombres_unicos_rec:
            if nombre not in pg_recomendaciones:
                cur.execute("""
                    INSERT INTO sinb.recomendacion (nombre)
                    VALUES (%s) RETURNING id
                """, (nombre,))
                pg_recomendaciones[nombre] = cur.fetchone()[0]
                insertados_rec += 1
        
        pg_conn.commit()
        print(f"    + Insertadas: {insertados_rec} recomendaciones nuevas")
        
        # Crear mapeo id_mdb -> id_pg
        for id_mdb, nombre in recomendaciones_mdb.items():
            mdb_to_pg_recomendacion[id_mdb] = pg_recomendaciones[nombre]
        
        print(f"  ✓ Mapeo completado: {len(mdb_to_pg_recomendacion)} registros")
    
    return mdb_to_pg_categoria, mdb_to_pg_escenario, mdb_to_pg_recomendacion


def get_observacion_to_pronostico_largo_mapping(pg_conn):
    """
    Obtiene el mapeo entre id_observacion_mdb -> id_pronostico_largo_pg
    Usamos el código SINB-{obs_id:04d} que se generó en la migración anterior
    """
    print("\n4. Obteniendo mapeo observacion_mdb -> pronostico_largo_pg...")
    
    mapping = {}
    with pg_conn.cursor() as cur:
        cur.execute("""
            SELECT codigo, id FROM sinb.pronostico_largo
        """)
        for row in cur.fetchall():
            codigo = row[0]  # ej: SINB-0001
            id_pg = row[1]
            # Extraer número del código
            match = re.match(r'SINB-(\d+)', codigo)
            if match:
                obs_id_mdb = int(match.group(1))
                mapping[obs_id_mdb] = id_pg
    
    print(f"  ✓ Mapeo obtenido: {len(mapping)} registros")
    return mapping


def migrate_pronostico_largo_items(pg_conn, mdb_data, mdb_to_pg_categoria, mdb_to_pg_escenario, obs_to_pronostico):
    """
    Migrar t_observacion_pronostico -> sinb.pronostico_largo_item + sinb.escenario_estacional
    
    Estructura MariaDB:
    - t_observacion_pronostico: id, t_observacion_id_observacion, t_pronostico_estacional_id_pronostico_estacional
    - t_pronostico_estacional: id, nombre (categoria)
    - t_escenario_estacional: id, nombre, pronostico_estacional_id (FK a t_pronostico_estacional)
    
    Cada observación puede tener múltiples pronósticos (categorías), y cada categoría tiene un escenario.
    
    PostgreSQL destino:
    - sinb.pronostico_largo_item: id_pronostico_largo, id_categoria
    - sinb.escenario_estacional: id_pronostico_largo_item, id_escenario, probabilidad
    """
    print("\n5. Migrando items de pronóstico (pronostico_largo_item + escenario_estacional)...")
    
    # Agrupar pronósticos por observación
    # t_observacion_pronostico: (id, obs_id, pronostico_estacional_id)
    obs_pronosticos = defaultdict(list)
    for row in mdb_data['t_observacion_pronostico']:
        obs_id = int(row[1])
        pronostico_estacional_id = int(row[2])
        obs_pronosticos[obs_id].append(pronostico_estacional_id)
    
    # Para cada pronostico_estacional, obtener sus escenarios
    # t_escenario_estacional: (id, nombre, pronostico_estacional_id)
    escenarios_por_pronostico = defaultdict(list)
    for row in mdb_data['t_escenario_estacional']:
        escenario_id = int(row[0])
        pronostico_estacional_id = int(row[3])
        escenarios_por_pronostico[pronostico_estacional_id].append(escenario_id)
    
    print(f"  Observaciones con pronósticos: {len(obs_pronosticos)}")
    print(f"  Categorías con escenarios: {len(escenarios_por_pronostico)}")
    
    insertados_items = 0
    insertados_escenarios = 0
    errores = 0
    sin_mapeo = 0
    
    with pg_conn.cursor() as cur:
        for obs_id_mdb, pronostico_ids_mdb in obs_pronosticos.items():
            # Obtener id_pronostico_largo_pg
            id_pronostico_largo_pg = obs_to_pronostico.get(obs_id_mdb)
            if not id_pronostico_largo_pg:
                sin_mapeo += 1
                continue
            
            # Para cada categoría asociada a esta observación
            for pron_estacional_id_mdb in pronostico_ids_mdb:
                id_categoria_pg = mdb_to_pg_categoria.get(pron_estacional_id_mdb)
                if not id_categoria_pg:
                    errores += 1
                    continue
                
                # Insertar item (categoría)
                try:
                    cur.execute("""
                        INSERT INTO sinb.pronostico_largo_item 
                        (id_pronostico_largo, id_categoria, orden, creado_en)
                        VALUES (%s, %s, 0, NOW())
                        RETURNING id
                    """, (id_pronostico_largo_pg, id_categoria_pg))
                    
                    id_item_pg = cur.fetchone()[0]
                    insertados_items += 1
                    
                    # Insertar escenarios asociados a esta categoría
                    escenario_ids_mdb = escenarios_por_pronostico.get(pron_estacional_id_mdb, [])
                    for escenario_mdb_id in escenario_ids_mdb:
                        id_escenario_pg = mdb_to_pg_escenario.get(escenario_mdb_id)
                        if id_escenario_pg:
                            cur.execute("""
                                INSERT INTO sinb.escenario_estacional
                                (id_pronostico_largo_item, id_escenario, probabilidad)
                                VALUES (%s, %s, 100)
                            """, (id_item_pg, id_escenario_pg))
                            insertados_escenarios += 1
                    
                except psycopg2.IntegrityError as e:
                    # Puede haber duplicados si ya existe la misma categoría para este pronóstico
                    errores += 1
                    if insertados_items % 100 == 0:
                        print(f"    → {insertados_items} items migrados...")
    
    pg_conn.commit()
    print(f"  Sin mapeo: {sin_mapeo}")
    print(f"  ✓ Items insertados: {insertados_items}")
    print(f"  ✓ Escenarios insertados: {insertados_escenarios}")
    print(f"  Errores: {errores}")
    
    return insertados_items, insertados_escenarios


def migrate_recomendaciones(pg_conn, mdb_data, mdb_to_pg_recomendacion, obs_to_pronostico):
    """
    Migrar t_observacion_recomendacion -> sinb.pronostico_largo_recomendacion
    
    Estructura MariaDB:
    - t_observacion_recomendacion: id, t_observacion_id_observacion, t_recomendacion_local_id_recomendacion_local
    
    PostgreSQL destino:
    - sinb.pronostico_largo_recomendacion: id_pronostico_largo, id_recomendacion
    """
    print("\n6. Migrando recomendaciones (pronostico_largo_recomendacion)...")
    
    insertados = 0
    sin_mapeo = 0
    errores = 0
    
    with pg_conn.cursor() as cur:
        for row in mdb_data['t_observacion_recomendacion']:
            obs_id_mdb = int(row[1])
            recomendacion_local_id_mdb = int(row[2])
            
            # Obtener id_pronostico_largo_pg
            id_pronostico_largo_pg = obs_to_pronostico.get(obs_id_mdb)
            if not id_pronostico_largo_pg:
                sin_mapeo += 1
                continue
            
            # Obtener id_recomendacion_pg
            id_recomendacion_pg = mdb_to_pg_recomendacion.get(recomendacion_local_id_mdb)
            if not id_recomendacion_pg:
                errores += 1
                continue
            
            try:
                cur.execute("""
                    INSERT INTO sinb.pronostico_largo_recomendacion
                    (id_pronostico_largo, id_recomendacion)
                    VALUES (%s, %s)
                """, (id_pronostico_largo_pg, id_recomendacion_pg))
                insertados += 1
                
            except psycopg2.IntegrityError:
                # Duplicado, ya existe
                pass
    
    pg_conn.commit()
    print(f"  Sin mapeo: {sin_mapeo}")
    print(f"  ✓ Recomendaciones insertadas: {insertados}")
    print(f"  Errores: {errores}")
    
    return insertados


def main():
    print("=" * 70)
    print("MIGRACIÓN DE DATOS RELACIONALES - PRONÓSTICO LARGO PLAZO")
    print("=" * 70)
    
    print("\nConectando a PostgreSQL...")
    pg_conn = psycopg2.connect(**PG_CONFIG)
    print("  ✓ Conexión exitosa")
    
    # Cargar datos desde MariaDB dump
    mdb_data = load_mdb_tables('SINB/sinb_20260714.sql')
    
    # Construir mapeos de catálogos
    mdb_to_pg_categoria, mdb_to_pg_escenario, mdb_to_pg_recomendacion = \
        build_catalog_mappings(pg_conn, mdb_data)
    
    # Obtener mapeo observacion_mdb -> pronostico_largo_pg
    obs_to_pronostico = get_observacion_to_pronostico_largo_mapping(pg_conn)
    
    # Migrar items de pronóstico
    items, escenarios = migrate_pronostico_largo_items(
        pg_conn, mdb_data, 
        mdb_to_pg_categoria, mdb_to_pg_escenario, 
        obs_to_pronostico
    )
    
    # Migrar recomendaciones
    recomendaciones = migrate_recomendaciones(
        pg_conn, mdb_data,
        mdb_to_pg_recomendacion,
        obs_to_pronostico
    )
    
    print(f"\n{'=' * 70}")
    print("MIGRACIÓN COMPLETADA")
    print(f"{'=' * 70}")
    print(f"  Categorías mapeadas: {len(mdb_to_pg_categoria)}")
    print(f"  Escenarios mapeados: {len(mdb_to_pg_escenario)}")
    print(f"  Recomendaciones mapeadas: {len(mdb_to_pg_recomendacion)}")
    print(f"  Items insertados: {items}")
    print(f"  Escenarios insertados: {escenarios}")
    print(f"  Recomendaciones insertadas: {recomendaciones}")
    print(f"{'=' * 70}")
    
    pg_conn.close()


if __name__ == '__main__':
    main()
