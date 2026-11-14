# ADR-013: Decisiones de implementación del MVP frente al plan original

**Estado:** Aceptado
**Fecha:** 2026-11-13

## Contexto
Entrega en un día, una sola persona, sin Docker, Git, JDK ni clave de API en el equipo (solo Python 3.15 y Node 26).

## Decisión
- **Persistencia:** SQLite con **consultas parametrizadas** (en lugar de PostgreSQL + pgvector).
- **Frontend:** JavaScript vanilla, sin build y **sin `innerHTML`/`eval`** (en lugar de React + Vite); el contenido dinámico se inserta como nodos de texto.
- **Arranque:** `py run.py` crea `.venv`, instala dependencias y levanta `uvicorn` (en lugar de Docker Compose).
- **Ejecución del código generado:** análisis estático previo y `node --permission` con lectura limitada al directorio temporal (sin red, sin procesos hijos, sin escritura) para la equivalencia.
- **Cobertura:** `--experimental-test-coverage` es incompatible con `--permission`; corre **sin permisos** pero solo después de que el mismo código haya pasado la ejecución restringida y el escaneo estático, con entorno vacío (sin la clave de API) y TEMP en el directorio del proyecto temporal.
- **Oráculo Python:** validación por AST (solo `decimal`/`math`), `python -I`, builtins restringidos, entorno vacío.
- Agentes: orquestador propio con hilos en el proceso; sin cola externa.

## Consecuencias
- Cero dependencias de infraestructura; fácil de ejecutar en el equipo de la demo.
- Menor aislamiento que un contenedor (el modo cobertura confía en el escaneo previo); sin RBAC, sin cifrado en reposo, sin conexión a Git ni RAG.
- Java/C# no se compilan; las pruebas de la UI son estáticas y capturas manuales.
- Estas desviaciones están reflejadas en `docs/plan/01_arquitectura_solucion.md` (planeado vs. implementado).
