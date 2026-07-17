# DESPLIEGUE DE BASE DE DATOS EDAN

Instalacion rapida de la base de datos EDAN en **Ubuntu** o **Zorin OS**.

---

## Instalacion en 1 paso (recomendado)

```bash
cd DB_EDAN
sudo bash setup.sh
```

Esto instala PostgreSQL, crea el usuario, restaura la BD y verifica todo.

---

## Instalacion paso a paso

Si prefieres hacerlo manualmente:

### Paso 1: Copiar la carpeta

```bash
scp -r DB_EDAN/ usuario@192.168.1.100:~/DB_EDAN/
```

### Paso 2: Dar permisos

```bash
cd ~/DB_EDAN/deploy
chmod +x *.sh
```

### Paso 3: Instalar PostgreSQL

```bash
sudo bash instalar_postgresql.sh
```

### Paso 4: Desplegar la BD

```bash
bash desplegar_bd.sh
```

### Paso 5: Verificar

```bash
bash verificar.sh
```

### Paso 6: Conectar

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 127.0.0.1
```

---

## Credenciales

| Parametro  | Valor         |
|------------|---------------|
| Usuario    | `sinagersat`  |
| Password   | `12345678`    |
| Base datos | `db_sinagersat` |
| Host       | `127.0.0.1`   |
| Puerto     | `5432`        |

---

## Estructura de archivos

```
DB_EDAN/
├── setup.sh                              # INSTALACION EN 1 PASO
├── README.md
├── Formulario.pdf
├── deploy/
│   ├── setup.sh                          # (enlace al padre)
│   ├── instalar_postgresql.sh            # Solo instalar PostgreSQL
│   ├── desplegar_bd.sh                   # Restaurar BD desde backup
│   ├── verificar.sh                      # Verificar todo
│   ├── config/
│   │   ├── postgresql.conf
│   │   └── pg_hba.conf
│   └── README.md
├── database/
│   ├── edan_db_backup.sql                # Backup completo (restaurar)
│   ├── crear_edan_db.sql                 # Esquema SQL (alternativo)
│   ├── insert_provincias_municipios.sql  # Datos geograficos
│   ├── servers.json                      # Config pgAdmin4
│   ├── restore_db.sh                     # Restaurar BD
│   ├── test_conn.sh                      # Test de conexion
│   └── iniciar_edan.bat                  # Inicio desde Windows
├── config/
│   ├── postgresql.conf
│   └── pg_hba.conf
├── docs/
│   └── EDAN_BD.md
└── home/
```

---

## Herramientas graficas

### pgAdmin4
1. Abrir pgAdmin4
2. **File > Import/Export Servers > Import**
3. Seleccionar `database/servers.json`

### DBeaver
1. Nuevo.getConnection > PostgreSQL
2. Host: `127.0.0.1` | Port: `5432`
3. Database: `db_sinagersat` | User: `sinagersat`
4. Password: `12345678`

---

## Solucion de problemas

### "PostgreSQL no esta corriendo"
```bash
sudo service postgresql start
sudo service postgresql status
```

### "Password authentication failed"
```bash
sudo -u postgres psql
ALTER ROLE sinagersat WITH PASSWORD '12345678';
\q
```

### "Database does not exist"
```bash
bash desplegar_bd.sh
```

### Restaurar desde cero
```bash
bash restore_db.sh
```

### Verificar la BD
```bash
bash verificar.sh
```
