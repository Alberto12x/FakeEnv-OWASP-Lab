#!/usr/bin/env bash
#
# One-time installer + content seeder for the FakeEnv Drupal 7 blog.
# Run INSIDE the drupal container:
#   docker compose exec drupal bash /seed/seed_blog.sh
#
# It installs Drupal with drush, then creates categories, dummy authors and a
# set of realistic environmental articles.

set -e

DRUSH=/usr/local/bin/drush
DOCROOT=/var/www/html

# ── 1. Install drush 8 (8.1.18 still runs on the PHP 5.6 base) ────────────────
if [ ! -x "$DRUSH" ]; then
    echo "→ Instalando drush 8..."
    php -r "copy('https://github.com/drush-ops/drush/releases/download/8.1.18/drush.phar', '/tmp/drush.phar');"
    mv /tmp/drush.phar "$DRUSH"
    chmod +x "$DRUSH"
fi

# ── 1b. Install the MySQL client (drush needs it to create the database) ──────
if ! command -v mysql >/dev/null 2>&1; then
    echo "→ Instalando el cliente MySQL..."
    apt-get update -qq || true
    apt-get install -y -qq default-mysql-client >/dev/null 2>&1 \
        || apt-get install -y -qq mariadb-client >/dev/null 2>&1 \
        || apt-get install -y -qq mysql-client >/dev/null 2>&1 || true
fi
if ! command -v mysql >/dev/null 2>&1; then
    echo "✗ No se pudo instalar el cliente MySQL en el contenedor." >&2
    exit 1
fi

cd "$DOCROOT"

# ── 2. Wait for the database to accept connections ───────────────────────────
echo "→ Esperando a la base de datos..."
until php -r "new PDO('mysql:host=drupal_db;dbname=drupal','drupal','drupal');" 2>/dev/null; do
    sleep 3
done

# A no-op sendmail so Drupal's welcome e-mail doesn't error out (no MTA here).
if [ ! -x /usr/sbin/sendmail ]; then
    printf '#!/bin/sh\nexit 0\n' > /usr/sbin/sendmail
    chmod +x /usr/sbin/sendmail
fi

# ── 3. Install Drupal (standard profile) if not already installed ────────────
if ! "$DRUSH" status bootstrap 2>/dev/null | grep -qi "Successful"; then
    echo "→ Instalando Drupal 7..."
    # Remove any half-written settings from a previous failed attempt.
    chmod -R u+w sites/default 2>/dev/null || true
    rm -f sites/default/settings.php
    # Make the files directory (a Docker named volume) writable by Apache.
    mkdir -p sites/default/files
    chmod -R 0777 sites/default/files
    # --db-su lets drush create the database as root (the 'drupal' user has no
    # privilege to CREATE DATABASE). '|| true' keeps a harmless non-zero exit
    # (e.g. a mail warning) from aborting the script under 'set -e'.
    "$DRUSH" -y site-install standard \
        --db-url="mysql://drupal:drupal@drupal_db/drupal" \
        --db-su=root \
        --db-su-pw=root \
        --site-name="FakeEnv Blog" \
        --account-name=admin \
        --account-pass=admin123 \
        --account-mail=admin@fakenv.com || true
fi

# Make sure Drupal is actually installed before trying to seed content.
if ! "$DRUSH" status bootstrap 2>/dev/null | grep -qi "Successful"; then
    echo "✗ Drupal no se instaló correctamente." >&2
    exit 1
fi

# ── 4. Categories, authors and articles ──────────────────────────────────────
echo "→ Creando categorías, autores y artículos..."
"$DRUSH" php-eval '
$vocab = taxonomy_vocabulary_machine_name_load("tags");

function fe_term($vid, $name) {
    $found = taxonomy_get_term_by_name($name, "tags");
    if ($found) { return reset($found)->tid; }
    $t = new stdClass();
    $t->name = $name;
    $t->vid = $vid;
    taxonomy_term_save($t);
    return $t->tid;
}

function fe_user($name, $mail, $pass) {
    if (user_load_by_name($name)) { return; }
    $account = new stdClass();
    $account->is_new = TRUE;
    user_save($account, array(
        "name" => $name, "mail" => $mail, "pass" => $pass, "status" => 1,
        "init" => $mail,
    ));
}

function fe_article($title, $body, $author, $tid) {
    $existing = db_query("SELECT nid FROM {node} WHERE title = :t",
        array(":t" => $title))->fetchField();
    if ($existing) { return; }
    $account = user_load_by_name($author);
    $uid = $account ? $account->uid : 1;
    $node = new stdClass();
    $node->type = "article";
    node_object_prepare($node);
    $node->title = $title;
    $node->language = LANGUAGE_NONE;
    $node->uid = $uid;
    $node->status = 1;
    $node->promote = 1;
    $node->body[LANGUAGE_NONE][0]["value"] = $body;
    $node->body[LANGUAGE_NONE][0]["format"] = "filtered_html";
    $node->field_tags[LANGUAGE_NONE][0]["tid"] = $tid;
    node_save($node);
}

$t_agua  = fe_term($vocab->vid, "Ahorro de agua");
$t_energia = fe_term($vocab->vid, "Energía");
$t_hogar = fe_term($vocab->vid, "Hogar eficiente");
$t_clima = fe_term($vocab->vid, "Clima");

fe_user("ana_blog", "ana@blog.test", "password1");
fe_user("carlos_blog", "carlos@blog.test", "qwerty");
fe_user("lucia_blog", "lucia@blog.test", "lucia2024");

fe_article(
    "10 trucos para ahorrar agua en casa",
    "Reducir el consumo de agua es sencillo: instala aireadores en los grifos, "
    . "reutiliza el agua de lavar verduras para las plantas, repara las fugas a "
    . "tiempo y opta por duchas cortas. Pequeños gestos que ahorran miles de "
    . "litros al año y reducen tu factura.",
    "ana_blog", $t_agua);

fe_article(
    "Beneficios de la energía geotérmica",
    "La geotermia aprovecha el calor del subsuelo para climatizar viviendas con "
    . "una eficiencia muy superior a los sistemas tradicionales. Es estable "
    . "durante todo el año, tiene emisiones casi nulas y, aunque la inversión "
    . "inicial es alta, se amortiza en pocos años.",
    "carlos_blog", $t_energia);

fe_article(
    "Ventanas eficientes: cómo elegirlas",
    "El doble acristalamiento con cámara de aire y rotura de puente térmico "
    . "evita pérdidas de calor en invierno y entradas de calor en verano. "
    . "Fíjate en el factor solar y la transmitancia térmica para acertar.",
    "lucia_blog", $t_hogar);

fe_article(
    "Qué es la huella de carbono y cómo reducirla",
    "La huella de carbono mide las emisiones de CO2 asociadas a nuestra "
    . "actividad. Puedes reducirla consumiendo productos locales, moviéndote en "
    . "transporte público y mejorando el aislamiento de tu vivienda.",
    "ana_blog", $t_clima);

fe_article(
    "Paneles solares para autoconsumo: primeros pasos",
    "El autoconsumo fotovoltaico permite generar tu propia electricidad. "
    . "Analiza tu consumo, orienta los paneles al sur y estudia las ayudas "
    . "disponibles antes de dimensionar la instalación.",
    "carlos_blog", $t_energia);

echo "Contenido del blog creado correctamente.\n";
'

# ── 5. Summary ───────────────────────────────────────────────────────────────
ARTICLES=$("$DRUSH" sql-query "SELECT COUNT(*) FROM node WHERE type='article'" 2>/dev/null | tail -1)
echo "→ Versión de Drupal: $("$DRUSH" status 'Drupal version' --fields=drupal-version 2>/dev/null | tr -d ' ')"
echo "→ Artículos en el blog: ${ARTICLES}"
echo "✓ Blog Drupal listo en http://localhost:8080 (admin / admin123)"
