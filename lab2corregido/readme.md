# 🌳 Implementación de Árbol de Merkle en Python

Este proyecto es una implementación interactiva de un **Árbol de Merkle** (*Merkle Tree*) desarrollada en Python. Permite construir el árbol a partir de un conjunto de transacciones, visualizar su estructura jerárquica en la consola, realizar pruebas de inclusión (*Audit Proofs*) y simular la alteración de datos para verificar la inmutabilidad de la raíz.

---

## 🤖 Declaración de Uso de Inteligencia Artificial

En cumplimiento con las buenas prácticas académicas y de desarrollo, se declara explícitamente el uso de **Inteligencia Artificial (Gemini / ChatGPT)** en las siguientes secciones del código:

### 1. Visualización Gráfica en Consola
* **Función:** `adaptar_a_formato_grafico()` / `mostrar_grafico_arbol()`
* **Aporte de la IA:** Adaptación recursiva para mapear la estructura personalizada `NodoMerkle` a la librería externa `binarytree`, recortando los hashes a 8 caracteres para mantener la legibilidad visual en la terminal.

### 2. Algoritmo de Búsqueda de Ruta de Verificación (*Audit Proof*)
* **Función:** `localizar_ruta_hermanos()`
* **Aporte de la IA:** Implementación de la búsqueda recursiva a través del árbol binario para recolectar las parejas de hashes hermanos (*Proof Path*) necesarias para validar una transacción sin procesar todo el árbol.

### 3. Refactorización de Nombres y Estructura
* **Ámbito:** Nombres de variables, clases y funciones.
* **Aporte de la IA:** Renombrado general del código fuente para mejorar la legibilidad y cumplir con estándares de nombrado claros (*Clean Code*).

---

## 📖 Explicación del Código

El programa está estructurado de manera modular para separar la representación de datos, la construcción del árbol, la verificación criptográfica y la interfaz de usuario:

### 1. Estructura de Datos Base (`NodoMerkle`)
La clase `NodoMerkle` actúa como el bloque de construcción del árbol. Cada instancia contiene:
* `clave_hash`: El valor hash SHA-256 almacenado en el nodo.
* `izquierdo` y `derecho`: Punteros que apuntan a sus nodos hijos (son `None` en el caso de las hojas).

### 2. Captura y Hasheo de Datos (`registrar_transacciones`)
Solicita al usuario $n$ cadenas de texto (transacciones), aplica la función hash `hashlib.sha256()` a cada una en formato de bytes `.encode()`, y retorna una lista de strings hexadecimales.

### 3. Construcción Jerárquica (`generar_nivel_superior` y `construir_arbol_merkle`)
* **Balanceo de Nodos Impares:** Si la lista de nodos en un nivel es impar, la función duplica el último elemento (`nodos_actuales.append(nodos_actuales[-1])`) para permitir el agrupamiento en pares.
* **Agrupación y Hash Padre:** Toma pares contiguos (`hijo_izq`, `hijo_der`), concatena sus hashes (`hash_combinado`), genera el nuevo hash SHA-256 resultante y crea un nodo padre vinculando ambos hijos.
* **Reducción a la Raíz:** Mediante un bucle `while len(nodos_hoja) > 1`, se construyen niveles superiores hasta que queda un único nodo: la **Raíz de Merkle** (*Merkle Root*).

### 4. Simulación de Tampering / Alteración (`editar_transaccion`)
Permite seleccionar una hoja específica, modificar su contenido original y recalcular el árbol entero. Esto demuestra la **sensibilidad criptográfica**: un cambio mínimo en una sola transacción altera completamente la raíz resultante.

### 5. Adaptador de Visualización (`adaptar_a_formato_grafico` y `mostrar_grafico_arbol`)
Utiliza recursividad para convertir los objetos de la clase `NodoMerkle` a objetos `binarytree.Node`. Para evitar que la consola se desborde con cadenas de 64 caracteres, recorta cada hash a sus primeros 8 dígitos.

### 6. Prueba de Inclusión y Audit Proof (`verificar_pertenencia_bloque3` y `localizar_ruta_hermanos`)
* **`localizar_ruta_hermanos`:** Recorre recursivamente el árbol buscando el hash objetivo. Durante el retorno de la llamada recursiva, guarda en la lista `camino_verificacion` la tupla `("izquierda"|"derecha", hash_hermano)` del nodo adyacente.
* **`verificar_pertenencia_bloque3`:** Toma únicamente el hash inicial y la lista de hermanos recolectados, re-calculando el hash hacia arriba. Si el resultado final coincide con la raíz original (`hash_calculado == nodo_raiz.clave_hash`), la transacción se valida en tiempo $O(\log n)$.

### La IA Gemini fue usada para la redacción y presentacion apropiada de este readme
---

## 🛠️ Requisitos e Instalación

### Prerrequisitos
* **Python 3.10+**
## Como ejecutarlo:
copiar y pegar en la consola de comandos
```bash
python merkle_tree.py
```
### Dependencias
Instala la biblioteca necesaria para la representación visual en consola:

```bash
pip install binarytree

