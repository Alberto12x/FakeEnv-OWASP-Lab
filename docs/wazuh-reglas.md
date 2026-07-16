# Cheatsheet — Reglas de Wazuh (FakeEnv)

Guía práctica para escribir reglas personalizadas en `siem/config/local_rules.xml`. Los ejemplos salen del propio laboratorio.

> Las reglas de fábrica de Wazuh (web, MariaDB, ssh…) ya vienen dentro del contenedor `wazuh.manager`. Aquí solo se añade **encima** el significado de los eventos de FakeEnv.

---

## 1. Anatomía de una regla

```xml
<rule id="100110" level="12">
  <if_sid>100100</if_sid>
  <field name="event">^idor_invoice_access$</field>
  <description>IDOR: $(accessed_by) leyó una factura ajena (id $(id_factura))</description>
  <mitre><id>T1190</id></mitre>
  <group>attack,</group>
</rule>
```

| Elemento | Para qué sirve |
|----------|----------------|
| `id` | Identificador único. **Usa el rango 100000–120000** (reservado a reglas locales). |
| `level` | Severidad 0–15. Determina si genera alarma y cómo se prioriza. |
| `<if_sid>` | Esta regla solo se evalúa si antes disparó la regla padre (encadenamiento). |
| `<field>` | Condición sobre un campo decodificado (regex). |
| `<description>` | Texto de la alarma. Admite `$(campo)` para interpolar valores del log. |
| `<mitre><id>` | Técnica MITRE ATT&CK asociada (opcional, recomendable). |
| `<group>` | Etiquetas para agrupar/filtrar alarmas. |

---

## 2. Niveles (`level`) — qué severidad poner

| Nivel | Uso típico | ¿Alarma? |
|-------|-----------|----------|
| 0 | Silenciar (ignorar evento) | No |
| 3 | Evento informativo, base de encadenamiento | Traza |
| 5–7 | Eventos relevantes (login OK, reset password) | Baja |
| 8–10 | Sospechoso (login fallido, subida de fichero, alta de admin) | Media |
| 12–15 | Ataque confirmado (IDOR, RCE, bypass) | Alta |

Regla práctica: **la regla base va en 3** y las hijas suben el nivel según la gravedad.

---

## 3. Los tres patrones que usarás el 90% del tiempo

### 3.1 Regla base (madre) — ancla en el decoder JSON

Toda la cadena cuelga de una regla que reconoce el origen del log. No lleva `if_sid`: la dispara directamente el decoder JSON integrado de Wazuh.

```xml
<rule id="100100" level="3">
  <decoded_as>json</decoded_as>
  <field name="logger">^fakenv$</field>
  <description>FakeEnv: evento $(event) (user_id=$(user_id), ip=$(ip))</description>
</rule>
```

### 3.2 Regla hija — un evento concreto (`if_sid` + `field`)

El caso más común: sobre la base, filtra por el nombre del evento.

```xml
<rule id="100101" level="8">
  <if_sid>100100</if_sid>
  <field name="event">^login_failed$</field>
  <description>Login fallido para "$(identifier)" desde $(ip)</description>
  <mitre><id>T1110</id></mitre>
</rule>
```

### 3.3 Regla de frecuencia — correlación en el tiempo

Salta cuando algo se repite N veces en un intervalo. Aquí se detecta fuerza bruta:

```xml
<rule id="100102" level="10" frequency="5" timeframe="60">
  <if_matched_sid>100101</if_matched_sid>   <!-- 5 login_failed... -->
  <same_field>ip</same_field>                <!-- ...desde la MISMA ip... -->
  <description>Posible fuerza bruta (5+ fallos en 60s) desde $(ip)</description>
</rule>
```

`frequency="5"` = a la **quinta** coincidencia salta (el contador empieza en 0, ojo con el desfase de 1). `timeframe` en segundos.

---

## 4. Condiciones sobre campos (`<field>`)

`<field>` compara un campo contra una **expresión regular**, no contra otro campo.

```xml
<field name="event">^login_failed$</field>     <!-- igualdad exacta -->
<field name="path">/admin</field>              <!-- contiene -->
<field name="status">^4\d\d$</field>           <!-- regex: 4xx -->
<field name="role" negate="yes">^user$</field> <!-- NO es user -->
```

- Ancla con `^...$` para igualdad exacta; sin anclas es "contiene".
- `negate="yes"` invierte la condición.
- Otras condiciones útiles: `<srcip>`, `<program_name>`, `<match>` (texto crudo en el log), `<pcre2>` (regex avanzada).

---

## 5. Comparar campos entre sí

Wazuh **no compara dos campos de la misma línea** (no existe `campoA != campoB`). Dos soluciones:

**A) Dentro de un mismo log → decide en la app.** La aplicación compara y emite un evento (o un flag booleano); la regla solo lo reconoce:

```xml
<field name="event">^idor_invoice_access$</field>   <!-- la app ya sabía que owner != accessor -->
```

**B) Entre dos eventos → `same_field` / `not_same_field`** (requiere `frequency`/`timeframe`):

```xml
<rule id="100150" level="10" frequency="2" timeframe="120">
  <if_matched_sid>100103</if_matched_sid>   <!-- login_success -->
  <same_field>username</same_field>          <!-- mismo usuario... -->
  <not_same_field>ip</not_same_field>        <!-- ...pero IP distinta -->
  <description>$(username) inicia sesión desde IPs distintas</description>
</rule>
```

---

## 6. Encadenamiento: `if_sid` vs `if_matched_sid`

| Directiva | Significado |
|-----------|-------------|
| `<if_sid>X</if_sid>` | Evalúa esta regla **solo si** el mismo evento ya casó la regla X (jerarquía sobre un único log). |
| `<if_matched_sid>X</if_matched_sid>` | Salta si la regla X casó **N veces** (`frequency`) dentro de `timeframe` (correlación entre varios logs). |
| `<if_group>web,</if_group>` | Como `if_sid` pero sobre un grupo de reglas, no una en concreto. |

---

## 7. Interpolar valores en la descripción

Usa `$(nombre_campo)` para meter datos del log en la alarma:

```xml
<description>Alta de usuario $(new_user) ($(new_role)) por $(actor)</description>
```

Los campos disponibles son los del JSON del evento **más** el contexto que añade la app automáticamente: `ip`, `method`, `path`, `user_id`, `user_agent`.

---

## 8. MITRE y grupos

```xml
<mitre><id>T1110</id></mitre>     <!-- Brute Force -->
<group>authentication_failures,</group>
```

- El `<id>` MITRE enriquece la alarma en el dashboard (táctica/técnica). La coma final en `<group>` es la convención de Wazuh.
- Técnicas usadas en el laboratorio: `T1110` (fuerza bruta), `T1190` (explotación de app web), `T1083` (descubrimiento de ficheros).

---

## 9. Flujo de trabajo: crear y probar una regla

1. **Averigua los campos** del log real:
   ```bash
   tail -f logs/app/fakenv.log
   ```
2. **Escribe la regla** en `siem/config/local_rules.xml`, dentro de `<group name="fakenv,"> ... </group>`, con un `id` libre del rango 1001xx.
3. **Recarga el manager** (el fichero está montado por volumen, no hace falta rebuild):
   ```bash
   docker compose restart wazuh
   ```
4. **Prueba en seco** con el simulador de logs de Wazuh:
   ```bash
   docker compose exec wazuh /var/ossec/bin/wazuh-logtest
   # pega una línea del log y mira qué regla dispara y con qué nivel
   ```
5. **Verifica la alarma** en `alerts.json` o en el dashboard (https://localhost).

> `wazuh-logtest` es tu mejor amigo: te dice exactamente qué regla casó, el nivel y los campos decodificados, sin esperar a que ocurra el evento real.

---

## 10. Errores frecuentes

- **`id` fuera del rango local** (usa 100000–120000) o repetido → Wazuh ignora el fichero entero.
- **Olvidar `^...$`** en `<field>` → casa de más ("contiene" en vez de "es igual").
- **`frequency` sin `timeframe`** (o al revés) → la correlación no funciona.
- **XML mal formado** (etiqueta sin cerrar) → el manager no arranca; revisa los logs con `docker compose logs wazuh`.
- **Esperar comparar dos campos en un `<field>`** → no se puede; ver sección 5.

---

Referencias del proyecto: [SIEM.md](SIEM.md) · reglas reales en [../siem/config/local_rules.xml](../siem/config/local_rules.xml).
