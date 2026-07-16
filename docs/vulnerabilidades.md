# Vulnerabilidades (OWASP Top 10)

> ## ⚠️ Aviso: aplicación deliberadamente insegura
>
> Laboratorio educativo para un TFM sobre el **OWASP Top 10**. Contiene
> vulnerabilidades **a propósito**. **No la despliegues en Internet ni reutilices
> su código en producción.** Cada punto débil está marcado en el código con un
> comentario que empieza por `INTENTIONAL`/`INTENTIONALLY`.

| Componente | Debilidad intencionada | OWASP Top 10 (2021) |
|------------|------------------------|----------------------|
| Login | Sin rate limiting ni MFA | A07 – Identification & Authentication Failures |
| Contraseñas | Hash **MD5** con salt global del `.env` | A02 – Cryptographic Failures |
| Recuperación de contraseña | Pregunta de seguridad, respuesta en texto plano | A07 |
| Facturas | Acceso por `?id_factura=` sin comprobar propietario (**IDOR**) | A01 – Broken Access Control |
| Telemetría | Filtro de fechas con excepción mal controlada (*fail-open*): una fecha inválida ignora el filtro `user_id` y vuelca la telemetría de todos los usuarios | A01 – Broken Access Control |
| Perfil (mensaje) | **SSTI** vía `render_template_string` sobre datos del usuario | A03 – Injection |
| Foto de perfil | Subida de archivos sin `secure_filename`, sin validar tipo/tamaño | A04 / unrestricted file upload |
| Raíz del proyecto | Cualquier archivo servible como texto (`/.env`, `/config.py`…) y path traversal | A05 – Security Misconfiguration |
| Modo debug | Con `FLASK_DEBUG=1`, cualquier excepción muestra el depurador de Werkzeug (código fuente + consola = RCE) | A05 – Security Misconfiguration |
| Blog | Drupal 7.30 (EOL): SQLi *Drupalgeddon* (SA-CORE-2014-005) y RCE *Drupalgeddon2* (CVE-2018-7600) | A06 – Vulnerable & Outdated Components / A03 – Injection |

## Demostración rápida del IDOR

Inicia sesión como `ana.torres` y visita
`http://127.0.0.1:5000/dashboard/invoice?id_factura=7`: verás una factura que
pertenece a `carlos.ruiz`, sin ninguna comprobación de propiedad.

> Detección de estos ataques con el SIEM en [SIEM.md](SIEM.md).
