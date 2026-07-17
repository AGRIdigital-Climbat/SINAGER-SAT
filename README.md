# EDAN - Base de Datos

Evaluación de Daños y Análisis de Necesidades. Sistema de gestión de desastres naturales.

---

## Desplegar desde cero

```bash
sudo bash setup.sh
```

Esto instala PostgreSQL, crea la BD y verifica todo automáticamente.

---

## Restaurar BD (si ya tienes PostgreSQL instalado)

```bash
bash deploy/desplegar_bd.sh
```

---

## Verificar

```bash
bash deploy/verificar.sh
```

---

## Conexión

| Parámetro | Valor |
|-----------|-------|
| Host | `10.10.10.220` |
| Puerto | `5432` |
| Base de datos | `db_sinagersat` |
| Usuario | `sinagersat` |
| Contraseña | `12345678` |

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 10.10.10.220
```

---

## Herramientas gráficas

- **DBeaver**: Host: `10.10.10.220` | Port: `5432` | DB: `db_sinagersat` | User: `sinagersat`
- **pgAdmin4**: File > Import > `database/servers.json`

---

## Documentación

Ver `docs/CONECTAR.md` para credenciales y `docs/EDAN_BD.md` para documentación completa de la BD.

---

## Solución de problemas

```bash
# PostgreSQL no está corriendo
sudo service postgresql start

# Restaurar BD
bash deploy/desplegar_bd.sh

# Verificar
bash deploy/verificar.sh
```
