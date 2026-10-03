# Estrategia de DNS — MercadoInsight

Este documento define la arquitectura de dominios, la evaluación técnica de subdominios, la matriz de registros DNS requeridos, las políticas de TTL y los procedimientos de propagación y validación para **MercadoInsight**.

---

## 1. Arquitectura de Dominios

### 1.1 Dominio Principal y Manejo de `www`
* **Dominio Canónico**: `mercadoinsight.cl` (Apex / Naked domain).
* **Tratamiento de `www`**: El subdominio `www.mercadoinsight.cl` se resuelve a través de un registro CNAME y es redirigido permanentemente (HTTP 301) hacia el dominio raíz en NGINX. Esto consolida el posicionamiento SEO, evita duplicidad de cookies y unifica las métricas de tráfico.

### 1.2 Evaluación: Dominio Unificado vs Subdominio API

| Criterio | Dominio Unificado (`mercadoinsight.cl/api`) | Subdominio Separado (`api.mercadoinsight.cl`) | Decisión para MercadoInsight |
| :--- | :--- | :--- | :--- |
| **Peticiones Preflight CORS** | **Cero**: Peticiones mismo origen. No requieren `OPTIONS`. | Obligatorio en cada petición con headers personalizados. | **Unificado**: Ahorra 30-100ms por request. |
| **Certificados TLS** | Un único certificado para todo el sitio. | Requiere certificado SAN adicional o comodín (`*.`). | **Unificado**: Menor complejidad operativa. |
| **Políticas de Cookies** | `SameSite=Lax` / `Strict` funciona sin fricción. | Requiere `SameSite=None; Secure` para cookies compartidas. | **Unificado**: Mayor seguridad contra CSRF. |
| **Routing y Edge** | NGINX centraliza frontend y API en un solo contenedor. | Requiere balanceo perimetral o proxy adicional. | **Unificado**: Arquitectura más compacta. |

> **Decisión Definitiva**: Adoptar el **modelo de dominio unificado** (`mercadoinsight.cl` para frontend y `/api` para backend).

---

## 2. Matriz de Registros DNS de Producción

| Tipo | Nombre (Host) | Valor / Destino | TTL Recomendado | Propósito |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `@` (mercadoinsight.cl) | `<IP_PUBLICA_SERVIDOR>` | `300` (inicio) / `3600` (estable) | Resolución IPv4 del dominio raíz. |
| **AAAA** | `@` (mercadoinsight.cl) | `<IPV6_SERVIDOR>` (si aplica) | `3600` | Resolución IPv6 para clientes modernos. |
| **CNAME** | `www` | `mercadoinsight.cl.` | `3600` | Alias canónico redirigido por NGINX. |
| **A** | `staging` | `<IP_PUBLICA_STAGING>` | `300` | Servidor del entorno de pre-producción. |
| **CAA** | `@` | `0 issue "letsencrypt.org"` | `86400` | Autoriza exclusivamente a Let's Encrypt para emitir certificados. |
| **CAA** | `@` | `0 issuewild ";" ` | `86400` | Prohíbe la emisión no autorizada de certificados comodín. |
| **TXT** | `@` | `v=spf1 include:_spf.proveedor.com ~all` | `3600` | SPF: Autoriza servidores de envío para alertas de Alertmanager. |
| **TXT** | `_dmarc` | `v=DMARC1; p=reject; rua=mailto:dmarc@mercadoinsight.cl` | `3600` | DMARC: Política estricta contra suplantación de identidad. |

---

## 3. Política de TTL (Time to Live)

El TTL determina cuánto tiempo los resolvers DNS de internet almacenan en caché las respuestas:

1. **Fase de Despliegue / Migración**:
   - Configurar `TTL = 300` (5 minutos) 48 horas antes de cualquier migración de IP o cambio de servidor.
   - Permite que cualquier corrección o reversión de emergencia se propague a nivel global en menos de 5 minutos.
2. **Fase de Operación Estable**:
   - Una vez estabilizado el servicio, elevar a `TTL = 3600` (1 hora) para registros A/CNAME y `TTL = 86400` (24 horas) para registros CAA y TXT.
   - Reduce consultas redundantes y mejora la velocidad de resolución inicial para los usuarios.

---

## 4. Proveedores DNS Recomendados

1. **Cloudflare**:
   - DNS Anycast global ultrarrápido (<15ms de latencia).
   - Soporte para CNAME Flattening en el ápice (`@`).
   - Mitigación básica de ataques DDoS a nivel DNS.
2. **AWS Route 53 / Azure DNS / Google Cloud DNS**:
   - Recomendados si la infraestructura está alojada íntegramente en la nube correspondiente.
3. **NIC Chile**:
   - Registro primario del dominio `.cl`. Se configuran los nameservers delegados hacia el proveedor DNS seleccionado (ej. `ns1.cloudflare.com`).

---

## 5. Procedimientos de Validación y Verificación

Para comprobar que los registros se propagaron correctamente y responden a la IP esperada:

```bash
# Verificar registro A de producción
dig +short A mercadoinsight.cl

# Verificar resolución CNAME de www
dig +short CNAME www.mercadoinsight.cl

# Verificar registros CAA
dig CAA mercadoinsight.cl

# Verificar propagación en resolvers públicos principales
dig @1.1.1.1 mercadoinsight.cl     # Cloudflare DNS
dig @8.8.8.8 mercadoinsight.cl     # Google Public DNS

# En Windows (PowerShell):
Resolve-DnsName -Name mercadoinsight.cl -Type A
Resolve-DnsName -Name www.mercadoinsight.cl -Type CNAME
```
