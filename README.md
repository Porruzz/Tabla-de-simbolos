Implementación de un Analizador Léxico, Sintáctico, AST, Tabla de Símbolos y Generación de Código Intermedio (3AC) para un Subconjunto de Python
1. Descripción General del Proyecto

Este proyecto implementa un compilador educativo que procesa un subconjunto del lenguaje Python usando una gramática basada en la especificación oficial de Python (PEG Grammar). El compilador realiza las etapas fundamentales del proceso de traducción:

Análisis léxico

Análisis sintáctico

Construcción del Árbol de Sintaxis Abstracta (AST)

Construcción de la tabla de símbolos

Generación de código intermedio en tres direcciones (Three-Address Code, 3AC)

El proyecto tiene fines académicos y demuestra la arquitectura modular de un compilador real, implementado en Python y ejecutado en entornos Linux, preferiblemente Kali Linux.

2. Estructura del Proyecto

El proyecto se organiza de manera modular para facilitar su comprensión y mantenimiento:

|-- tokens.py          # Definición de tokens del lenguaje
|-- lexer.py           # Analizador léxico
|-- parser.py          # Analizador sintáctico (descenso recursivo)
|-- astnodes.py        # Definición de nodos del AST
|-- symtable.py        # Construcción y gestión de la tabla de símbolos
|-- codegen3ac.py      # Generación de código intermedio (3AC)
|-- main.py            # Archivo principal de orquestación
|-- prom1.mpy          # Ejemplo de programa de entrada
|-- README.md          # Este documento


Cada componente cumple una función específica dentro del pipeline de compilación.

3. Flujo de Procesamiento

El compilador sigue una secuencia ordenada de etapas:

3.1. Análisis Léxico

El archivo lexer.py lee el código fuente y produce una lista de tokens con información relevante: tipo, lexema y posición.

3.2. Análisis Sintáctico

El analizador sintáctico (parser.py) recibe la secuencia de tokens y valida que el código cumpla las reglas de la gramática, generando a su vez el AST.

3.3. Árbol de Sintaxis Abstracta (AST)

El módulo astnodes.py define las clases correspondientes a las estructuras internas del lenguaje (asignaciones, expresiones, funciones, llamadas, etc.).
El parser construye este árbol de manera jerárquica.

3.4. Tabla de Símbolos

En symtable.py se implementa la construcción de tablas de símbolos por alcance (global y locales), almacenando información sobre variables, funciones y parámetros.

3.5. Código Intermedio (3AC)

El módulo codegen3ac.py convierte el AST en un conjunto de instrucciones de tres direcciones para representar operaciones de manera más cercana al nivel máquina.

4. Ejemplo de Entrada

El archivo prom1.mpy incluye un programa de prueba:

x = 10
y = 20

def sumar(a, b):
    c = a + b
    return c

z = sumar(x, y)
print(z)


Este archivo permite validar todas las etapas del compilador, incluyendo funciones, variables, expresiones aritméticas y llamadas.

5. Formas de Ejecución

El compilador se controla desde el archivo principal main.py.
Las siguientes instrucciones deben ejecutarse desde la línea de comandos, ubicándose previamente en el directorio del proyecto.

5.1. Mostrar únicamente los tokens generados
python3 main.py prom1.mpy --tokens

5.2. Visualizar el Árbol de Sintaxis Abstracta (AST)
python3 main.py prom1.mpy --ast

5.3. Mostrar la tabla de símbolos
python3 main.py prom1.mpy --symtable

5.4. Generar el código intermedio (3AC)
python3 main.py prom1.mpy --3ac

5.5. Ejecutar todas las fases del compilador
python3 main.py prom1.mpy --tokens --ast --symtable --3ac

6. Requisitos Previos

Python 3.8 o superior

Sistema operativo Linux (recomendado: Kali Linux)

Editor de texto o IDE a elección

Estructura del proyecto completa y archivos ubicados correctamente

7. Objetivo Académico

Este trabajo tiene como propósito reforzar los conceptos fundamentales del diseño de compiladores, permitiendo al estudiante comprender e implementar:

El funcionamiento interno de un lexer y parser

La utilidad del AST para la representación estructurada del programa

La creación y mantenimiento de tablas de símbolos

La traducción del código fuente a una representación intermedia

El proyecto demuestra una implementación clara, modular y funcional de un compilador básico.
