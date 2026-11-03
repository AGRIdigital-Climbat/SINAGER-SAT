#!/usr/bin/env python3
"""
Actualiza pronósticos de corto plazo con usuarios correctos (mapeo por celular)
"""

import re
import psycopg2

PG_CONFIG = {
    'host': '127.0.0.1',
    'port': 5432,
    'database': 'db_sinagersat',
    'user': 'sinagersat',
    'password': '12345678'
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
        rows = []
        current_row = ''
        paren_depth = 0
        in_string = False
        
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
                if current_row.strip():
                    rows.append(current_row.strip())
                current_row = ''
            else:
                current_row += char
            
            i += 1
        
        if current_row.strip():
            rows.append(current_row.strip())
        
        for row in rows:
            fields = parse_row_fields(row)
            if fields:
                all_rows.append(fields)
    
    return all_rows

def main():
    print("=" * 70)
    print("ACTUALIZACIÓN PRONÓSTICOS DE CORTO PLAZO")
    print("=" * 70)
    
    # Conectar PostgreSQL
    pg_conn = psycopg2.connect(**PG_CONFIG)
    
    # Leer dump MariaDB
    with open('SINB/sinb_20260714.sql', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parsear t_usuario
    print("\nParseando t_usuario...")
    usuarios_mdb = parse_values(content, 't_usuario')
    print(f"  → {len(usuarios_mdb)} usuarios")
    
    # Crear mapeo celular → usuario PG
    print("\nObteniendo mapeo de usuarios PostgreSQL...")
    with pg_conn.cursor() as cur:
        cur.execute("SELECT celular, id_usuario FROM usuarios.usuario WHERE celular IS NOT NULL AND celular != ''")
        usuario_celular = {str(row[0]): row[1] for row in cur.fetchall()}
    print(f"  → {len(usuario_celular)} usuarios con celular")
    
    # Mapear usuarios MDB → PG
    usuario_mdb_pg = {}
    for row in usuarios_mdb:
        mdb_id = int(row[0])
        celular = row[6] if len(row) > 6 else None
        if celular:
            pg_id = usuario_celular.get(str(celular))
            if pg_id:
                usuario_mdb_pg[mdb_id] = pg_id
    
    print(f"  → {len(usuario_mdb_pg)} usuarios mapeados")
    
    # Parsear t_usuario_pronostico_temporal
    print("\nParseando t_usuario_pronostico_temporal...")
    usu_prono = parse_values(content, 't_usuario_pronostico_temporal')
    print(f"  → {len(usu_prono)} registros")
    
    # Obtener pronósticos cortos existentes
    print("\nObteniendo pronósticos cortos existentes...")
    with pg_conn.cursor() as cur:
        cur.execute("SELECT id, codigo FROM sinb.pronostico_corto ORDER BY codigo")
        pronos_pg = cur.fetchall()
    print(f"  → {len(pronos_pg)} pronósticos")
    
    # Actualizar
    print("\nActualizando pronósticos...")
    actualizados = 0
    
    with pg_conn.cursor() as cur:
        for row in usu_prono:
            pron_id = int(row[2])  # pronostico_id
            usuario_mdb_id = int(row[1])  # usuario_id
            
            # Mapear usuario
            usuario_pg_id = usuario_mdb_pg.get(usuario_mdb_id)
            
            if not usuario_pg_id:
                print(f"  → Pronóstico {pron_id}: usuario MDB {usuario_mdb_id} NO mapeado")
                continue
            
            # Actualizar pronostico_corto
            codigo = f"PT-{pron_id}"
            cur.execute("""
                UPDATE sinb.pronostico_corto 
                SET id_usuario_subio = %s
                WHERE codigo = %s
            """, (usuario_pg_id, codigo))
            
            if cur.rowcount > 0:
                actualizados += 1
                print(f"  → {codigo}: usuario {usuario_mdb_id} → {usuario_pg_id}")
            
            # Insertar observador
            cur.execute("""
                INSERT INTO sinb.pronostico_corto_observador 
                (id_pronostico_corto, id_usuario, confianza)
                SELECT id, %s, 'MEDIA'
                FROM sinb.pronostico_corto 
                WHERE codigo = %s
                ON CONFLICT (id_pronostico_corto, id_usuario) DO NOTHING
            """, (usuario_pg_id, codigo))
    
    pg_conn.commit()
    
    print(f"\n{'=' * 70}")
    print(f"ACTUALIZACIÓN COMPLETADA")
    print(f"  Actualizados: {actualizados}")
    print(f"{'=' * 70}")
    
    pg_conn.close()

if __name__ == '__main__':
    main()
