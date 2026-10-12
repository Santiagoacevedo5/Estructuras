"""
Experimento del Laboratorio 3.

Mide, para Lista, ABB y Árbol B+:
  - INSERTAR: tiempo de construir la estructura insertando los N estudiantes uno a uno.
  - BUSCAR:   tiempo de buscar estudiantes por ID (en lotes de M búsquedas).
  - LISTAR:   tiempo de obtener todos los estudiantes ordenados por ID.

Hay dos experimentos:
  A) Variar N (número de estudiantes), con M fijo, en datos ordenados y aleatorios.
  B) Variar M (número de búsquedas por lote), con N fijo, en datos aleatorios.

VENTANA MÍNIMA DE MEDICIÓN (guías de benchmarking)
  Una búsqueda dura menos de un microsegundo. Medir intervalos tan cortos es muy ruidoso:
  cualquier interrupción del sistema operativo pesa mucho. Por eso cada medición repite la
  operación las veces necesarias para que el tiempo medido sea de AL MENOS
  `VENTANA_MINIMA_S` segundos (1 s), y luego se divide por el número de repeticiones. Así
  se reporta el costo de UNA operación (que naturalmente está en nanosegundos o
  microsegundos), pero medido sobre una ventana de más de un segundo.

Uso:
    python experimento.py            # experimento completo (~1 hora)
    python experimento.py --rapido   # prueba corta (~1 minuto) para ver que todo funciona
"""
import argparse
import csv
import gc
import math
import os
import platform
import random
import sys
import time
from datetime import datetime

import ABB
from arbolbplus import ArbolBPlus
from lista import generar_estudiantes

# Carpeta donde están estos archivos .py (Arboles). Los resultados se guardan aquí,
# sin importar desde qué carpeta se ejecute el programa.
CARPETA_DEL_PROYECTO = os.path.dirname(os.path.abspath(__file__))

# ----------------------------------------------------------------------
# Parámetros del experimento
# ----------------------------------------------------------------------
CONFIGURACION_COMPLETA = {
    "VALORES_N": [100, 300, 1000, 3000, 10000, 30000, 100000],  # tamaños para el experimento A
    "BUSQUEDAS_POR_LOTE": 1000,                                  # M fijo del experimento A
    "VALORES_M": [100, 300, 1000, 3000, 10000],                  # valores de M para el experimento B
    "N_FIJO": 10000,                                             # N usado en el experimento B
    "REPETICIONES": 20,
    "VENTANA_MINIMA_S": 1.0,      # duración mínima de cada medición (segundos)
    "MAX_N_ABB_ORDENADO": 30000,  # por encima tarda demasiado en construirse (O(N^2))
    "CARPETA": os.path.join(CARPETA_DEL_PROYECTO, "resultados"),
}
CONFIGURACION_RAPIDA = {
    "VALORES_N": [100, 1000, 3000],
    "BUSQUEDAS_POR_LOTE": 1000,
    "VALORES_M": [100, 1000],
    "N_FIJO": 1000,
    "REPETICIONES": 3,
    "VENTANA_MINIMA_S": 0.05,
    "MAX_N_ABB_ORDENADO": 3000,
    "CARPETA": os.path.join(CARPETA_DEL_PROYECTO, "resultados_prueba"),
}
ORDEN_ARBOL_BPLUS = 32  # máximo de hijos por nodo del árbol B+


# ----------------------------------------------------------------------
# Las tres estructuras, con la misma "interfaz":
#   construir(estudiantes) -> estructura
#   buscar(estructura, id) -> estudiante o None
#   listar(estructura)     -> lista de estudiantes ordenada por ID
#   altura(estructura)     -> número de niveles (vacío para la lista)
# ----------------------------------------------------------------------
def construir_lista(estudiantes):
    lista_estudiantes = []
    for estudiante in estudiantes:
        lista_estudiantes.append(estudiante)
    return lista_estudiantes


def buscar_en_lista(lista_estudiantes, id_buscado):
    for estudiante in lista_estudiantes:
        if estudiante["id"] == id_buscado:
            return estudiante
    return None


def listar_lista_ordenada(lista_estudiantes):
    return sorted(lista_estudiantes, key=lambda estudiante: estudiante["id"])


def construir_arbol_bplus(estudiantes):
    arbol_bplus = ArbolBPlus(ORDEN_ARBOL_BPLUS)
    for estudiante in estudiantes:
        arbol_bplus.insertar(estudiante["id"], estudiante)
    return arbol_bplus


ESTRUCTURAS = {
    "Lista": {
        "construir": construir_lista,
        "buscar": buscar_en_lista,
        "listar": listar_lista_ordenada,
        "altura": lambda lista_estudiantes: "",
    },
    "ABB": {
        "construir": ABB.construir_abb,
        "buscar": ABB.buscar_en_abb,
        "listar": ABB.recorrer_abb_inorden,
        "altura": ABB.calcular_altura_abb,
    },
    "B+": {
        "construir": construir_arbol_bplus,
        "buscar": lambda arbol_bplus, id_buscado: arbol_bplus.buscar(id_buscado),
        "listar": lambda arbol_bplus: [estudiante for _, estudiante in arbol_bplus.recorrer_en_orden()],
        "altura": lambda arbol_bplus: arbol_bplus.calcular_altura(),
    },
}

COLUMNAS_CSV = ["experimento", "estructura", "orden", "N", "M", "repeticion",
                # tiempo de UNA construcción, de UN lote de M búsquedas y de UN listado (segundos)
                "t_construccion_s", "t_busqueda_s", "t_listar_s",
                # cuántas veces se repitió cada operación dentro de su ventana
                "veces_construccion", "lotes_busqueda", "veces_listar",
                # duración total medida de cada ventana (segundos): debe ser >= minimo_s
                "ventana_construccion_s", "ventana_busqueda_s", "ventana_listar_s",
                "minimo_s", "altura", "momento_min"]

# Momento en que arrancó el experimento: cada medición guarda cuántos minutos
# habían pasado, para revisar después si el computador cambió de velocidad.
INICIO_DEL_EXPERIMENTO = time.perf_counter()


def minutos_transcurridos():
    return (time.perf_counter() - INICIO_DEL_EXPERIMENTO) / 60


# ----------------------------------------------------------------------
# Medición
# ----------------------------------------------------------------------
def cronometrar(funcion):
    """Ejecuta funcion() y devuelve (resultado, segundos).
    El recolector de basura se apaga mientras se mide para que no meta pausas."""
    gc.collect()
    gc.disable()
    try:
        inicio = time.perf_counter()
        resultado = funcion()
        segundos = time.perf_counter() - inicio
    finally:
        gc.enable()
    return resultado, segundos


def medir_con_ventana_minima(funcion, ventana_minima_s):
    """Repite funcion() hasta acumular al menos ventana_minima_s segundos medidos.

    La primera ejecución sirve de calibración: si ya dura ventana_minima_s o más (por
    ejemplo, construir el ABB degenerado con N grande) se usa tal cual. Si no, se descarta
    (sirve de calentamiento), se calcula cuántas veces hay que repetir para llenar la
    ventana y se mide ese bloque de repeticiones.

    Devuelve (resultado de la primera ejecución, segundos por ejecución, veces, ventana total)."""
    resultado, tiempo_calibracion = cronometrar(funcion)
    if tiempo_calibracion >= ventana_minima_s:
        return resultado, tiempo_calibracion, 1, tiempo_calibracion

    tiempo_total, ejecuciones_totales = 0.0, 0
    tiempo_estimado = max(tiempo_calibracion, 1e-7)
    while tiempo_total < ventana_minima_s:
        ejecuciones_del_bloque = max(1, math.ceil((ventana_minima_s - tiempo_total) / tiempo_estimado * 1.05))

        def ejecutar_bloque():
            for _ in range(ejecuciones_del_bloque):
                funcion()

        _, tiempo_bloque = cronometrar(ejecutar_bloque)
        tiempo_total += tiempo_bloque
        ejecuciones_totales += ejecuciones_del_bloque
        tiempo_estimado = tiempo_total / ejecuciones_totales
    return resultado, tiempo_total / ejecuciones_totales, ejecuciones_totales, tiempo_total


def medir_busquedas(funcion_buscar, estructura, cantidad_estudiantes, busquedas_por_lote,
                    semilla, ventana_minima_s):
    """Busca lotes de M IDs, con IDs NUEVOS en cada lote, hasta acumular ventana_minima_s segundos.

    Usar IDs nuevos en cada lote evita repetir siempre los mismos caminos del árbol: si se
    repitieran, esos nodos quedarían en la memoria caché del procesador y la medición
    saldría más rápida de lo real. Los IDs se generan ANTES de cronometrar.
    Con la misma semilla, las tres estructuras buscan exactamente la misma secuencia de IDs.

    Devuelve (segundos por lote de M búsquedas, número de lotes, ventana total)."""
    generador_aleatorio = random.Random(semilla)
    ids_posibles = range(1, cantidad_estudiantes + 1)

    def generar_lotes(cantidad_lotes):
        # con reemplazo: M puede ser mayor que N
        return [generador_aleatorio.choices(ids_posibles, k=busquedas_por_lote)
                for _ in range(cantidad_lotes)]

    def buscar_lotes(lotes):
        encontrados = 0
        for ids_del_lote in lotes:
            for id_buscado in ids_del_lote:
                if funcion_buscar(estructura, id_buscado) is not None:
                    encontrados += 1
        return encontrados

    def comprobar(encontrados, esperados):
        if encontrados != esperados:  # todos los IDs buscados existen: deben encontrarse
            raise RuntimeError(f"Búsqueda incorrecta: {encontrados} de {esperados}")

    # Calibración con un lote
    lotes = generar_lotes(1)
    encontrados, tiempo_calibracion = cronometrar(lambda: buscar_lotes(lotes))
    comprobar(encontrados, busquedas_por_lote)
    if tiempo_calibracion >= ventana_minima_s:
        return tiempo_calibracion, 1, tiempo_calibracion

    tiempo_total, lotes_medidos = 0.0, 0
    tiempo_estimado = max(tiempo_calibracion, 1e-7)
    max_lotes_por_bloque = max(1, 200_000 // busquedas_por_lote)  # no generar millones de IDs de una vez
    while tiempo_total < ventana_minima_s:
        lotes_del_bloque = max(1, math.ceil((ventana_minima_s - tiempo_total) / tiempo_estimado * 1.05))
        lotes_del_bloque = min(lotes_del_bloque, max_lotes_por_bloque)
        lotes = generar_lotes(lotes_del_bloque)
        encontrados, tiempo_bloque = cronometrar(lambda: buscar_lotes(lotes))
        comprobar(encontrados, lotes_del_bloque * busquedas_por_lote)
        tiempo_total += tiempo_bloque
        lotes_medidos += lotes_del_bloque
        tiempo_estimado = tiempo_total / lotes_medidos
    return tiempo_total / lotes_medidos, lotes_medidos, tiempo_total


def medir_estructura(nombre_estructura, estudiantes, busquedas_por_lote, semilla_busquedas,
                     ventana_minima_s, medir_todo=True):
    """Mide construir, buscar y listar una estructura. Devuelve una fila para el CSV."""
    operaciones = ESTRUCTURAS[nombre_estructura]
    cantidad_estudiantes = len(estudiantes)
    fila = {"minimo_s": ventana_minima_s}

    if medir_todo:
        estructura, tiempo_construccion, veces_construccion, ventana_construccion = medir_con_ventana_minima(
            lambda: operaciones["construir"](estudiantes), ventana_minima_s)
        fila.update(t_construccion_s=tiempo_construccion, veces_construccion=veces_construccion,
                    ventana_construccion_s=ventana_construccion)
    else:
        estructura = operaciones["construir"](estudiantes)

    tiempo_busqueda, lotes_busqueda, ventana_busqueda = medir_busquedas(
        operaciones["buscar"], estructura, cantidad_estudiantes, busquedas_por_lote,
        semilla_busquedas, ventana_minima_s)
    fila.update(t_busqueda_s=tiempo_busqueda, lotes_busqueda=lotes_busqueda,
                ventana_busqueda_s=ventana_busqueda)

    if medir_todo:
        listado, tiempo_listar, veces_listar, ventana_listar = medir_con_ventana_minima(
            lambda: operaciones["listar"](estructura), ventana_minima_s)
        if [estudiante["id"] for estudiante in listado] != list(range(1, cantidad_estudiantes + 1)):
            raise RuntimeError(f"{nombre_estructura}: el listado no salió en orden")
        fila.update(t_listar_s=tiempo_listar, veces_listar=veces_listar, ventana_listar_s=ventana_listar)

    fila["altura"] = operaciones["altura"](estructura)
    return fila


def mezclar_orden_de_estructuras(nombres_estructuras, semilla):
    """Se cambia el orden en que se miden las estructuras en cada repetición, para que
    ninguna quede siempre de primera (o de última) y eso no sesgue los tiempos."""
    nombres_estructuras = list(nombres_estructuras)
    random.Random(semilla).shuffle(nombres_estructuras)
    return nombres_estructuras


# ----------------------------------------------------------------------
# Experimentos
# ----------------------------------------------------------------------
def guardar_entorno(configuracion, carpeta):
    try:
        ram_gb = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024 ** 3
        ram = f"{ram_gb:.1f} GB"
    except (ValueError, AttributeError, OSError):
        ram = "no disponible (anótala a mano)"
    reloj = time.get_clock_info("perf_counter")
    with open(os.path.join(carpeta, "entorno.txt"), "w", encoding="utf-8") as archivo_entorno:
        archivo_entorno.write(f"Fecha: {datetime.now():%Y-%m-%d %H:%M}\n")
        archivo_entorno.write(f"Sistema operativo: {platform.platform()}\n")
        archivo_entorno.write(f"Procesador: {platform.processor() or platform.machine()}\n")
        archivo_entorno.write(f"Núcleos lógicos: {os.cpu_count()}\n")
        archivo_entorno.write(f"RAM: {ram}\n")
        archivo_entorno.write(f"Python: {sys.version.split()[0]} ({platform.python_implementation()})\n")
        archivo_entorno.write(f"Reloj: time.perf_counter ({reloj.implementation}), resolución {reloj.resolution:.1e} s\n")
        archivo_entorno.write(f"Orden del árbol B+: {ORDEN_ARBOL_BPLUS}\n")
        for parametro, valor in configuracion.items():
            archivo_entorno.write(f"{parametro}: {valor}\n")


def calentamiento():
    """Una ronda corta que NO se guarda. Las primeras ejecuciones de un programa suelen
    ser más lentas (Python carga cosas en memoria por primera vez)."""
    estudiantes = generar_estudiantes(2000, "aleatorio", semilla=999)
    for nombre_estructura in ESTRUCTURAS:
        medir_estructura(nombre_estructura, estudiantes, 500, 999, ventana_minima_s=0.05)


def experimento_variar_n(configuracion, escritor_csv, archivo_csv):
    """A) Varía N. M fijo. Datos ordenados y aleatorios.

    IMPORTANTE: en cada repetición las configuraciones (N, orden) se recorren en un
    ORDEN ALEATORIO. Si se midieran en orden (primero todos los N=100, luego N=300...),
    cualquier cambio de velocidad del computador durante el experimento quedaría
    mezclado con el efecto de N. Mezclándolas, ese cambio afecta a todos los N por igual."""
    combinaciones = [(cantidad_estudiantes, orden)
                     for cantidad_estudiantes in configuracion["VALORES_N"]
                     for orden in ("ordenado", "aleatorio")]
    total_combinaciones = len(combinaciones) * configuracion["REPETICIONES"]
    combinaciones_hechas = 0
    for repeticion in range(1, configuracion["REPETICIONES"] + 1):
        combinaciones_mezcladas = combinaciones[:]
        random.Random(5_000_000 + repeticion).shuffle(combinaciones_mezcladas)
        for cantidad_estudiantes, orden in combinaciones_mezcladas:
            estudiantes = generar_estudiantes(cantidad_estudiantes, orden, semilla=repeticion)
            for nombre_estructura in mezclar_orden_de_estructuras(
                    ESTRUCTURAS, semilla=repeticion * 31 + cantidad_estudiantes):
                if (nombre_estructura == "ABB" and orden == "ordenado"
                        and cantidad_estudiantes > configuracion["MAX_N_ABB_ORDENADO"]):
                    continue
                fila = medir_estructura(nombre_estructura, estudiantes, configuracion["BUSQUEDAS_POR_LOTE"],
                                        1_000_000 + repeticion, configuracion["VENTANA_MINIMA_S"])
                fila.update(experimento="A_variar_N", estructura=nombre_estructura, orden=orden,
                            N=cantidad_estudiantes, M=configuracion["BUSQUEDAS_POR_LOTE"],
                            repeticion=repeticion, momento_min=minutos_transcurridos())
                escritor_csv.writerow(fila)
            archivo_csv.flush()

            combinaciones_hechas += 1
            print(f"\r[A] repetición {repeticion:>2}/{configuracion['REPETICIONES']}"
                  f"  N={cantidad_estudiantes:>6} {orden:<9}"
                  f"  ({combinaciones_hechas}/{total_combinaciones}, {minutos_transcurridos():.1f} min)",
                  end="", flush=True)
    print()


def experimento_variar_m(configuracion, escritor_csv, archivo_csv):
    """B) Varía M. N fijo. Datos aleatorios. Solo se mide buscar (construir y listar no
    dependen de M). Los valores de M se recorren en orden aleatorio en cada repetición."""
    cantidad_estudiantes = configuracion["N_FIJO"]
    for repeticion in range(1, configuracion["REPETICIONES"] + 1):
        estudiantes = generar_estudiantes(cantidad_estudiantes, "aleatorio", semilla=repeticion)
        valores_m = list(configuracion["VALORES_M"])
        random.Random(6_000_000 + repeticion).shuffle(valores_m)
        for busquedas_por_lote in valores_m:
            for nombre_estructura in mezclar_orden_de_estructuras(
                    ESTRUCTURAS, semilla=repeticion * 7 + busquedas_por_lote):
                fila = medir_estructura(nombre_estructura, estudiantes, busquedas_por_lote,
                                        2_000_000 + repeticion, configuracion["VENTANA_MINIMA_S"],
                                        medir_todo=False)
                fila.update(experimento="B_variar_M", estructura=nombre_estructura, orden="aleatorio",
                            N=cantidad_estudiantes, M=busquedas_por_lote, repeticion=repeticion,
                            momento_min=minutos_transcurridos())
                escritor_csv.writerow(fila)
        archivo_csv.flush()
        print(f"\r[B] N={cantidad_estudiantes} repetición {repeticion:>2}/{configuracion['REPETICIONES']}"
              f"  ({minutos_transcurridos():.1f} min)", end="", flush=True)
    print()


def main():
    parser = argparse.ArgumentParser(description="Experimento Lista vs ABB vs B+")
    parser.add_argument("--rapido", action="store_true", help="prueba corta para verificar que todo funciona")
    argumentos = parser.parse_args()
    configuracion = CONFIGURACION_RAPIDA if argumentos.rapido else CONFIGURACION_COMPLETA

    carpeta = configuracion["CARPETA"]
    os.makedirs(carpeta, exist_ok=True)
    guardar_entorno(configuracion, carpeta)

    print("Calentamiento...")
    calentamiento()

    ruta_mediciones = os.path.join(carpeta, "mediciones.csv")
    with open(ruta_mediciones, "w", newline="", encoding="utf-8") as archivo_csv:
        escritor_csv = csv.DictWriter(archivo_csv, fieldnames=COLUMNAS_CSV)
        escritor_csv.writeheader()
        experimento_variar_n(configuracion, escritor_csv, archivo_csv)
        experimento_variar_m(configuracion, escritor_csv, archivo_csv)

    print(f"Listo en {minutos_transcurridos():.1f} min. Mediciones en {ruta_mediciones}")
    print(f"Siguiente paso: python analisis.py{' --rapido' if argumentos.rapido else ''}")


if __name__ == "__main__":
    main()
