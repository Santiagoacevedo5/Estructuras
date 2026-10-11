#construccion arbol ABB
import random
import time

from lista import generar_estudiantes


class NodoABB:
    def __init__(self, estudiante):
        self.estudiante = estudiante
        self.izquierda = None
        self.derecha = None

def insertar_en_abb(raiz, estudiante):
    nuevo_nodo = NodoABB(estudiante)
    if raiz is None:
        return nuevo_nodo

    nodo_actual = raiz
    while True:
        if estudiante["id"] < nodo_actual.estudiante["id"]:
            if nodo_actual.izquierda is None:
                nodo_actual.izquierda = nuevo_nodo
                return raiz
            nodo_actual = nodo_actual.izquierda
        else:
            if nodo_actual.derecha is None:
                nodo_actual.derecha = nuevo_nodo
                return raiz
            nodo_actual = nodo_actual.derecha


def buscar_en_abb(raiz, id_buscado):
    nodo_actual = raiz
    while nodo_actual is not None:
        if nodo_actual.estudiante["id"] == id_buscado:
            return nodo_actual.estudiante
        elif id_buscado < nodo_actual.estudiante["id"]:
            nodo_actual = nodo_actual.izquierda
        else:
            nodo_actual = nodo_actual.derecha
    return None


def recorrer_abb_inorden(raiz):
    """Devuelve los estudiantes ordenados por ID (izquierda -> nodo -> derecha).
    Usa una pila en vez de recursión para no chocar con el límite de Python."""
    estudiantes_ordenados = []
    pila_pendientes = []
    nodo_actual = raiz
    while pila_pendientes or nodo_actual is not None:
        while nodo_actual is not None:      # bajar todo a la izquierda
            pila_pendientes.append(nodo_actual)
            nodo_actual = nodo_actual.izquierda
        nodo_actual = pila_pendientes.pop()            # el menor pendiente
        estudiantes_ordenados.append(nodo_actual.estudiante)
        nodo_actual = nodo_actual.derecha        # seguir con su subárbol derecho
    return estudiantes_ordenados


def calcular_altura_abb(raiz):
    """Altura calculada sin recursión (recorrido por niveles)."""
    if raiz is None:
        return 0
    nodos_del_nivel, altura = [raiz], 0
    while nodos_del_nivel:
        altura += 1
        nodos_del_nivel = [hijo for nodo in nodos_del_nivel
                           for hijo in (nodo.izquierda, nodo.derecha) if hijo]
    return altura


def construir_abb(estudiantes):
    raiz = None
    for estudiante in estudiantes:
        raiz = insertar_en_abb(raiz, estudiante)
    return raiz


def medir_busquedas_abb(raiz, cantidad_estudiantes):
    ids_a_buscar = random.sample(range(1, cantidad_estudiantes + 1), 100)

    inicio = time.perf_counter()
    for id_buscado in ids_a_buscar:
        buscar_en_abb(raiz, id_buscado)
    fin = time.perf_counter()

    return fin - inicio


if __name__ == "__main__":
    estudiantes = generar_estudiantes()

    # Insertando en orden aleatorio: el ABB queda mucho más balanceado
    estudiantes_mezclados = estudiantes[:]
    random.shuffle(estudiantes_mezclados)
    raiz_mezclada = construir_abb(estudiantes_mezclados)

    cantidad_estudiantes = len(estudiantes)
    print("ABB con IDs mezclados:    altura", calcular_altura_abb(raiz_mezclada),
          f"| tiempo 100 búsquedas: {medir_busquedas_abb(raiz_mezclada, cantidad_estudiantes):.6f} s")
