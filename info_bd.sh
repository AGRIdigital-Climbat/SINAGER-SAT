#!/bin/bash
# ================================================================
#  SINAGERSAT - Información de la Base de Datos
#  Muestra todos los datos de conexión
# ================================================================

VERDE="\033[0;32m"
CYAN="\033[0;36m"
AMARILLO="\033[1;33m"
SIN_COLOR="\033[0m"

# IP local
IP=$(hostname -I | awk '{print $1}')

echo ""
echo -e "${CYAN}================================================${SIN_COLOR}"
echo -e "${CYAN}  SINAGERSAT - BASE DE DATOS${SIN_COLOR}"
echo -e "${CYAN}================================================${SIN_COLOR}"
echo ""
echo -e "  ${VERDE}Host:${SIN_COLOR}       $IP"
echo -e "  ${VERDE}Puerto:${SIN_COLOR}     5432"
echo -e "  ${VERDE}Base de datos:${SIN_COLOR} db_sinagersat"
echo -e "  ${VERDE}Usuario:${SIN_COLOR}     sinagersat"
echo -e "  ${VERDE}Contraseña:${SIN_COLOR}  12345678"
echo ""
echo -e "${AMARILLO}------------------------------------------------${SIN_COLOR}"
echo -e "${AMARILLO}  COMANDOS DE CONEXIÓN${SIN_COLOR}"
echo -e "${AMARILLO}------------------------------------------------${SIN_COLOR}"
echo ""
echo -e "  ${VERDE}Desde esta máquina:${SIN_COLOR}"
echo "    PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 127.0.0.1"
echo ""
echo -e "  ${VERDE}Desde otra máquina:${SIN_COLOR}"
echo "    PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h $IP"
echo ""
echo -e "${AMARILLO}------------------------------------------------${SIN_COLOR}"
echo -e "${AMARILLO}  HERRAMIENTAS GRÁFICAS${SIN_COLOR}"
echo -e "${AMARILLO}------------------------------------------------${SIN_COLOR}"
echo ""
echo -e "  ${VERDE}DBeaver:${SIN_COLOR}"
echo "    Host: $IP"
echo "    Port: 5432"
echo "    Database: db_sinagersat"
echo "    User: sinagersat"
echo "    Password: 12345678"
echo ""
echo -e "  ${VERDE}pgAdmin4:${SIN_COLOR}"
echo "    File > Import/Export Servers > Import"
echo "    Seleccionar: database/servers.json"
echo ""
echo -e "${CYAN}================================================${SIN_COLOR}"
echo -e "${CYAN}  Presiona ENTER para cerrar...${SIN_COLOR}"
echo -e "${CYAN}================================================${SIN_COLOR}"
read
