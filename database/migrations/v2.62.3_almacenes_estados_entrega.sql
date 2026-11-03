-- v2.62.3: Estados claros para entrega/PECOSA
BEGIN;

ALTER TABLE rida.entrega ADD COLUMN IF NOT EXISTS estado_nuevo VARCHAR(20);
UPDATE rida.entrega SET estado_nuevo = CASE 
    WHEN estado_despacho = 'ANULADA' THEN 'ANULADA'
    WHEN estado_despacho = 'DESPACHADA' THEN 'DESPACHADA'
    WHEN estado = 'CERRADA' THEN 'CERRADA'
    ELSE 'BORRADOR'
END WHERE estado_nuevo IS NULL;

-- Normalizar
ALTER TABLE rida.entrega DROP CONSTRAINT IF EXISTS entrega_estado_nuevo_check;
ALTER TABLE rida.entrega ADD CONSTRAINT entrega_estado_nuevo_check CHECK (estado_nuevo IN ('BORRADOR','DESPACHADA','ENTREGADA_PARCIAL','ENTREGADA_TOTAL','CERRADA','ANULADA'));

COMMIT;
