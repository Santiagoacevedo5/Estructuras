# Librería estándar de Python utilizada para generar hashes
import hashlib


class NodoMerkle:
    """Representa un nodo dentro de la estructura del árbol de Merkle."""

    def __init__(self, clave_hash):
        """Inicializa un nodo con su hash y sus enlaces a nodos hijos."""
        self.clave_hash = clave_hash
        self.izquierdo = None
        self.derecho = None


def registrar_transacciones(cantidad):
    """Solicita los datos de entrada y genera sus hashes SHA-256.
    Args: cantidad: Número de registros a procesar.
    Returns: Lista con las huellas digitales (hashes) generadas."""

    lista_hashes = []
    for indice in range(cantidad):
        entrada = input(f"Ingrese la transacción #{indice + 1}: ")
        # Se genera el hash SHA-256 de la transacción.
        hash_generado = hashlib.sha256(entrada.encode()).hexdigest()
        lista_hashes.append(hash_generado)

    return lista_hashes


def generar_nivel_superior(nodos_actuales):
    """Construye el siguiente nivel jerárquico del árbol.
    Args: nodos_actuales: Lista de nodos del nivel presente.
    Returns: Lista con los nuevos nodos del nivel superior."""

    # Si la cantidad de nodos es impar, se duplica el último nodo
    if len(nodos_actuales) % 2 != 0:
        nodos_actuales.append(nodos_actuales[-1])

    siguiente_nivel = []

    # Se agrupan los nodos de dos en dos.
    for i in range(0, len(nodos_actuales), 2):
        hijo_izq, hijo_der = nodos_actuales[i], nodos_actuales[i + 1]
        # Se unen las cadenas hash de los nodos inferiores.
        hash_combinado = hijo_izq.clave_hash + hijo_der.clave_hash
        # Se calcula el hash correspondiente al nodo padre.
        hash_padre = hashlib.sha256(hash_combinado.encode()).hexdigest()
        nodo_padre = NodoMerkle(hash_padre)
        # Se vinculan los nodos inferiores con el nodo padre.
        nodo_padre.izquierdo = hijo_izq
        nodo_padre.derecho = hijo_der
        siguiente_nivel.append(nodo_padre)

    return siguiente_nivel


def construir_arbol_merkle(lista_hashes):
    """Construye el árbol completo hasta llegar a la raíz.
    Args: lista_hashes: Lista de hashes de los datos iniciales.
    Returns: Objeto nodo que representa la raíz del árbol."""

    # Creación de los nodos hoja iniciales.
    nodos_hoja = [NodoMerkle(h) for h in lista_hashes]
    # Se combinan niveles progresivamente hasta obtener la raíz única.
    while len(nodos_hoja) > 1:
        nodos_hoja = generar_nivel_superior(nodos_hoja)
    return nodos_hoja[0]


def editar_transaccion(hojas_hash, nodo_raiz):
    """Permite alterar un registro y recalcular la raíz del árbol.
    Args: hojas_hash: Lista de hashes base. nodo_raiz: Raíz actual del árbol."""

    print("\nModificación de bloque\n")
    indice_bloque = int(input("Qué bloque desea modificar (0-4): "))
    nueva_entrada = input("Ingrese la transacción modificada: ")
    # Se actualiza el hash de la posición elegida.
    hojas_hash[indice_bloque] = hashlib.sha256(nueva_entrada.encode()).hexdigest()
    # Se reconstruye la estructura con el cambio.
    raiz_actualizada = construir_arbol_merkle(hojas_hash)
    print(f"\nRaíz original: {nodo_raiz.clave_hash}")
    print(f"Raíz modificada: {raiz_actualizada.clave_hash}\n")
    # Se despliega el gráfico con el árbol resultante.
    print("Árbol modificado:")
    mostrar_grafico_arbol(raiz_actualizada)


def obtener_lineas_ascii(nodo):
    """Genera recursivamente las líneas formateadas en ASCII para construir la jerarquía."""
    if nodo is None:
        return [], 0, 0, 0

    etiqueta = f"[{nodo.clave_hash[:8]}]"

    # Si es una hoja (sin hijos)
    if nodo.izquierdo is None and nodo.derecho is None:
        linea = etiqueta
        ancho = len(linea)
        alto = 1
        centro = ancho // 2
        return [linea], ancho, alto, centro

    # Recursión para el hijo izquierdo y derecho
    lineas_izq, ancho_izq, alto_izq, centro_izq = obtener_lineas_ascii(nodo.izquierdo)
    lineas_der, ancho_der, alto_der, centro_der = obtener_lineas_ascii(nodo.derecho)

    ancho_etiqueta = len(etiqueta)

    # Espaciado entre subárboles
    separacion = 2
    ancho_total = max(ancho_izq + separacion + ancho_der, ancho_etiqueta)

    # Cálculo de posiciones de conexión
    centro_real_izq = centro_izq
    centro_real_der = ancho_izq + separacion + centro_der
    centro_padre = (centro_real_izq + centro_real_der) // 2

    # Línea 1: El nodo actual (padre)
    linea_padre = " " * (centro_padre - ancho_etiqueta // 2) + etiqueta
    linea_padre = linea_padre.ljust(ancho_total)

    # Línea 2: Ramas de conexión ASCII
    rama = [" "] * ancho_total
    rama[centro_real_izq] = "+"
    for i in range(centro_real_izq + 1, centro_padre):
        rama[i] = "-"
    rama[centro_padre] = "|"
    for i in range(centro_padre + 1, centro_real_der):
        rama[i] = "-"
    rama[centro_real_der] = "+"
    linea_rama = "".join(rama)

    # Combinación del nivel inferior
    lineas_combinadas = []
    max_alto = max(alto_izq, alto_der)

    for i in range(max_alto):
        izq_p = lineas_izq[i] if i < alto_izq else " " * ancho_izq
        der_p = lineas_der[i] if i < alto_der else " " * ancho_der
        lineas_combinadas.append(izq_p + " " * separacion + der_p)

    lineas_resultado = [linea_padre, linea_rama] + lineas_combinadas
    return lineas_resultado, len(linea_padre), len(lineas_resultado), centro_padre


def mostrar_grafico_arbol(nodo_raiz):
    """Muestra el diagrama ASCII completo en la terminal."""
    lineas, _, _, _ = obtener_lineas_ascii(nodo_raiz)
    for linea in lineas:
        print(linea)


def verificar_pertenencia_bloque3(nodo_raiz):
    """Ejecuta una verificación de inclusión para el bloque 3.
    Reconstruye la raíz usando únicamente la ruta de nodos hermanos."""

    print("\nPrueba de inclusión bloque 3\n")
    camino_verificacion = []
    bloque_entrada = input("Ingrese la transacción 3: ")
    hash_objetivo = hashlib.sha256(bloque_entrada.encode()).hexdigest()
    hash_calculado = hash_objetivo

    # Se recopilan los nodos necesarios para comprobar la validez.
    if localizar_ruta_hermanos(nodo_raiz, hash_objetivo, camino_verificacion):
        for posicion, hash_hermano in camino_verificacion:
            # La concatenación varía según la posición del nodo hermano.
            if posicion == "izquierda":
                union = hash_hermano + hash_calculado
            else:
                union = hash_calculado + hash_hermano
            # Cálculo del hash del nivel superior.
            hash_calculado = hashlib.sha256(union.encode()).hexdigest()
        # Verificación final contra la raíz almacenada.
        print(f"La transacción 3 es válida: {hash_calculado} == {nodo_raiz.clave_hash}")
    else:
        print(f"La transacción 3 NO es válida: {hash_calculado} != {nodo_raiz.clave_hash}")


def localizar_ruta_hermanos(nodo_actual, hash_objetivo, camino_verificacion):
    """Busca recursivamente la ruta de hashes hermanos para la prueba de inclusión.
    Returns: True si el hash existe dentro de las hojas; False en caso contrario."""

    # Identificación de nodos hoja.
    if nodo_actual.izquierdo is None and nodo_actual.derecho is None:
        return nodo_actual.clave_hash == hash_objetivo

    # Búsqueda en la rama izquierda.
    if nodo_actual.izquierdo and localizar_ruta_hermanos(nodo_actual.izquierdo, hash_objetivo, camino_verificacion):
        camino_verificacion.append(("derecha", nodo_actual.derecho.clave_hash))
        return True

    # Búsqueda en la rama derecha.
    if nodo_actual.derecho and localizar_ruta_hermanos(nodo_actual.derecho, hash_objetivo, camino_verificacion):
        camino_verificacion.append(("izquierda", nodo_actual.izquierdo.clave_hash))
        return True

    return False


def ejecutar_programa():
    """Gobernador del flujo principal de la aplicación."""
    print("\nConstruir árbol\n")
    num_registros = int(input("Ingrese el número de transacciones: "))
    # Obtención de los valores base.
    hojas_hashes = registrar_transacciones(num_registros)
    # Generación de la raíz inicial.
    raiz_principal = construir_arbol_merkle(hojas_hashes)
    print(f"\nRaiz: {raiz_principal.clave_hash}\n")
    print("Estructura del Árbol de Merkle (Diagrama ASCII):")
    mostrar_grafico_arbol(raiz_principal)

    # Ciclo de interacción del menú.
    while True:
        opcion = input(
            "\nSeleccione un experimento: \n1. Modificar un bloque \n2. Prueba de inclusión para el bloque 3 \n3. Salir\n"
        )
        match opcion:
            case "1":
                editar_transaccion(hojas_hashes, raiz_principal)
            case "2":
                verificar_pertenencia_bloque3(raiz_principal)
            case "3":
                break


# Punto de entrada del programa.
ejecutar_programa()
