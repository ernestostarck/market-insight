-- updated_at triggers for mutable business tables.

DROP TRIGGER IF EXISTS trg_document_metadata_updated_at ON documents.document_metadata;
CREATE TRIGGER trg_document_metadata_updated_at
BEFORE UPDATE ON documents.document_metadata
FOR EACH ROW
EXECUTE FUNCTION core.set_updated_at();

DROP TRIGGER IF EXISTS trg_tenders_updated_at ON procurement.tenders;
CREATE TRIGGER trg_tenders_updated_at
BEFORE UPDATE ON procurement.tenders
FOR EACH ROW
EXECUTE FUNCTION core.set_updated_at();

DROP TRIGGER IF EXISTS trg_licitaciones_updated_at ON procurement.licitaciones;
CREATE TRIGGER trg_licitaciones_updated_at
BEFORE UPDATE ON procurement.licitaciones
FOR EACH ROW
EXECUTE FUNCTION core.set_updated_at();

DROP TRIGGER IF EXISTS trg_ordenes_compra_updated_at ON procurement.ordenes_compra;
CREATE TRIGGER trg_ordenes_compra_updated_at
BEFORE UPDATE ON procurement.ordenes_compra
FOR EACH ROW
EXECUTE FUNCTION core.set_updated_at();

DROP TRIGGER IF EXISTS trg_proveedores_updated_at ON procurement.proveedores;
CREATE TRIGGER trg_proveedores_updated_at
BEFORE UPDATE ON procurement.proveedores
FOR EACH ROW
EXECUTE FUNCTION core.set_updated_at();

DROP TRIGGER IF EXISTS trg_contratos_updated_at ON procurement.contratos;
CREATE TRIGGER trg_contratos_updated_at
BEFORE UPDATE ON procurement.contratos
FOR EACH ROW
EXECUTE FUNCTION core.set_updated_at();

DROP TRIGGER IF EXISTS trg_convenios_marco_updated_at ON procurement.convenios_marco;
CREATE TRIGGER trg_convenios_marco_updated_at
BEFORE UPDATE ON procurement.convenios_marco
FOR EACH ROW
EXECUTE FUNCTION core.set_updated_at();

DROP TRIGGER IF EXISTS trg_adjudicaciones_updated_at ON procurement.adjudicaciones;
CREATE TRIGGER trg_adjudicaciones_updated_at
BEFORE UPDATE ON procurement.adjudicaciones
FOR EACH ROW
EXECUTE FUNCTION core.set_updated_at();

