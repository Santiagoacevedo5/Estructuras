"""
Sistema de estudiantes usando un árbol B+.

Toma la lista `estudiantes` generada en lista.py y la guarda en un árbol B+
cuya clave es el ID (matrícula) y cuyo valor es el diccionario del estudiante.
"""
import random
import time

import ABB
from arbolbplus import ArbolBPlus
from lista import generar_estudiantes

ORDEN_ARBOL_BPLUS = 32  # máximo de hijos por nodo (en bases de datos reales suele ser mucho mayor)


def construir_arbol_bplus(estudiantes, orden=ORDEN_ARBOL_BPLUS):
    arbol_bplus = ArbolBPlus(orden)
    for estudiante in estudiantes:
        arbol_bplus.insertar(estudiante["id"], estudiante)
    return arbol_bplus


def mostrar_estudiante(estudiante):
    print(f'ID: {estudiante["id"]} | Nombre: {estudiante["nombre"]} | Edad: {estudiante["edad"]} | Promedio: {estudiante["promedio"]}')


def pedir_entero(mensaje):
    while True:
        try:
            return int(input(mensaje))
        except ValueError:
            print("Debe ser un número entero.")


def pedir_promedio(mensaje):
    while True:
        try:
            promedio = float(input(mensaje))
            if 0 <= promedio <= 10:
                return promedio
            print("El promedio debe estar entre 0 y 10.")
        except ValueError:
            print("Debe ser un número (por ejemplo 7.5).")


def buscar_estudiante_en_arbol(arbol_bplus):
    id_buscado = pedir_entero("Ingrese el ID del estudiante a buscar: ")
    estudiante = arbol_bplus.buscar(id_buscado)
    if estudiante is None:
        print("Estudiante no encontrado")
    else:
        mostrar_estudiante(estudiante)


def insertar_estudiante_en_arbol(arbol_bplus, estudiantes):
    nuevo_id = (arbol_bplus.clave_maxima() or 0) + 1
    nombre = input("Ingrese nombre: ").strip()
    edad = pedir_entero("Ingrese edad: ")
    promedio = pedir_promedio("Ingrese promedio: ")
    estudiante = {"id": nuevo_id, "nombre": nombre, "edad": edad, "promedio": promedio}
    arbol_bplus.insertar(nuevo_id, estudiante)
    estudiantes.append(estudiante)  # la lista también se mantiene al día
    print(f"Estudiante insertado con ID {nuevo_id}")


def listar_estudiantes_del_arbol(arbol_bplus):
    for _, estudiante in arbol_bplus.recorrer_en_orden():  # ya salen ordenados por ID
        mostrar_estudiante(estudiante)


def medir_tiempo_busquedas(nombre_estructura, funcion_buscar, ids_a_buscar):
    inicio = time.perf_counter()
    for id_buscado in ids_a_buscar:
        funcion_buscar(id_buscado)
    print(f"{nombre_estructura:<30} {time.perf_counter() - inicio:.6f} s")


def buscar_en_lista(estudiantes, id_buscado):
    for estudiante in estudiantes:
        if estudiante["id"] == id_buscado:
            return estudiante


def comparar_tiempos(estudiantes):
    estudiantes_ordenados = sorted(estudiantes, key=lambda estudiante: estudiante["id"])
    estudiantes_revueltos = random.sample(estudiantes_ordenados, len(estudiantes_ordenados))
    ids_a_buscar = random.sample([estudiante["id"] for estudiante in estudiantes_ordenados], 100)

    for titulo, datos_de_prueba in (("DATOS EN ORDEN", estudiantes_ordenados),
                                    ("DATOS REVUELTOS", estudiantes_revueltos)):
        raiz_abb = ABB.construir_abb(datos_de_prueba)
        arbol_bplus = construir_arbol_bplus(datos_de_prueba)
        print(f"\n{titulo} (100 búsquedas)")
        medir_tiempo_busquedas("Lista", lambda id_buscado: buscar_en_lista(datos_de_prueba, id_buscado), ids_a_buscar)
        medir_tiempo_busquedas("ABB", lambda id_buscado: ABB.buscar_en_abb(raiz_abb, id_buscado), ids_a_buscar)
        medir_tiempo_busquedas("Árbol B+", arbol_bplus.buscar, ids_a_buscar)


def main():
    estudiantes = generar_estudiantes()
    arbol_bplus = construir_arbol_bplus(estudiantes)

    while True:
        print("\n--- MENU (Árbol B+) ---")
        print("1. Buscar estudiante")
        print("2. Insertar estudiante")
        print("3. Listar estudiantes")
        print("4. Comparar tiempos (lista, ABB y árbol B+)")
        print("5. Salir")

        opcion = input("Seleccione una opción: ").strip()

        if opcion == "1":
            buscar_estudiante_en_arbol(arbol_bplus)
        elif opcion == "2":
            insertar_estudiante_en_arbol(arbol_bplus, estudiantes)
        elif opcion == "3":
            listar_estudiantes_del_arbol(arbol_bplus)
        elif opcion == "4":
            comparar_tiempos(estudiantes)
        elif opcion == "5":
            print("Ha salido.")
            break
        else:
            print("Opción inválida")


if __name__ == "__main__":
    main()
