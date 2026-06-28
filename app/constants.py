"""Shared constants for FakeEnv.

SECURITY_QUESTIONS is a deliberately weak set of account-recovery questions:
every answer is the kind of fact an attacker can usually find with a little
OSINT (social networks, public records, photos…). This reinforces the weak
recovery flow demonstrated in the auth blueprint (OWASP A07).
"""

SECURITY_QUESTIONS = [
    "¿Cuál es el nombre de tu padre?",
    "¿Cuál es el nombre de soltera de tu madre?",
    "¿En qué ciudad naciste?",
    "¿Cuál es el nombre de tu primera mascota?",
    "¿En qué colegio estudiaste de pequeño?",
    "¿Cuál es tu equipo de fútbol favorito?",
    "¿Cuál es el nombre de tu mejor amigo de la infancia?",
    "¿En qué calle vivías cuando eras niño?",
    "¿Cuál era la marca de tu primer coche?",
    "¿Cómo se llama tu hermano o hermana mayor?",
]
