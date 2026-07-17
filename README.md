# EDAN - Base de Datos

Evaluacion de Danos y Analisis de Necesidades. Sistema de gestion de desastres naturales.

---

## Instalacion rapida

```bash
sudo bash setup.sh
```

Eso es todo. Instala PostgreSQL, crea la BD y verifica todo automaticamente.

---

## Instalacion manual (paso a paso)

Si prefieres hacerlo manualmente, ver `deploy/README.md`.

---

## Conexion

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 127.0.0.1
```

## Herramientas graficas

- **pgAdmin4**: File > Import > `database/servers.json`
- **DBeaver**: Host: 127.0.0.1 | DB: db_sinagersat | User: sinagersat | Pass: 12345678

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

## Estructura

```
DB_EDAN/
├── setup.sh                              # INSTALACION EN 1 PASO
├── README.md                             # Este archivo
├── Formulario.pdf                        # Formulario EDAN original
├── deploy/
│   ├── instalar_postgresql.sh            # Solo instalar PostgreSQL
│   ├── desplegar_bd.sh                   # Desplegar BD desde backup
│   ├── verificar.sh                      # Verificar la BD
│   ├── config/                           # Configs PostgreSQL
│   └── README.md                         # Guia detallada de despliegue
├── database/
│   ├── edan_db_backup.sql                # Backup completo
│   ├── crear_edan_db.sql                 # Esquema SQL (alternativo)
│   ├── insert_provincias_municipios.sql  # Geografia INE Bolivia
│   ├── restore_db.sh                     # Restaurar BD
│   ├── test_conn.sh                      # Test de conexion
│   ├── servers.json                      # Config pgAdmin4
│   └── iniciar_edan.bat                  # Inicio desde Windows
├── config/
│   ├── postgresql.conf
│   └── pg_hba.conf
├── docs/
│   └── EDAN_BD.md                        # Documentacion completa
└── home/
```

---

## Comandos utiles

```bash
# Verificar la BD
bash deploy/verificar.sh

# Restaurar desde backup
bash database/restore_db.sh

# Test de conexion
bash database/test_conn.sh

# Crear backup (desde PostgreSQL)
sudo -u postgres pg_dump -d db_sinagersat > database/edan_db_backup.sql
```

---

## Backup y migracion

### Crear backup
```bash
sudo -u postgres pg_dump -d db_sinagersat > database/edan_db_backup.sql
```

### Migrar a otra maquina
1. Copiar toda la carpeta `DB_EDAN/`
2. En la maquina destino: `sudo bash setup.sh`

---

## Documentacion

Ver `docs/EDAN_BD.md` para documentacion completa de la estructura de la BD.

---

## Windows (WSL)

Si usas Windows con WSL, ejecuta `database/iniciar_edan.bat` para configurar el reenvio de puertos y pgAdmin4.

---

## Solucion de problemas

```bash
# PostgreSQL no esta corriendo
sudo service postgresql start

# Restaurar BD
bash database/restore_db.sh

# Verificar
bash deploy/verificar.sh
```
