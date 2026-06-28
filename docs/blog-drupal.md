# Blog en Drupal 7.30 (Docker)

Se construye una imagen propia con **Drupal 7.30 sobre PHP 5.6**
([../docker/Dockerfile.drupal](../docker/Dockerfile.drupal)). Esa versión
(anterior a 7.32 y a 7.58) es vulnerable a **Drupalgeddon** (SA-CORE-2014-005,
SQLi) y a **Drupalgeddon2** (CVE-2018-7600, RCE no autenticado). Por eso no se
usa la imagen oficial `drupal:7`, que trae la última versión sobre PHP 8 (donde
7.30 ni siquiera arranca).

## Puesta en marcha

El blog forma parte del **stack único** de la raíz (ver [instalacion.md](instalacion.md)).
Se levanta junto al resto y se siembra una sola vez:

```bash
docker compose up -d --build                       # construye y arranca TODO
docker compose exec drupal bash /seed/seed_blog.sh # contenido del blog (1ª vez)
```

El script instala Drupal con drush (creando la BD, instalando el cliente MySQL y
silenciando el correo) y crea categorías, autores ficticios y artículos. Al
terminar imprime la versión de Drupal y el número de artículos.

- Blog: **http://localhost:8080** · Admin de Drupal: `admin` / `admin123`
- El botón **Blog** de la web pública apunta a esta instancia (`BLOG_URL`).

La instalación (`settings.php` + ficheros) vive en el volumen `drupal_data` y
**sobrevive** a reinicios. Empezar de cero: `docker compose down -v`.

## Comprobar la versión

Desde el navegador, `http://localhost:8080/CHANGELOG.txt` (la 1ª línea es
`Drupal 7.30, …`), o por terminal: `docker compose exec drupal drush status`.

## Explotación (Drupalgeddon2)

La RCE se demostró con Metasploit (`exploit/unix/webapp/drupal_drupalgeddon2`):
`RHOSTS 127.0.0.1`, `RPORT 8080`, `TARGETURI /`, `PHP_FUNC passthru` → sesión
Meterpreter como `www-data` dentro del contenedor.
