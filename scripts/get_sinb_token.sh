#!/bin/bash
# Obtener token SINB y guardar en archivo temporal
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v2/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"usuario":"admin","contrasena":"vid3ci"}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('data', {}).get('access_token', ''))" 2>/dev/null)

if [ -n "$TOKEN" ]; then
    echo "$TOKEN" > /tmp/sinb_token
    echo "Token actualizado: $(date)"
else
    echo "Error al obtener token"
    exit 1
fi
