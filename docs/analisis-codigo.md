# Análisis de código y seguridad

FakeEnv se audita con varias familias de análisis **complementarias**: cada una
mira el sistema desde un ángulo distinto y detecta cosas que las demás no ven.
Los scripts viven en `analisis_codigo/<tipo>/` y vuelcan sus informes a
`analisis_codigo/<tipo>/reportes_<herramienta>/` (esa carpeta está en
`.gitignore`: contiene resultados, que se regeneran ejecutando los scripts).

Este documento explica **qué es y para qué sirve** cada tipo de análisis, no los
resultados concretos.

| Tipo | Carpeta | Herramienta | Qué examina | OWASP Top 10 |
|------|---------|-------------|-------------|--------------|
| SAST | `sast/` | bandit, semgrep | el código fuente | A03, A01… |
| DAST | `dast/` | OWASP ZAP | la app en ejecución | varias |
| SCA | `sca/` | pip-audit, trivy | dependencias e imágenes | **A06** |
| Secretos | `secrets/` | gitleaks | claves/credenciales en el repo | A02, A07 |
| IaC | `iac/` | hadolint, trivy config | Dockerfiles y compose | A05 |

---

## SAST — Static Application Security Testing

Analiza el **código fuente sin ejecutarlo**. Busca patrones peligrosos en la
propia lógica: concatenación de SQL, uso de `render_template_string`, hashes
débiles, deserialización insegura, etc. Es el análisis de "caja blanca": ve todo
el código pero no sabe qué se explota de verdad en runtime.

- **bandit**: específico de Python; revisa la app Flask.
- **semgrep**: reglas multi-lenguaje (`p/security-audit`, `p/flask`).

Sirve para encontrar la **causa raíz en el código** y señalar el fichero y la
línea exactos donde está el fallo.

## DAST — Dynamic Application Security Testing

Analiza la **aplicación en marcha**, atacándola desde fuera como lo haría un
atacante, sin ver el código ("caja negra"). Lanza peticiones y observa las
respuestas: cabeceras de seguridad ausentes, XSS reflejado, formularios sin
protección, etc.

- **OWASP ZAP** (modo baseline) contra la app (`:8000`) y el blog (`:8080`).

Sirve para validar el comportamiento **real** desplegado, incluido lo que SAST
no puede ver (configuración del servidor, cabeceras, sesiones).

## SCA — Software Composition Analysis

No mira *tu* código, sino el **código de terceros** que arrastras: librerías y
capas de las imágenes de contenedor. Cruza cada componente y su versión contra
bases de datos de vulnerabilidades conocidas (CVE) y reporta cuáles tienen
fallos publicados. Es el análisis que materializa **A06 — Componentes
vulnerables y desactualizados** (el motivo del Drupal 7.30 del laboratorio).

- **pip-audit**: audita las dependencias Python de `requirements.txt`.
- **trivy**: escanea las **imágenes Docker** (CVEs del SO base y de las
  librerías del sistema) y también las dependencias del proyecto.

Sirve para responder: "¿alguna de las piezas que uso tiene un agujero conocido y
un parche disponible?".

## Secretos — Secret Scanning

Busca **credenciales hardcodeadas**: claves de API, contraseñas, tokens,
`SECRET_KEY`, etc., tanto en los ficheros actuales como en el **historial de
git** (un secreto borrado sigue vivo en commits antiguos). Relacionado con
**A02 (fallos criptográficos)** y **A07 (identificación y autenticación)**.

- **gitleaks**: escanea el árbol de trabajo y todo el historial de commits.

Sirve para detectar secretos filtrados antes de que acaben en un repositorio
público o en una imagen.

## IaC — Infrastructure as Code

Analiza los ficheros de **infraestructura y despliegue** (Dockerfiles,
`docker-compose.yml`) en busca de malas prácticas de seguridad: contenedores que
corren como root, ausencia de `USER`, secretos en variables de entorno,
imágenes base sin fijar, etc. Cae bajo **A05 — Configuración de seguridad
defectuosa**.

- **hadolint**: linter de buenas prácticas de Dockerfile.
- **trivy config**: detecta configuraciones inseguras en Dockerfiles y compose.

Sirve para asegurar que el *cómo se despliega* la aplicación no introduzca
fallos al margen del código.

---

## Cómo ejecutarlos

Cada script es autónomo y deja sus informes en su carpeta `reportes_*`:

```bash
# SCA
bash analisis_codigo/sca/pip-audit.sh
bash analisis_codigo/sca/trivy.sh          # requiere las imágenes construidas

# Secretos
bash analisis_codigo/secrets/gitleaks.sh

# IaC
bash analisis_codigo/iac/hadolint.sh
bash analisis_codigo/iac/trivy-config.sh
```

- **pip-audit** se instala en el entorno virtual (`pip install pip-audit`).
- **gitleaks**, **hadolint** y **trivy** son binarios únicos en `~/.local/bin`.
- **DAST** requiere el stack levantado (`docker compose up -d`); **SCA de
  imágenes** requiere haberlas construido (`docker compose build`).
