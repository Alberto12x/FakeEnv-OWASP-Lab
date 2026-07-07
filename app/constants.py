"""Constantes compartidas de FakeEnv.

SECURITY_QUESTIONS es un conjunto de preguntas de recuperación débil a propósito:
toda respuesta es el tipo de dato que un atacante suele encontrar con algo de
OSINT (redes sociales, registros públicos, fotos…). Refuerza el flujo de
recuperación débil del blueprint de autenticación (A07).
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
