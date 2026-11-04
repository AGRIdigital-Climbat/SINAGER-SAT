from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional
from ...response import SuccessResponse
from ..core.llm import get_modo_global, set_modo_global, usar_modelo_externo
from ..core.secrets import encrypt_secret, enmascarar_clave, es_cifrado
from ..db.queries import (
    listar_proveedores_llm,
    obtener_proveedor_llm,
    obtener_proveedores_internos,
    crear_proveedor_llm,
    actualizar_proveedor_llm,
    actualizar_estado_modelo_proveedor,
    eliminar_proveedor_llm,
    resumen_uso_llm,
    resumen_uso_embeddings,
)
from ..security import _validar_token_api

router = APIRouter(prefix="/llm", tags=["MotorIA > LLM"])

MODOS = ("local", "external")


# --- Modelos de lenguaje: modo global ---


class ModoRequest(BaseModel):
    modo: str = Field(
        ...,
        description="Modo global del LLM: 'local' (Qwen2.5-3B) o 'external' (OpenAI-compatible).",
    )
    persistir: bool = Field(
        True,
        description=(
            "Si es true (default), guarda el modo en .env (LLM_MODE) y el cambio "
            "sobrevive al reinicio del servidor. Con false solo vale para la sesion actual."
        ),
    )


@router.get("/modo", dependencies=[Depends(_validar_token_api)])
def modo_actual():
    """Modo global del LLM actual y como se resolveria una peticion sin `llm_externo`.

    Requiere `X-API-Key` (único endpoint de lectura bajo token).
    """
    return {
        "modo": get_modo_global(),
        "modos_disponibles": list(MODOS),
        "llm_externo_usado": usar_modelo_externo(),
    }


@router.post("/modo", dependencies=[Depends(_validar_token_api)])
def cambiar_modo(req: ModoRequest):
    """Cambia el modo global del LLM: `local` o `external`.

    Si `persistir: true` escribe LLM_MODE en `.env` para que el cambio siga
    vigente tras reiniciar el servidor. Las peticiones de `/chat` con
    `llm_externo: null` usaran este modo global hasta que se vuelva a cambiar.
    """
    modo = req.modo.strip().lower()
    if modo not in MODOS:
        raise HTTPException(
            status_code=400,
            detail=f"modo debe ser uno de {list(MODOS)}",
        )
    nuevo = set_modo_global(modo, persistir=req.persistir)
    return {
        "mensaje": f"Modo LLM global cambiado a '{nuevo}'",
        "modo": nuevo,
        "persistido": req.persistir,
        "llm_externo_usado": usar_modelo_externo(),
    }


# --- CRUD Proveedores de LLM externos ---


class ProveedorCreate(BaseModel):
    nombre: str = Field(..., description="Nombre del proveedor (unico). Ej: 'Groq', 'DeepSeek'.")
    base_url: str = Field(..., description="Base URL compatible OpenAI. Ej: 'https://api.groq.com/openai/v1'")
    apikey: Optional[str] = Field(None, description="Clave del proveedor (se almacena cifrada en la BD).")
    modelo_base: str = Field(..., description="Modelo por defecto. Ej: 'openai/gpt-oss-20b'.")
    estado_manual: bool = Field(True, description="true = proveedor habilitado, false = deshabilitado.")


class ProveedorUpdate(BaseModel):
    nombre: Optional[str] = Field(None, description="Nuevo nombre.")
    base_url: Optional[str] = Field(None, description="Nueva base URL.")
    apikey: Optional[str] = Field(None, description="Nueva clave (se cifrara).")
    modelo_base: Optional[str] = Field(None, description="Nuevo modelo base.")
    estado_manual: Optional[bool] = Field(None, description="Nuevo estado manual (true/false).")


@router.get("/proveedores")
def listar_proveedores(
    limit: int = Query(100, ge=1, le=500, description="Cantidad a devolver (los más recientes primero)"),
    skip: int = Query(0, ge=0, description="Saltar registros (paginación, sólo con limit)"),
    todos: bool = Query(False, description="Devolver todos los proveedores sin paginar"),
    q: Optional[str] = Query(None, description="Filtrar por nombre, base_url o modelo."),
    estado_manual: Optional[bool] = Query(None, description="Filtrar por interruptor manual del proveedor."),
    estado_modelo: Optional[bool] = Query(None, description="Filtrar por último estado verificado del modelo."),
):
    """Lista proveedores de LLM registrados con cantidad, paginación y filtros.

    La apikey nunca se muestra en texto plano; se devuelve el flag
    `apikey_configurada` y la máscara `apikey_mascarada`.
    """
    proveedores, total = listar_proveedores_llm(
        q=q,
        estado_manual=estado_manual,
        estado_modelo=estado_modelo,
        limit=limit,
        skip=skip,
        todos=todos,
    )
    resultado = []
    for p in proveedores:
        item = dict(p)
        item["apikey_mascarada"] = "••••" if not item.get("apikey_configurada") else "(configurada)"
        resultado.append(item)
    return SuccessResponse(message="Proveedores listados", data=resultado, total=total)


@router.get("/proveedores/{proveedor_id}")
def detalle_proveedor(proveedor_id: int):
    """Detalle de un proveedor (apikey enmascarada)."""
    proveedor = obtener_proveedor_llm(proveedor_id)
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    item = dict(proveedor)
    item["apikey_mascarada"] = "••••" if not item.get("apikey_configurada") else "(configurada)"
    return item


@router.post("/proveedores", dependencies=[Depends(_validar_token_api)])
def crear_proveedor(req: ProveedorCreate):
    """Crea un nuevo proveedor de LLM externo.

    La apikey se cifra AES-256-GCM antes de almacenarse y nunca se guarda en
    texto plano.
    """
    if not req.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacio")
    if not req.base_url.strip():
        raise HTTPException(status_code=400, detail="La base_url no puede estar vacia")
    if not req.modelo_base.strip():
        raise HTTPException(status_code=400, detail="El modelo_base no puede estar vacio")
    apikey_cifrado = encrypt_secret(req.apikey) if req.apikey else None
    proveedor_id = crear_proveedor_llm(
        nombre=req.nombre.strip(),
        base_url=req.base_url.strip(),
        apikey_cifrado=apikey_cifrado,
        modelo_base=req.modelo_base.strip(),
        estado_manual=req.estado_manual,
    )
    return {"mensaje": "Proveedor creado correctamente", "proveedor_id": proveedor_id}


@router.put("/proveedores/{proveedor_id}", dependencies=[Depends(_validar_token_api)])
def editar_proveedor(proveedor_id: int, req: ProveedorUpdate):
    """Edita un proveedor existente. Solo se actualizan los campos enviados (no nulos).

    Si se envía una nueva apikey, se cifra antes de almacenar.
    """
    proveedor = obtener_proveedor_llm(proveedor_id)
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    nombre = req.nombre.strip() if req.nombre is not None else proveedor["nombre"]
    base_url = req.base_url.strip() if req.base_url is not None else proveedor["base_url"]
    modelo_base = req.modelo_base.strip() if req.modelo_base is not None else proveedor["modelo_base"]
    estado_manual = req.estado_manual if req.estado_manual is not None else proveedor["estado_manual"]
    if req.apikey is not None:
        apikey_cifrado = encrypt_secret(req.apikey)
    else:
        # conservar el valor existente (obtener_proveedor_llm no trae apikey;
        # necesitamos obtenerla internamente)
        internos = [r for r in obtener_proveedores_internos() if r["id"] == proveedor_id]
        apikey_cifrado = internos[0]["apikey"] if internos else None
    actualizar_proveedor_llm(proveedor_id, nombre, base_url, apikey_cifrado, modelo_base, estado_manual)
    return {"mensaje": "Proveedor actualizado correctamente"}


@router.delete("/proveedores/{proveedor_id}", dependencies=[Depends(_validar_token_api)])
def borrar_proveedor(proveedor_id: int):
    """Elimina un proveedor de la BD."""
    proveedor = obtener_proveedor_llm(proveedor_id)
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    eliminar_proveedor_llm(proveedor_id)
    return {"mensaje": "Proveedor eliminado correctamente"}


@router.post("/proveedores/{proveedor_id}/probar", dependencies=[Depends(_validar_token_api)])
def probar_proveedor(proveedor_id: int):
    """Prueba un proveedor realizando una llamada al modelo y actualiza su `estado_modelo`.

    Usa la apikey cifrada de la BD (descifrándola internamente).
    Responde con `true` o `false` en `estado_modelo`.
    """
    internos = [r for r in obtener_proveedores_internos() if r["id"] == proveedor_id]
    if not internos:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    prov = internos[0]
    try:
        from ..core.secrets import decrypt_secret
        from openai import OpenAI
        apikey = decrypt_secret(prov["apikey"])
        client = OpenAI(api_key=apikey, base_url=prov["base_url"])
        client.chat.completions.create(
            model=prov["modelo_base"],
            messages=[{"role": "user", "content": "Responde unicamente con la palabra OK"}],
            max_tokens=64,
        )
        estado = True
    except Exception:
        estado = False
    actualizar_estado_modelo_proveedor(proveedor_id, estado)
    return {
        "proveedor_id": proveedor_id,
        "nombre": prov["nombre"],
        "estado_modelo": estado,
        "modelo_base": prov["modelo_base"],
    }


@router.get("/uso/resumen", dependencies=[Depends(_validar_token_api)])
def resumen_uso(
    desde: Optional[str] = Query(None, description="Fecha inicial filtro (YYYY-MM-DD, inclusiva)."),
    hasta: Optional[str] = Query(None, description="Fecha final filtro (YYYY-MM-DD, inclusiva)."),
):
    """Resumen de consumo de LLM y embeddings.

    Devuelve tres bloques:
      - `llm`: uso historico de `/chat` (llamadas, tokens y proveedores).
      - `embeddings`: uso de embeddings externos (Google por defecto): llamadas,
        textos, tokens totales y por tipo `query` o `index`.
      - `uso_total`: sumatoria simple LLM + embeddings para controlar quota.

    Los tokens de embeddings se toman de `usage` del proveedor cuando los
    devuelve; si no los devuelve, se estiman por carateres y quedan marcados
    en `llamadas_con_tokens_estimados`.
    """
    llm = resumen_uso_llm(desde=desde, hasta=hasta)
    embeddings = resumen_uso_embeddings(desde=desde, hasta=hasta)

    uso_total = {
        "llamadas": int(llm["resumen_total"]["llamadas"]) + int(embeddings["resumen_total"]["llamadas"]),
        "llamadas_exitosas": int(llm["resumen_total"]["llamadas_exitosas"]) + int(embeddings["resumen_total"]["llamadas_exitosas"]),
        "llamadas_sin_exito": int(llm["resumen_total"]["llamadas_sin_exito"]) + int(embeddings["resumen_total"]["llamadas_sin_exito"]),
        "tokens_total": int(llm["resumen_total"]["tokens_total"]) + int(embeddings["resumen_total"]["tokens_total"]),
    }

    return {
        **llm,
        "uso_total": uso_total,
        "embeddings": embeddings,
    }
