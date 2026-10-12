"""
Árbol B+ en Python.

Reglas del árbol (con orden m = número máximo de hijos de un nodo interno):
  - Cada nodo guarda como máximo m - 1 claves.
  - Los datos (valores) viven SOLO en las hojas.
  - Los nodos internos solo guardan claves "separadoras" para guiar la búsqueda:
        hijos[i] contiene claves >= claves[i-1]  y  < claves[i]
  - Todas las hojas están enlazadas en orden (atributo `siguiente`),
    lo que permite recorrer todo el árbol ordenado sin volver a subir.
  - Todas las hojas están a la misma profundidad.
"""

from bisect import bisect_left, bisect_right


class _NodoBPlus:
    """Un nodo del árbol. Puede ser hoja o nodo interno."""

    __slots__ = ("es_hoja", "claves", "hijos", "valores", "siguiente")

    def __init__(self, es_hoja):
        self.es_hoja = es_hoja
        self.claves = []      # claves ordenadas
        self.hijos = []       # solo nodos internos: len(hijos) == len(claves) + 1
        self.valores = []     # solo hojas: valores[i] corresponde a claves[i]
        self.siguiente = None  # solo hojas: la hoja de la derecha


class ArbolBPlus:
    def __init__(self, orden=4):
        if orden < 3:
            raise ValueError("El orden debe ser al menos 3")
        self.orden = orden
        self.max_claves = orden - 1
        self.min_claves = (orden + 1) // 2 - 1
        self.raiz = _NodoBPlus(es_hoja=True)
        self._cantidad_claves = 0

    def __len__(self):
        return self._cantidad_claves

    def __contains__(self, clave):
        return self.buscar(clave) is not None

    def _buscar_hoja(self, clave):
        """Baja desde la raíz hasta la hoja donde está (o estaría) la clave.
        Devuelve la hoja y el camino recorrido: lista de (nodo_interno, índice_del_hijo)."""
        nodo = self.raiz
        camino = []
        while not nodo.es_hoja:
            indice_hijo = bisect_right(nodo.claves, clave)
            camino.append((nodo, indice_hijo))
            nodo = nodo.hijos[indice_hijo]
        return nodo, camino

    def buscar(self, clave):
        """Devuelve el valor asociado a la clave, o None si no existe."""
        hoja, _ = self._buscar_hoja(clave)
        posicion = bisect_left(hoja.claves, clave)
        if posicion < len(hoja.claves) and hoja.claves[posicion] == clave:
            return hoja.valores[posicion]
        return None

    def insertar(self, clave, valor):
        """Inserta (clave, valor). Lanza KeyError si la clave ya existe."""
        hoja, camino = self._buscar_hoja(clave)
        posicion = bisect_left(hoja.claves, clave)
        if posicion < len(hoja.claves) and hoja.claves[posicion] == clave:
            raise KeyError(f"La clave {clave!r} ya existe")

        hoja.claves.insert(posicion, clave)
        hoja.valores.insert(posicion, valor)
        self._cantidad_claves += 1

        if len(hoja.claves) <= self.max_claves:
            return  # cabe, no hay que hacer nada más

        # La hoja se llenó de más: se divide en dos.
        mitad = len(hoja.claves) // 2
        nueva_hoja = _NodoBPlus(es_hoja=True)
        nueva_hoja.claves = hoja.claves[mitad:]
        nueva_hoja.valores = hoja.valores[mitad:]
        hoja.claves = hoja.claves[:mitad]
        hoja.valores = hoja.valores[:mitad]

        nueva_hoja.siguiente = hoja.siguiente
        hoja.siguiente = nueva_hoja

        # En una hoja, la primera clave de la nueva hoja se COPIA hacia el padre.
        self._insertar_en_padre(camino, nueva_hoja.claves[0], nueva_hoja)

    def _insertar_en_padre(self, camino, separador, nuevo_nodo):
        """Sube el separador y el nuevo nodo hacia los padres, dividiendo si hace falta."""
        while camino:
            padre, indice_hijo = camino.pop()
            padre.claves.insert(indice_hijo, separador)
            padre.hijos.insert(indice_hijo + 1, nuevo_nodo)

            if len(padre.claves) <= self.max_claves:
                return

            # El nodo interno se llenó de más: se divide.
            # En un nodo interno, la clave del medio SUBE (no se copia).
            mitad = len(padre.claves) // 2
            separador = padre.claves[mitad]
            nuevo_nodo = _NodoBPlus(es_hoja=False)
            nuevo_nodo.claves = padre.claves[mitad + 1:]
            nuevo_nodo.hijos = padre.hijos[mitad + 1:]
            padre.claves = padre.claves[:mitad]
            padre.hijos = padre.hijos[:mitad + 1]

        # Si llegamos aquí se dividió la raíz: el árbol crece un nivel.
        nueva_raiz = _NodoBPlus(es_hoja=False)
        nueva_raiz.claves = [separador]
        nueva_raiz.hijos = [self.raiz, nuevo_nodo]
        self.raiz = nueva_raiz

    def eliminar(self, clave):
        """Elimina la clave y devuelve su valor. Lanza KeyError si no existe."""
        hoja, camino = self._buscar_hoja(clave)
        posicion = bisect_left(hoja.claves, clave)
        if posicion == len(hoja.claves) or hoja.claves[posicion] != clave:
            raise KeyError(f"La clave {clave!r} no existe")

        hoja.claves.pop(posicion)
        valor = hoja.valores.pop(posicion)
        self._cantidad_claves -= 1
        self._rebalancear(hoja, camino)
        return valor

    def _rebalancear(self, nodo, camino):
        """Arregla nodos que quedaron con menos claves del mínimo."""
        while True:
            if not camino:  # nodo es la raíz
                if not nodo.es_hoja and len(nodo.hijos) == 1:
                    self.raiz = nodo.hijos[0]  # el árbol baja un nivel
                return

            if len(nodo.claves) >= self.min_claves:
                return  # el nodo sigue siendo válido

            padre, indice_hijo = camino.pop()
            hermano_izquierdo = padre.hijos[indice_hijo - 1] if indice_hijo > 0 else None
            hermano_derecho = padre.hijos[indice_hijo + 1] if indice_hijo + 1 < len(padre.hijos) else None

            # 1) Pedir prestado al hermano izquierdo
            if hermano_izquierdo is not None and len(hermano_izquierdo.claves) > self.min_claves:
                if nodo.es_hoja:
                    nodo.claves.insert(0, hermano_izquierdo.claves.pop())
                    nodo.valores.insert(0, hermano_izquierdo.valores.pop())
                    padre.claves[indice_hijo - 1] = nodo.claves[0]
                else:
                    nodo.claves.insert(0, padre.claves[indice_hijo - 1])
                    padre.claves[indice_hijo - 1] = hermano_izquierdo.claves.pop()
                    nodo.hijos.insert(0, hermano_izquierdo.hijos.pop())
                return

            # 2) Pedir prestado al hermano derecho
            if hermano_derecho is not None and len(hermano_derecho.claves) > self.min_claves:
                if nodo.es_hoja:
                    nodo.claves.append(hermano_derecho.claves.pop(0))
                    nodo.valores.append(hermano_derecho.valores.pop(0))
                    padre.claves[indice_hijo] = hermano_derecho.claves[0]
                else:
                    nodo.claves.append(padre.claves[indice_hijo])
                    padre.claves[indice_hijo] = hermano_derecho.claves.pop(0)
                    nodo.hijos.append(hermano_derecho.hijos.pop(0))
                return

            # 3) Ningún hermano puede prestar: fusionar con uno de ellos
            if hermano_izquierdo is not None:
                self._fusionar(hermano_izquierdo, nodo, padre, indice_hijo - 1)
            else:
                self._fusionar(nodo, hermano_derecho, padre, indice_hijo)

            # El padre perdió una clave: puede que ahora él necesite arreglo
            nodo = padre

    @staticmethod
    def _fusionar(nodo_izquierdo, nodo_derecho, padre, indice_separador):
        """Une `nodo_derecho` dentro de `nodo_izquierdo`.
        indice_separador es la posición, en el padre, de la clave que separa a ambos."""
        if nodo_izquierdo.es_hoja:
            nodo_izquierdo.claves.extend(nodo_derecho.claves)
            nodo_izquierdo.valores.extend(nodo_derecho.valores)
            nodo_izquierdo.siguiente = nodo_derecho.siguiente
        else:
            # En nodos internos el separador del padre baja al nodo fusionado
            nodo_izquierdo.claves.append(padre.claves[indice_separador])
            nodo_izquierdo.claves.extend(nodo_derecho.claves)
            nodo_izquierdo.hijos.extend(nodo_derecho.hijos)
        padre.claves.pop(indice_separador)
        padre.hijos.pop(indice_separador + 1)

    def _hoja_mas_izquierda(self):
        nodo = self.raiz
        while not nodo.es_hoja:
            nodo = nodo.hijos[0]
        return nodo

    def recorrer_en_orden(self):
        """Genera todos los pares (clave, valor) en orden ascendente,
        usando la lista enlazada de hojas."""
        hoja = self._hoja_mas_izquierda()
        while hoja is not None:
            yield from zip(hoja.claves, hoja.valores)
            hoja = hoja.siguiente

    def buscar_rango(self, clave_desde, clave_hasta):
        """Genera los pares (clave, valor) con clave_desde <= clave <= clave_hasta."""
        hoja, _ = self._buscar_hoja(clave_desde)
        posicion = bisect_left(hoja.claves, clave_desde)
        while hoja is not None:
            while posicion < len(hoja.claves):
                if hoja.claves[posicion] > clave_hasta:
                    return
                yield hoja.claves[posicion], hoja.valores[posicion]
                posicion += 1
            hoja, posicion = hoja.siguiente, 0

    def clave_maxima(self):
        """Devuelve la clave más grande del árbol, o None si está vacío."""
        nodo = self.raiz
        while not nodo.es_hoja:
            nodo = nodo.hijos[-1]
        return nodo.claves[-1] if nodo.claves else None

    def calcular_altura(self):
        altura, nodo = 1, self.raiz
        while not nodo.es_hoja:
            nodo = nodo.hijos[0]
            altura += 1
        return altura

    def imprimir_por_niveles(self):
        """Muestra el árbol nivel por nivel (útil con pocos datos)."""
        nodos_del_nivel = [self.raiz]
        numero_nivel = 0
        while nodos_del_nivel:
            print(f"Nivel {numero_nivel}: " + "  ".join(str(nodo.claves) for nodo in nodos_del_nivel))
            if nodos_del_nivel[0].es_hoja:
                break
            nodos_del_nivel = [hijo for nodo in nodos_del_nivel for hijo in nodo.hijos]
            numero_nivel += 1
