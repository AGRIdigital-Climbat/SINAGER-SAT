#!/usr/bin/env python3
"""
Migración de datos históricos de pronóstico de largo plazo (estacional)
MariaDB (SINB) → PostgreSQL (MD15 estructura anidada)

Mapeo de usuarios por número de celular
Cadena biocultural: se elige una cadena válida por grupo (indicador→característica→comportamiento)
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

GRUPO_MDB_TO_NOMBRE = {
    1: 'Animales',
    2: 'Plantas', 
    3: 'Condiciones meteorológicas',
    4: 'Constelaciones',
    5: 'Eventos atmosféricos',
    6: 'Hidrológicos',
    7: 'Eventos tradicionales',
}

def parse_row_fields(row_str):
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

def parse_values(content, table_name):
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

def load_mariaDB_dump(filepath):
    print(f"Leyendo dump MariaDB: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    data = {}
    tables = [
        't_usuario', 't_comunidad', 't_observacion',
        't_observacion_usuario', 't_observacion_grupo',
        't_usuario_comunidad',
    ]
    
    for table in tables:
        print(f"  Parseando {table}...", end=' ')
        data[table] = parse_values(content, table)
        print(f"→ {len(data[table])} registros")
    
    return data

def build_pg_catalogs(pg_conn):
    print("Cargando catálogos desde PostgreSQL...")
    
    catalogs = {}
    
    with pg_conn.cursor() as cur:
        # Grupos
        cur.execute("SELECT id, nombre FROM sinb.grupo")
        catalogs['grupo'] = {row[1]: row[0] for row in cur.fetchall()}
        print(f"  Grupos: {len(catalogs['grupo'])}")
        
        # Cadenas completas por grupo: indicador→característica→comportamiento
        cur.execute("""
            SELECT g.id as id_grupo, i.id as id_indicador, c.id as id_caracteristica, b.id as id_comportamiento
            FROM sinb.grupo g
            JOIN sinb.indicador_natural i ON i.id_grupo = g.id
            JOIN sinb.caracteristica c ON c.id_indicador_natural = i.id
            JOIN sinb.comportamiento b ON b.id_caracteristica = c.id
            ORDER BY g.nombre, i.id, c.id, b.id
        """)
        
        cadenas_por_grupo = defaultdict(list)
        for row in cur.fetchall():
            id_grupo, id_indicador, id_caracteristica, id_comportamiento = row
            cadenas_por_grupo[id_grupo].append({
                'indicador': id_indicador,
                'caracteristica': id_caracteristica,
                'comportamiento': id_comportamiento,
            })
        
        catalogs['cadenas_por_grupo'] = dict(cadenas_por_grupo)
        print(f"  Cadenas por grupo: {len(cadenas_por_grupo)} grupos")
        for grupo_id, cadenas in cadenas_por_grupo.items():
            print(f"    → {grupo_id}: {len(cadenas)} cadenas")
        
        # Mapeo usuarios por celular
        cur.execute("SELECT celular, id_usuario FROM usuarios.usuario WHERE celular IS NOT NULL AND celular != ''")
        catalogs['usuario_celular'] = {str(row[0]): row[1] for row in cur.fetchall()}
        print(f"  Usuarios por celular: {len(catalogs['usuario_celular'])}")
    
    return catalogs

def build_mdb_lookups(mdb_data, catalogs):
    print("Construyendo lookups de MariaDB...")
    
    lookups = {}
    
    # Mapeo usuario MDB → PG por celular
    lookups['usuario_mdb_pg'] = {}
    for row in mdb_data['t_usuario']:
        mdb_id = int(row[0])
        celular = row[6] if len(row) > 6 else None
        if celular:
            pg_id = catalogs['usuario_celular'].get(str(celular))
            if pg_id:
                lookups['usuario_mdb_pg'][mdb_id] = pg_id
    
    print(f"  Usuarios mapeados: {len(lookups['usuario_mdb_pg'])} de {len(mdb_data['t_usuario'])}")
    
    # Grupo por observación
    # Necesitamos parsear t_observacion_grupo del SQL directamente
    lookups['obs_grupo'] = {}
    
    # Usuarios por observación
    lookups['obs_usuarios_pg'] = defaultdict(list)
    
    # Usuario → Comunidad
    lookups['usuario_comunidad'] = {}
    for row in mdb_data['t_usuario_comunidad']:
        usuario_id = int(row[1])
        comunidad_id = int(row[2])
        lookups['usuario_comunidad'][usuario_id] = comunidad_id
    
    # Comunidad info
    lookups['comunidad'] = {}
    
    return lookups

def get_municipio(pg_conn, comunidad_info):
    try:
        with pg_conn.cursor() as cur:
            cur.execute("""
                SELECT m.id FROM shared.municipio m 
                WHERE ST_Contains(m.geom, ST_SetSRID(ST_Point(%s, %s), 4326))
                LIMIT 1
            """, (comunidad_info['lon'], comunidad_info['lat']))
            result = cur.fetchone()
            if result:
                return result[0]
    except:
        pass
    
    nombre = comunidad_info['nombre'].lower()
    try:
        with pg_conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM shared.municipio 
                WHERE LOWER(nombre) LIKE %s 
                LIMIT 1
            """, (f'%{nombre}%',))
            result = cur.fetchone()
            if result:
                return result[0]
    except:
        pass
    
    return None

def migrate_data(pg_conn, mdb_data, catalogs, mdb_lookups, filepath):
    # Parsear tablas adicionales incrementalmente
    print("\nParseando tablas adicionales...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # t_observacion
    print("  Parseando t_observacion...", end=' ')
    observaciones = parse_values(content, 't_observacion')
    print(f"→ {len(observaciones)} registros")
    
    # t_observacion_grupo
    print("  Parseando t_observacion_grupo...", end=' ')
    obs_grupo_data = parse_values(content, 't_observacion_grupo')
    obs_grupo = {int(row[1]): int(row[2]) for row in obs_grupo_data}
    print(f"→ {len(obs_grupo)} registros")
    
    # t_observacion_usuario
    print("  Parseando t_observacion_usuario...", end=' ')
    obs_usuario_data = parse_values(content, 't_observacion_usuario')
    obs_usuarios_mdb = defaultdict(list)
    for row in obs_usuario_data:
        obs_id = int(row[1])
        usuario_mdb_id = int(row[2])
        obs_usuarios_mdb[obs_id].append(usuario_mdb_id)
    print(f"→ {len(obs_usuarios_mdb)} registros")
    
    # t_comunidad
    print("  Parseando t_comunidad...", end=' ')
    comunidades = parse_values(content, 't_comunidad')
    comunidad_info = {}
    for row in comunidades:
        com_id = int(row[0])
        comunidad_info[com_id] = {
            'nombre': row[2],
            'lat': float(row[3]),
            'lon': float(row[4]),
        }
    print(f"→ {len(comunidad_info)} registros")
    
    print(f"\nMigrando {len(observaciones)} observaciones...")
    
    insertados = 0
    errores = 0
    sin_municipio = 0
    sin_usuario = 0
    sin_grupo = 0
    
    with pg_conn.cursor() as cur:
        for obs in observaciones:
            obs_id = int(obs[0])
            fecha_obs = obs[1]
            fecha_inicio = obs[2]
            fecha_fin = obs[3]
            
            # Obtener grupo
            grupo_mdb = obs_grupo.get(obs_id)
            if not grupo_mdb:
                sin_grupo += 1
                continue
            
            # Mapear grupo
            grupo_nombre = GRUPO_MDB_TO_NOMBRE.get(grupo_mdb)
            grupo_pg = catalogs['grupo'].get(grupo_nombre) if grupo_nombre else None
            if not grupo_pg:
                sin_grupo += 1
                continue
            
            # Elegir una cadena válida para este grupo
            cadenas = catalogs['cadenas_por_grupo'].get(grupo_pg, [])
            if not cadenas:
                errores += 1
                continue
            
            # Elegir la primera cadena (o usar un hash del obs_id para distribuir)
            cadena = cadenas[obs_id % len(cadenas)]
            indicador_pg = cadena['indicador']
            carac_pg = cadena['caracteristica']
            comp_pg = cadena['comportamiento']
            
            # Obtener usuarios mapeados
            usuario_mdb_ids = obs_usuarios_mdb.get(obs_id, [])
            usuario_pg_ids = [mdb_lookups['usuario_mdb_pg'].get(uid) for uid in usuario_mdb_ids]
            usuario_pg_ids = [uid for uid in usuario_pg_ids if uid]
            
            # Obtener municipio
            id_municipio = None
            for uid_mdb in usuario_mdb_ids:
                com_id = mdb_lookups['usuario_comunidad'].get(uid_mdb)
                if com_id and com_id in comunidad_info:
                    id_municipio = get_municipio(pg_conn, comunidad_info[com_id])
                    if id_municipio:
                        break
            
            if not id_municipio:
                sin_municipio += 1
            
            id_usuario_subio = usuario_pg_ids[0] if usuario_pg_ids else None
            
            if not id_usuario_subio:
                sin_usuario += 1
                continue
            
            codigo = f"SINB-{obs_id:04d}"
            
            try:
                cur.execute("""
                    INSERT INTO sinb.pronostico_largo 
                    (codigo, fecha_emision, periodo_inicio, periodo_fin,
                     id_usuario_subio, id_municipio,
                     id_grupo, id_indicador_natural, id_caracteristica, id_comportamiento,
                     es_ingesta, creado_en, actualizado_en)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, NOW(), NOW())
                    RETURNING id
                """, (codigo, fecha_obs, fecha_inicio, fecha_fin,
                      id_usuario_subio, id_municipio,
                      grupo_pg, indicador_pg, carac_pg, comp_pg))
                
                id_pronostico_largo = cur.fetchone()[0]
                
                for uid_pg in usuario_pg_ids:
                    cur.execute("""
                        INSERT INTO sinb.pronostico_largo_observador 
                        (id_pronostico_largo, id_usuario)
                        VALUES (%s, %s)
                    """, (id_pronostico_largo, uid_pg))
                
                insertados += 1
                
                if insertados % 50 == 0:
                    pg_conn.commit()
                    print(f"  → {insertados} migradas...")
                    
            except Exception as e:
                errores += 1
                print(f"  Error en obs {obs_id}: {e}")
    
    pg_conn.commit()
    print(f"  Sin grupo válido: {sin_grupo}")
    print(f"  Sin usuario mapeado: {sin_usuario}")
    print(f"  Sin municipio: {sin_municipio}")
    return insertados, errores

def main():
    print("=" * 70)
    print("MIGRACIÓN PRONÓSTICO DE LARGO PLAZO (ESTACIONAL)")
    print("=" * 70)
    
    print("\nConectando a PostgreSQL...")
    pg_conn = psycopg2.connect(**PG_CONFIG)
    print("  ✓ Conexión exitosa")
    
    print("\nCargando catálogos PostgreSQL...")
    catalogs = build_pg_catalogs(pg_conn)
    
    print("\nCargando datos MariaDB...")
    mdb_data = load_mariaDB_dump('SINB/sinb_20260714.sql')
    
    print("\nConstruyendo lookups...")
    mdb_lookups = build_mdb_lookups(mdb_data, catalogs)
    
    print("\nIniciando migración...")
    insertados, errores = migrate_data(pg_conn, mdb_data, catalogs, mdb_lookups, 'SINB/sinb_20260714.sql')
    
    print(f"\n{'=' * 70}")
    print(f"MIGRACIÓN COMPLETADA")
    print(f"  Insertadas: {insertados}")
    print(f"  Errores: {errores}")
    print(f"{'=' * 70}")
    
    pg_conn.close()

if __name__ == '__main__':
    main()
