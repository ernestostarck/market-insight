"""Curated Validation Dataset of 20 Real/Realistic Mercado Público Tenders (ChileCompra).

Used for Phase 6.28 End-to-End Validation of the NLP and Knowledge Layer.
Covers diverse public procurement domains, Chilean public institutions, standard
product specifications, Chilean formats (RUT, CLP, delivery dates), and edge cases.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class RealTenderItem:
    correlativo: int
    codigo_producto: str
    nombre: str
    descripcion: str
    cantidad: float
    unidad_medida: str
    precio_referencial: float


@dataclass(frozen=True)
class RealTender:
    id: int
    codigo_externo: str
    nombre: str
    descripcion: str
    organismo_nombre: str
    rut_comprador: str
    monto_estimado: float
    fecha_cierre: datetime.datetime
    items: list[RealTenderItem]
    expected_category: str
    expected_relevant: bool
    expected_concepts: list[str] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        items_str = " ".join(f"{item.nombre}: {item.descripcion}" for item in self.items)
        return f"{self.nombre}. {self.descripcion}. {items_str}".strip()


def get_validation_tenders() -> list[RealTender]:
    """Return a curated set of 20 representative Mercado Público tenders."""
    # Reference future date for open tenders (20-60 days ahead)
    now = datetime.datetime(2026, 10, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
    future_20 = now + datetime.timedelta(days=20)
    future_45 = now + datetime.timedelta(days=45)
    past_10 = now - datetime.timedelta(days=10)

    return [
        # ==========================================
        # 1-6: Health / Geriatrics / Ayudas Técnicas
        # ==========================================
        RealTender(
            id=101,
            codigo_externo="2401-15-LR26",
            nombre="Adquisición de silla de ruedas y ayudas técnicas para adulto mayor",
            descripcion=(
                "El Servicio de Salud Metropolitano Central requiere adquirir sillas de ruedas "
                "clínicas plegables en estructura de aluminio con soporte de 120 kg para "
                "pacientes de geriatría con movilidad reducida del Hospital San Borja Arriarán."
            ),
            organismo_nombre="Servicio de Salud Metropolitano Central",
            rut_comprador="61.602.100-2",
            monto_estimado=24500000.0,
            fecha_cierre=future_20,
            items=[
                RealTenderItem(
                    correlativo=1,
                    codigo_producto="42192210",
                    nombre="Silla de ruedas neurológica estándar",
                    descripcion="Silla de ruedas de aluminio plegable con ruedas antipinchazo y capacidad de 120 kg.",
                    cantidad=35.0,
                    unidad_medida="UNIDAD",
                    precio_referencial=350000.0,
                ),
                RealTenderItem(
                    correlativo=2,
                    codigo_producto="42192211",
                    nombre="Andador ortopédico para adulto mayor",
                    descripcion="Andador de cuatro ruedas con asiento acolchado, frenos y canasta portaobjetos.",
                    cantidad=50.0,
                    unidad_medida="UNIDAD",
                    precio_referencial=110000.0,
                ),
            ],
            expected_category="health",
            expected_relevant=True,
            expected_concepts=["silla_de_ruedas", "andador", "adulto_mayor", "geriatria", "movilidad_reducida"],
        ),
        RealTender(
            id=102,
            codigo_externo="1057421-22-LE26",
            nombre="Suministro de prótesis y órtesis para servicio de rehabilitación física",
            descripcion=(
                "Hospital Clínico San Juan de Dios licita el suministro continuo de órtesis "
                "y prótesis biomecánicas para tratamientos de kinesiología y terapia ocupacional "
                "en personas en situación de discapacidad y adultos mayores."
            ),
            organismo_nombre="Hospital San Juan de Dios",
            rut_comprador="61.601.200-3",
            monto_estimado=48000000.0,
            fecha_cierre=future_45,
            items=[
                RealTenderItem(
                    correlativo=1,
                    codigo_producto="42241501",
                    nombre="Órtesis tobillo-pie articulada",
                    descripcion="Órtesis termoplástica de polipropileno con articulación libre y acolchado interior.",
                    cantidad=40.0,
                    unidad_medida="UNIDAD",
                    precio_referencial=450000.0,
                ),
                RealTenderItem(
                    correlativo=2,
                    codigo_producto="42241502",
                    nombre="Bastón ortopédico canadiense regulable",
                    descripcion="Bastón de apoyo ergonómico en aluminio anodizado con regatón antideslizante.",
                    cantidad=80.0,
                    unidad_medida="UNIDAD",
                    precio_referencial=28000.0,
                ),
            ],
            expected_category="health",
            expected_relevant=True,
            expected_concepts=["protesis", "ortesis", "baston", "rehabilitacion", "discapacidad"],
        ),
        RealTender(
            id=103,
            codigo_externo="608-4-LP26",
            nombre="Compra de audífonos digitales y dispositivos de asistencia auditiva",
            descripcion=(
                "Cenabast requiere compra centralizada de audífonos digitales retroauriculares "
                "para beneficiarios con discapacidad auditiva e hipoacusia neurosensorial severa "
                "en la red asistencial pública nacional."
            ),
            organismo_nombre="Central de Abastecimiento del Sistema Nacional de Servicios de Salud (CENABAST)",
            rut_comprador="61.608.000-0",
            monto_estimado=180000000.0,
            fecha_cierre=future_20,
            items=[
                RealTenderItem(
                    correlativo=1,
                    codigo_producto="42211503",
                    nombre="Audífono retroauricular BTE multicanal",
                    descripcion="Audífono programable digital con cancelación de ruido adaptativa y conectividad bluetooth.",
                    cantidad=300.0,
                    unidad_medida="UNIDAD",
                    precio_referencial=480000.0,
                )
            ],
            expected_category="health",
            expected_relevant=True,
            expected_concepts=["audifono", "discapacidad_auditiva", "ayuda_tecnica"],
        ),
        RealTender(
            id=104,
            codigo_externo="1204-8-LR26",
            nombre="Adquisición de grúa de traslado y equipamiento para pacientes postrados",
            descripcion=(
                "Instituto Nacional de Geriatría requiere adquisición de grúas eléctricas de traslado "
                "para pacientes con dependencia severa y movilidad reducida para prevención de caídas "
                "y facilitación de la labor del personal de enfermería geriátrica."
            ),
            organismo_nombre="Instituto Nacional de Geriatría Presidente Eduardo Frei Montalva",
            rut_comprador="61.602.400-1",
            monto_estimado=35000000.0,
            fecha_cierre=future_45,
            items=[
                RealTenderItem(
                    correlativo=1,
                    codigo_producto="42192212",
                    nombre="Grúa eléctrica de bipedestación y traslado",
                    descripcion="Grúa para pacientes con motor eléctrico recargable, arnés anatómico y soporte de 180 kg.",
                    cantidad=12.0,
                    unidad_medida="UNIDAD",
                    precio_referencial=1850000.0,
                )
            ],
            expected_category="health",
            expected_relevant=True,
            expected_concepts=["grua_de_traslado", "geriatria", "movilidad_reducida", "prevencion_caidas"],
        ),
        RealTender(
            id=105,
            codigo_externo="750-18-LP26",
            nombre="Suministro de insumos de geriatría e higiene para centros de día",
            descripcion=(
                "El Servicio Nacional del Adulto Mayor (SENAMA) licita provisión anual de insumos "
                "de cuidado geriátrico, pañales para adultos mayores y apósitos para centros diurnos "
                "y establecimientos de larga estadía (ELEAM)."
            ),
            organismo_nombre="Servicio Nacional del Adulto Mayor",
            rut_comprador="60.101.001-8",
            monto_estimado=85000000.0,
            fecha_cierre=future_20,
            items=[
                RealTenderItem(
                    correlativo=1,
                    codigo_producto="42131608",
                    nombre="Pañales anatómicos para adulto talla L",
                    descripcion="Pañal descartable con gel superabsorbente e indicador de humedad para adultos mayores.",
                    cantidad=25000.0,
                    unidad_medida="UNIDAD",
                    precio_referencial=680.0,
                )
            ],
            expected_category="health",
            expected_relevant=True,
            expected_concepts=["adulto_mayor", "centro_dia", "establecimiento_larga_estadia", "geriatria"],
        ),
        RealTender(
            id=106,
            codigo_externo="845-9-LR26",
            nombre="Camas clínicas hospitalarias eléctricas de 3 posiciones",
            descripcion=(
                "Hospital Sótero del Río requiere adquirir 25 camas clínicas de tres posiciones "
                "eléctricas con barandas laterales plegables y ruedas con freno centralizado "
                "para pabellón de medicina y rehabilitación."
            ),
            organismo_nombre="Complejo Asistencial Dr. Sótero del Río",
            rut_comprador="61.602.200-9",
            monto_estimado=42000000.0,
            fecha_cierre=past_10,  # Closed tender test case
            items=[
                RealTenderItem(
                    correlativo=1,
                    codigo_producto="42191801",
                    nombre="Cama clínica eléctrica multifuncional",
                    descripcion="Cama hospitalaria eléctrica con control remoto, capacidad 220 kg y barandas ABS.",
                    cantidad=25.0,
                    unidad_medida="UNIDAD",
                    precio_referencial=1500000.0,
                )
            ],
            expected_category="health",
            expected_relevant=False,  # Past closing date -> not commercially relevant
            expected_concepts=["rehabilitacion"],
        ),

        # ========================================================
        # 7-11: Construction / Accessibility / Universal Design
        # ========================================================
        RealTender(
            id=107,
            codigo_externo="4521-12-LR26",
            nombre="Obras de accesibilidad universal y construcción de rampa de acceso",
            descripcion=(
                "La Ilustre Municipalidad de Santiago llama a propuesta pública para ejecución "
                "de obras civiles de accesibilidad universal, construcción de rampas de acceso "
                "de hormigón armado, ensanche de puertas y eliminación de barreras arquitectónicas."
            ),
            organismo_nombre="Municipalidad de Santiago",
            rut_comprador="69.254.000-K",
            monto_estimado=65000000.0,
            fecha_cierre=future_45,
            items=[
                RealTenderItem(
                    correlativo=1,
                    codigo_producto="72121100",
                    nombre="Construcción de rampa de acceso universal",
                    descripcion="Rampa de hormigón armado H25 con pendiente máxima 8% y pasamanos doble de acero inoxidable.",
                    cantidad=1.0,
                    unidad_medida="GLOBAL",
                    precio_referencial=38000000.0,
                ),
                RealTenderItem(
                    correlativo=2,
                    codigo_producto="72121101",
                    nombre="Ampliación de vanos de puertas",
                    descripcion="Adecuación y ensanche de accesos peatonales a ancho libre mínimo de 90 cm.",
                    cantidad=12.0,
                    unidad_medida="UNIDAD",
                    precio_referencial=950000.0,
                ),
            ],
            expected_category="construction",
            expected_relevant=True,
            expected_concepts=[
                "accesibilidad_universal", "rampa_de_acceso", "ampliacion_vanos_puertas",
                "eliminacion_barreras_arquitectonicas"
            ],
        ),
        RealTender(
            id=108,
            codigo_externo="5012-3-LP26",
            nombre="Habilitación de baño accesible y barras de apoyo para edificio municipal",
            descripcion=(
                "Contratación de obras civiles para remodelación y habilitación de baño accesible "
                "universal con instalación de barras de apoyo de acero inoxidable y piso antideslizante "
                "según normativa OGUC para personas con movilidad reducida."
            ),
            organismo_nombre="Municipalidad de Providencia",
            rut_comprador="69.070.300-9",
            monto_estimado=28000000.0,
            fecha_cierre=future_20,
            items=[
                RealTenderItem(
                    correlativo=1,
                    codigo_producto="72121103",
                    nombre="Remodelación baño accesible universal",
                    descripcion="Inodoro elevado, lavamanos suspendido y grifería monomando con palanca gerontológica.",
                    cantidad=2.0,
                    unidad_medida="UNIDAD",
                    precio_referencial=8500000.0,
                ),
                RealTenderItem(
                    correlativo=2,
                    codigo_producto="30181503",
                    nombre="Barra de apoyo recta y abatible de seguridad",
                    descripcion="Barra de apoyo en acero inoxidable satinado de 32 mm de diámetro con fijaciones reforzadas.",
                    cantidad=8.0,
                    unidad_medida="UNIDAD",
                    precio_referencial=185000.0,
                ),
            ],
            expected_category="construction",
            expected_relevant=True,
            expected_concepts=["bano_accesible", "barra_de_apoyo", "piso_antideslizante", "movilidad_reducida"],
        ),
        RealTender(
            id=109,
            codigo_externo="3100-24-LP26",
            nombre="Suministro e instalación de ascensor accesible y plataforma elevadora",
            descripcion=(
                "Serviu Metropolitano convoca a licitación para la adquisición, montaje e "
                "instalación de ascensor accesible electromecánico y plataforma vertical elevadora "
                "en conjunto habitacional comunitario de Providencia."
            ),
            organismo_nombre="Serviu Metropolitano",
            rut_comprador="61.802.000-3",
            monto_estimado=115000000.0,
            fecha_cierre=future_45,
            items=[
                RealTenderItem(
                    correlativo=1,
                    codigo_producto="24101601",
                    nombre="Ascensor electromecánico accesible para 8 personas",
                    descripcion="Cabina adaptada con botonera en braille, sintetizador de voz y puertas telescópicas de 90 cm.",
                    cantidad=1.0,
                    unidad_medida="UNIDAD",
                    precio_referencial=82000000.0,
                ),
                RealTenderItem(
                    correlativo=2,
                    codigo_producto="24101602",
                    nombre="Plataforma elevadora vertical para silla de ruedas",
                    descripcion="Plataforma hidráulica de elevación vertical para superar desnivel de 1.8 metros con capacidad de 300 kg.",
                    cantidad=1.0,
                    unidad_medida="UNIDAD",
                    precio_referencial=28000000.0,
                ),
            ],
            expected_category="construction",
            expected_relevant=True,
            expected_concepts=["ascensor_accesible", "silla_de_ruedas", "senaletica_braille"],
        ),
        RealTender(
            id=110,
            codigo_externo="4819-7-LE26",
            nombre="Instalación de piso antideslizante y señalética en braille para CESFAM",
            descripcion=(
                "Dirección de Salud de Maipú licita suministro y colocación de piso vinílico "
                "antideslizante de alto tráfico para prevención de caídas y señalética en braille "
                "de orientación podotáctil en centro de salud familiar."
            ),
            organismo_nombre="Corporación Municipal de Maipú",
            rut_comprador="70.945.500-2",
            monto_estimado=21000000.0,
            fecha_cierre=future_20,
            items=[
                RealTenderItem(
                    correlativo=1,
                    codigo_producto="30161701",
                    nombre="Piso vinílico antideslizante en rollo",
                    descripcion="Pavimento vinílico continuo con clasificación R10 antideslizante y resistencia bacteriana.",
                    cantidad=650.0,
                    unidad_medida="METRO_CUADRADO",
                    precio_referencial=24000.0,
                )
            ],
            expected_category="construction",
            expected_relevant=True,
            expected_concepts=["piso_antideslizante", "prevencion_caidas", "senaletica_braille"],
        ),
        RealTender(
            id=111,
            codigo_externo="2150-11-LR26",
            nombre="Construcción de veredas peatonales y rebajes de acera accesibles",
            descripcion=(
                "Municipalidad de Valparaíso requiere obras de pavimentación de veredas con "
                "rebajes de cordón accesible para sillas de ruedas y huellas podotáctiles para "
                "personas con discapacidad visual en el casco histórico."
            ),
            organismo_nombre="Municipalidad de Valparaíso",
            rut_comprador="69.060.100-1",
            monto_estimado=95000000.0,
            fecha_cierre=future_45,
            items=[
                RealTenderItem(
                    correlativo=1,
                    codigo_producto="72141103",
                    nombre="Pavimentación de aceras de hormigón",
                    descripcion="Hormigonado de veredas con pendiente transversal 2% y textura antideslizante.",
                    cantidad=1800.0,
                    unidad_medida="METRO_CUADRADO",
                    precio_referencial=38000.0,
                )
            ],
            expected_category="construction",
            expected_relevant=True,
            expected_concepts=["silla_de_ruedas", "discapacidad_visual", "piso_antideslizante"],
        ),

        # ========================================================
        # 12-15: Technology / IT (Relevant / Other Domains)
        # ========================================================
        RealTender(
            id=112,
            codigo_externo="8901-2-LP26",
            nombre="Adquisición de servidores de procesamiento y almacenamiento cloud",
            descripcion=(
                "Subsecretaría de Telecomunicaciones licita adquisición de servidores rackeables "
                "de alta densidad con procesadores Xeon, memoria RAM DDR5 y cabina de discos SSD NVMe "
                "para consolidación del datacenter institucional."
            ),
            organismo_nombre="Subsecretaría de Telecomunicaciones",
            rut_comprador="60.702.000-7",
            monto_estimado=140000000.0,
            fecha_cierre=future_45,
            items=[
                RealTenderItem(
                    correlativo=1,
                    codigo_producto="43211501",
                    nombre="Servidor rack 2U Enterprise",
                    descripcion="Servidor con 2x CPU Intel Xeon Gold 6430, 256GB RAM y controladora RAID redundante.",
                    cantidad=6.0,
                    unidad_medida="UNIDAD",
                    precio_referencial=18000000.0,
                )
            ],
            expected_category="technology",
            expected_relevant=False,
            expected_concepts=[],
        ),
        RealTender(
            id=113,
            codigo_externo="6201-14-LE26",
            nombre="Renovación de computadores portátiles para establecimientos educacionales",
            descripcion=(
                "Junta Nacional de Auxilio Escolar y Becas (JUNAEB) licita la compra masiva de "
                "notebooks educativos para estudiantes de séptimo básico con procesador Core i5 "
                "y conectividad inalámbrica Wi-Fi 6."
            ),
            organismo_nombre="JUNAEB",
            rut_comprador="60.908.000-0",
            monto_estimado=2100000000.0,
            fecha_cierre=future_20,
            items=[
                RealTenderItem(
                    correlativo=1,
                    codigo_producto="43211503",
                    nombre="Notebook educativo 14 pulgadas",
                    descripcion="Pantalla FHD, 16GB RAM, SSD 512GB, teclado en español y sistema operativo preinstalado.",
                    cantidad=4500.0,
                    unidad_medida="UNIDAD",
                    precio_referencial=420000.0,
                )
            ],
            expected_category="technology",
            expected_relevant=False,
            expected_concepts=[],
        ),
        RealTender(
            id=114,
            codigo_externo="7100-5-LP26",
            nombre="Servicio de soporte y mantenimiento de plataforma informática ERP",
            descripcion=(
                "Servicio de Registro Civil e Identificación requiere contratación de servicio "
                "de consultoría, soporte especializado y mantenimiento correctivo de bases de datos "
                "PostgreSQL y sistema ERP corporativo."
            ),
            organismo_nombre="Servicio de Registro Civil e Identificación",
            rut_comprador="60.501.000-6",
            monto_estimado=72000000.0,
            fecha_cierre=future_45,
            items=[
                RealTenderItem(
                    correlativo=1,
                    codigo_producto="81112200",
                    nombre="Servicio mensual de soporte TI",
                    descripcion="Soporte técnico 24/7 con SLA de 2 horas para incidencias críticas del sistema.",
                    cantidad=12.0,
                    unidad_medida="MES",
                    precio_referencial=5500000.0,
                )
            ],
            expected_category="technology",
            expected_relevant=False,
            expected_concepts=[],
        ),
        RealTender(
            id=115,
            codigo_externo="9300-3-LR26",
            nombre="Instalación de red de fibra óptica y cableado estructurado categoría 6A",
            descripcion=(
                "Superintendencia de Salud llama a licitación para la provisión y tendido de cableado "
                "estructurado UTP Cat 6A y enlaces de fibra óptica monomodo para sus dependencias centrales."
            ),
            organismo_nombre="Superintendencia de Salud",
            rut_comprador="60.819.000-8",
            monto_estimado=38000000.0,
            fecha_cierre=future_20,
            items=[
                RealTenderItem(
                    correlativo=1,
                    codigo_producto="26121609",
                    nombre="Punto de red cableado Cat 6A certificado",
                    descripcion="Instalación de punto de red doble con conector RJ45 y certificación Fluke.",
                    cantidad=180.0,
                    unidad_medida="UNIDAD",
                    precio_referencial=145000.0,
                )
            ],
            expected_category="technology",
            expected_relevant=False,
            expected_concepts=[],
        ),

        # ========================================================
        # 16-18: Negative Controls / Completely Irrelevant
        # ========================================================
        RealTender(
            id=116,
            codigo_externo="3401-20-LP26",
            nombre="Suministro de mezcla asfáltica en frío para bacheo de caminos rurales",
            descripcion=(
                "Dirección Provincial de Vialidad de Melipilla requiere la provisión de 500 toneladas "
                "de asfalto en frío para mantenimiento de calzadas y caminos vecinales no pavimentados."
            ),
            organismo_nombre="Dirección de Vialidad - MOP",
            rut_comprador="61.202.000-K",
            monto_estimado=45000000.0,
            fecha_cierre=future_20,
            items=[
                RealTenderItem(
                    correlativo=1,
                    codigo_producto="30121501",
                    nombre="Asfalto en frío granel",
                    descripcion="Mezcla asfáltica densa en frío modificada con polímeros para bacheo instantáneo.",
                    cantidad=500.0,
                    unidad_medida="TONELADA",
                    precio_referencial=85000.0,
                )
            ],
            expected_category="not_relevant",
            expected_relevant=False,
            expected_concepts=[],
        ),
        RealTender(
            id=117,
            codigo_externo="4102-1-LE26",
            nombre="Servicio de mantención preventiva de camiones tolva y maquinaria pesada",
            descripcion=(
                "Municipalidad de Paine contrata servicio técnico integral y cambio de repuestos "
                "para flota de camiones tolva recolectores y retroexcavadoras municipales."
            ),
            organismo_nombre="Municipalidad de Paine",
            rut_comprador="69.245.000-0",
            monto_estimado=32000000.0,
            fecha_cierre=future_45,
            items=[
                RealTenderItem(
                    correlativo=1,
                    codigo_producto="78181500",
                    nombre="Mantenimiento preventivo camión tolva",
                    descripcion="Revisión de frenos, sistema hidráulico, cambio de aceite y filtros de motor diésel.",
                    cantidad=8.0,
                    unidad_medida="UNIDAD",
                    precio_referencial=3800000.0,
                )
            ],
            expected_category="not_relevant",
            expected_relevant=False,
            expected_concepts=[],
        ),
        RealTender(
            id=118,
            codigo_externo="5210-6-LP26",
            nombre="Compra de combustible diésel grado B para flota vehicular de aseo",
            descripcion=(
                "Ilustre Municipalidad de San Bernardo licita el suministro continuo de combustible "
                "diésel mediante tarjetas electrónicas para vehículos municipales durante el año 2026."
            ),
            organismo_nombre="Municipalidad de San Bernardo",
            rut_comprador="69.256.000-5",
            monto_estimado=98000000.0,
            fecha_cierre=future_20,
            items=[
                RealTenderItem(
                    correlativo=1,
                    codigo_producto="15101505",
                    nombre="Combustible diésel petróleo",
                    descripcion="Litros de diésel ultra bajo azufre despachados en estación de servicio.",
                    cantidad=110000.0,
                    unidad_medida="LITRO",
                    precio_referencial=870.0,
                )
            ],
            expected_category="not_relevant",
            expected_relevant=False,
            expected_concepts=[],
        ),

        # ========================================================
        # 19-20: Edge Cases & Ambiguous Tenders (Low Confidence / Boundary)
        # ========================================================
        RealTender(
            id=119,
            codigo_externo="9900-1-LR26",
            nombre="Servicio de mantención general",
            descripcion="Se solicita cotización para mantenciones menores en dependencias.",
            organismo_nombre="Delegación Presidencial Provincial",
            rut_comprador="60.301.000-1",
            monto_estimado=3500000.0,
            fecha_cierre=future_20,
            items=[
                RealTenderItem(
                    correlativo=1,
                    codigo_producto="72101500",
                    nombre="Mantención menor",
                    descripcion="Trabajos varios de reparación.",
                    cantidad=1.0,
                    unidad_medida="GLOBAL",
                    precio_referencial=3500000.0,
                )
            ],
            expected_category="not_relevant",
            expected_relevant=False,  # Extremely sparse text -> triggers low confidence / human review
            expected_concepts=[],
        ),
        RealTender(
            id=120,
            codigo_externo="8700-15-LP26",
            nombre="Adquisición de vehículos y furgones para traslado de personal y equipamiento",
            descripcion=(
                "Servicio de Salud O'Higgins licita furgones de transporte con rampa hidráulica "
                "posterior para traslado mixto de insumos hospitalarios y personal técnico de apoyo."
            ),
            organismo_nombre="Servicio de Salud O'Higgins",
            rut_comprador="61.603.000-8",
            monto_estimado=68000000.0,
            fecha_cierre=future_45,
            items=[
                RealTenderItem(
                    correlativo=1,
                    codigo_producto="25101503",
                    nombre="Furgón de carga y traslado",
                    descripcion="Furgón diésel adaptado con anclajes universales y rampa elevadora para carga pesada.",
                    cantidad=2.0,
                    unidad_medida="UNIDAD",
                    precio_referencial=32000000.0,
                )
            ],
            expected_category="health",
            expected_relevant=True,
            expected_concepts=["rampa_de_acceso"],
        ),
    ]
