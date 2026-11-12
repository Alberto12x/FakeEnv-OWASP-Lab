# Política de seguridad

## ⚠️ Vulnerabilidades intencionadas

FakeEnv es un **laboratorio deliberadamente vulnerable**. Las debilidades
documentadas en [docs/vulnerabilidades.md](docs/vulnerabilidades.md) (IDOR,
SSTI, MD5, subida de archivos, Drupal 7.30, credenciales por defecto, etc.)
**son intencionadas** y no se van a corregir: no hace falta reportarlas.

## 🛡️ Uso seguro

- Ejecuta el laboratorio solo en local o en una red aislada (por defecto, los
  puertos se publican solo en `127.0.0.1`).
- No lo expongas a Internet ni reutilices sus contraseñas o su código.
- Ataca solo tu propia instancia.

## 📬 Qué sí reportar

Abre un *issue* o un *security advisory* privado en GitHub si encuentras algo
que pueda afectar **al equipo de quien ejecuta el laboratorio**, más allá de
los contenedores. Por ejemplo, un escape del contenedor provocado por la
configuración de Docker de este repositorio, o un secreto real publicado por
error.
