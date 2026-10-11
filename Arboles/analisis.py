"""
Análisis estadístico de las mediciones del experimento.

Lee resultados/mediciones.csv y produce:
  - resultados/estadisticas_A.csv : estadísticas por (operación, estructura, orden, N)
  - resultados/estadisticas_B.csv : estadísticas por (estructura, M)
  - resultados/pendientes.csv     : pendientes log-log (comparación con la teoría)
  - resultados/resumen.md         : todo lo anterior en tablas legibles

Uso:
    python analisis.py            # analiza resultados/
    python analisis.py --rapido   # analiza resultados_prueba/
"""
import argparse
import os

import numpy as np
import pandas as pd
from scipy import stats

# Cada operación: (columna de tiempo en el CSV, cómo convertirla, unidad)
OPERACIONES = {
    "busqueda": ("t_busqueda_s", lambda mediciones: mediciones["t_busqueda_s"] / mediciones["M"] * 1e6,
                 "µs por búsqueda"),
    "insercion": ("t_construccion_s", lambda mediciones: mediciones["t_construccion_s"] / mediciones["N"] * 1e6,
                  "µs por inserción"),
    "listar": ("t_listar_s", lambda mediciones: mediciones["t_listar_s"] * 1e3, "ms por listado completo"),
}
NIVEL_CONFIANZA = 0.95

# Carpeta donde están estos archivos .py (Arboles): los resultados se leen y guardan aquí.
CARPETA_DEL_PROYECTO = os.path.dirname(os.path.abspath(__file__))


# ----------------------------------------------------------------------
# Estadísticas de un grupo de repeticiones
# ----------------------------------------------------------------------
def detectar_atipicos_iqr(valores):
    """Regla del rango intercuartílico (IQR):
    Q1 = percentil 25, Q3 = percentil 75, IQR = Q3 - Q1.
    Es atípico lo que esté por debajo de Q1 - 1.5*IQR o por encima de Q3 + 1.5*IQR."""
    cuartil_1, cuartil_3 = np.percentile(valores, [25, 75])
    rango_intercuartil = cuartil_3 - cuartil_1
    return ((valores < cuartil_1 - 1.5 * rango_intercuartil) |
            (valores > cuartil_3 + 1.5 * rango_intercuartil))


def resumir_repeticiones(valores):
    valores = np.asarray(valores, dtype=float)
    cantidad = len(valores)
    media = valores.mean()
    desviacion = valores.std(ddof=1) if cantidad > 1 else 0.0          # desviación estándar muestral
    error_estandar = desviacion / np.sqrt(cantidad) if cantidad > 1 else 0.0
    t_critico = stats.t.ppf((1 + NIVEL_CONFIANZA) / 2, cantidad - 1) if cantidad > 1 else 0.0
    margen_de_error = t_critico * error_estandar
    es_atipico = detectar_atipicos_iqr(valores) if cantidad >= 4 else np.zeros(cantidad, bool)
    valores_sin_atipicos = valores[~es_atipico]
    return {
        "repeticiones": cantidad,
        "media": media,
        "desv_estandar": desviacion,
        "cv_%": 100 * desviacion / media if media else np.nan,
        "ic95_inf": media - margen_de_error,
        "ic95_sup": media + margen_de_error,
        "mediana": np.median(valores),
        "minimo": valores.min(),
        "maximo": valores.max(),
        "atipicos": int(es_atipico.sum()),
        "media_sin_atipicos": valores_sin_atipicos.mean(),
    }


def nombre_curva(estructura, orden):
    return f"{estructura} ({orden})"


# ----------------------------------------------------------------------
# Experimento A: variar N
# ----------------------------------------------------------------------
def calcular_estadisticas_variar_n(mediciones):
    filas = []
    for operacion, (columna, convertir, unidad) in OPERACIONES.items():
        mediciones_operacion = mediciones.dropna(subset=[columna]).copy()
        mediciones_operacion["valor"] = convertir(mediciones_operacion)
        for (estructura, orden, cantidad_estudiantes), grupo in mediciones_operacion.groupby(
                ["estructura", "orden", "N"]):
            fila = {"operacion": operacion, "unidad": unidad,
                    "estructura": estructura, "orden": orden, "N": cantidad_estudiantes,
                    "curva": nombre_curva(estructura, orden)}
            fila.update(resumir_repeticiones(grupo["valor"]))
            fila["altura_media"] = pd.to_numeric(grupo["altura"], errors="coerce").mean()
            filas.append(fila)
    return pd.DataFrame(filas)


def calcular_pendientes(estadisticas_n):
    """Regresión lineal de log10(tiempo medio) contra log10(N).
    Si tiempo ≈ c·N^k, entonces log(tiempo) = log(c) + k·log(N): la pendiente es k.
      k ≈ 1   -> crece como N       (O(N))
      k ≈ 0   -> casi no crece      (O(1) u O(log N))
      k ≈ 1.x -> crece algo más rápido que N (por ejemplo O(N log N))"""
    filas = []
    for (operacion, curva), grupo in estadisticas_n.groupby(["operacion", "curva"]):
        if len(grupo) < 3:
            continue
        regresion = stats.linregress(np.log10(grupo["N"]), np.log10(grupo["media"]))
        fila = {"operacion": operacion, "curva": curva,
                "pendiente": regresion.slope, "error_pendiente": regresion.stderr,
                "r2": regresion.rvalue ** 2, "N_min": grupo["N"].min(), "N_max": grupo["N"].max(),
                "pendiente_altura": np.nan}
        # En los árboles, una búsqueda cuesta ~ (costo por nivel) x (altura). Si el costo por
        # nivel fuera constante, la pendiente del tiempo sería igual a la de la altura.
        if operacion == "busqueda" and grupo["altura_media"].notna().all():
            fila["pendiente_altura"] = stats.linregress(np.log10(grupo["N"]),
                                                        np.log10(grupo["altura_media"])).slope
        filas.append(fila)
    return pd.DataFrame(filas)


def calcular_costo_por_nivel(estadisticas_n):
    """Tiempo de búsqueda dividido por la altura: cuánto cuesta bajar UN nivel."""
    busquedas_en_arboles = estadisticas_n[(estadisticas_n.operacion == "busqueda") &
                                          estadisticas_n.altura_media.notna()].copy()
    busquedas_en_arboles["ns_por_nivel"] = (busquedas_en_arboles["media"] * 1000 /
                                            busquedas_en_arboles["altura_media"])
    return busquedas_en_arboles[["curva", "N", "altura_media", "media", "ns_por_nivel"]]


def correlacion_altura_tiempo(mediciones):
    """Correlación de Pearson entre la altura del árbol y el tiempo por búsqueda,
    usando todas las repeticiones (cada fila es una medición)."""
    mediciones_arboles = mediciones[(mediciones.experimento == "A_variar_N") &
                                    (mediciones.estructura != "Lista")].copy()
    mediciones_arboles["altura"] = pd.to_numeric(mediciones_arboles["altura"])
    mediciones_arboles["us_por_busqueda"] = mediciones_arboles["t_busqueda_s"] / mediciones_arboles["M"] * 1e6
    filas = []
    for estructura, grupo in mediciones_arboles.groupby("estructura"):
        coeficiente_r, p_valor = stats.pearsonr(grupo["altura"], grupo["us_por_busqueda"])
        filas.append({"estructura": estructura, "r_pearson": coeficiente_r, "p_valor": p_valor,
                      "mediciones": len(grupo)})
    return pd.DataFrame(filas)


def comparar_arboles_con_lista(estadisticas_n):
    """Para cada orden: menor N desde el cual cada árbol es más rápido que la lista
    con diferencia estadísticamente clara (los intervalos de confianza no se tocan)."""
    busquedas = estadisticas_n[estadisticas_n.operacion == "busqueda"]
    filas = []
    for orden in ("aleatorio", "ordenado"):
        tiempos_lista = busquedas[(busquedas.estructura == "Lista") & (busquedas.orden == orden)].set_index("N")
        for arbol in ("ABB", "B+"):
            tiempos_arbol = busquedas[(busquedas.estructura == arbol) & (busquedas.orden == orden)].set_index("N")
            valores_n_comunes = sorted(set(tiempos_lista.index) & set(tiempos_arbol.index))
            n_arbol_mas_rapido = [n for n in valores_n_comunes
                                  if tiempos_arbol.loc[n, "ic95_sup"] < tiempos_lista.loc[n, "ic95_inf"]]
            n_arbol_mas_lento = [n for n in valores_n_comunes
                                 if tiempos_arbol.loc[n, "ic95_inf"] > tiempos_lista.loc[n, "ic95_sup"]]
            n_maximo = valores_n_comunes[-1]
            filas.append({
                "orden": orden, "arbol": arbol,
                "N_donde_arbol_es_mas_rapido": ", ".join(map(str, n_arbol_mas_rapido)) or "ninguno",
                "N_donde_arbol_es_mas_lento": ", ".join(map(str, n_arbol_mas_lento)) or "ninguno",
                "veces_mas_rapido_en_N_max": tiempos_lista.loc[n_maximo, "media"] / tiempos_arbol.loc[n_maximo, "media"],
                "N_max_comparado": n_maximo,
            })
    return pd.DataFrame(filas)


def tiempos_normalizados(mediciones):
    """Divide cada tiempo de búsqueda por la mediana de su grupo (estructura, orden, N).
    Un valor de 1 significa "igual a lo típico de su grupo"; 2 significa "el doble de lento".
    Así se pueden comparar en una sola escala mediciones de estructuras y N muy distintos."""
    mediciones_a = mediciones[mediciones.experimento == "A_variar_N"].copy()
    mediciones_a["us"] = mediciones_a["t_busqueda_s"] / mediciones_a["M"] * 1e6
    mediciones_a["relativo"] = mediciones_a["us"] / mediciones_a.groupby(
        ["estructura", "orden", "N"])["us"].transform("median")
    return mediciones_a


def analizar_estabilidad(mediciones):
    """¿Cambió la velocidad del computador durante el experimento?
    Se divide la duración del experimento en 4 cuartos y se mira la mediana del tiempo
    relativo en cada cuarto. Si el computador fue estable, todas deberían ser ≈ 1.
    Además, correlación de Spearman entre el momento de la medición y el tiempo relativo
    (cerca de 0 = no hay tendencia en el tiempo)."""
    if "momento_min" not in mediciones.columns:
        return None, None
    normalizadas = tiempos_normalizados(mediciones)
    normalizadas["cuarto"] = pd.cut(normalizadas["momento_min"], 4,
                                    labels=["1.º cuarto", "2.º cuarto", "3.º cuarto", "4.º cuarto"])
    tabla_por_cuarto = normalizadas.groupby("cuarto", observed=True).agg(
        desde_min=("momento_min", "min"), hasta_min=("momento_min", "max"),
        mediciones=("relativo", "size"), mediana_relativa=("relativo", "median")).reset_index()
    rho, p_valor = stats.spearmanr(normalizadas["momento_min"], normalizadas["relativo"])
    return tabla_por_cuarto, {"rho": rho, "p": p_valor}


def resumir_duracion_ventanas(mediciones):
    """Cuánto duró cada ventana de medición (guía de benchmarking: al menos 1 segundo)."""
    if "ventana_busqueda_s" not in mediciones.columns:
        return None
    filas = []
    casos = [("A_variar_N", "Construir (insertar N)", "ventana_construccion_s"),
             ("A_variar_N", "Buscar", "ventana_busqueda_s"),
             ("A_variar_N", "Listar", "ventana_listar_s"),
             ("B_variar_M", "Buscar (exp. B)", "ventana_busqueda_s")]
    for experimento, operacion, columna in casos:
        mediciones_caso = mediciones[mediciones.experimento == experimento].dropna(subset=[columna])
        if mediciones_caso.empty:
            continue
        duraciones = mediciones_caso[columna]
        filas.append({"operacion": operacion, "mediciones": len(duraciones),
                      "minimo_exigido_s": mediciones_caso["minimo_s"].iloc[0],
                      "ventana_min_s": duraciones.min(), "ventana_mediana_s": duraciones.median(),
                      "ventana_max_s": duraciones.max(),
                      "cumplen_%": 100 * (duraciones >= mediciones_caso["minimo_s"] * 0.999).mean()})
    return pd.DataFrame(filas)


# ----------------------------------------------------------------------
# Experimento B: variar M
# ----------------------------------------------------------------------
def calcular_estadisticas_variar_m(mediciones):
    mediciones_b = mediciones[mediciones.experimento == "B_variar_M"].copy()
    mediciones_b["valor"] = mediciones_b["t_busqueda_s"] * 1e3  # ms por lote de M búsquedas
    filas = []
    for (estructura, busquedas_por_lote), grupo in mediciones_b.groupby(["estructura", "M"]):
        fila = {"estructura": estructura, "N": grupo["N"].iloc[0], "M": busquedas_por_lote,
                "unidad": "ms por lote de M búsquedas"}
        fila.update(resumir_repeticiones(grupo["valor"]))
        filas.append(fila)
    estadisticas_m = pd.DataFrame(filas)
    filas_pendientes = []
    for estructura, grupo in estadisticas_m.groupby("estructura"):
        regresion = stats.linregress(np.log10(grupo["M"]), np.log10(grupo["media"]))
        filas_pendientes.append({"estructura": estructura, "pendiente_vs_M": regresion.slope,
                                 "r2": regresion.rvalue ** 2})
    return estadisticas_m, pd.DataFrame(filas_pendientes)


# ----------------------------------------------------------------------
# Reporte en Markdown
# ----------------------------------------------------------------------
def formatear_numero(valor, decimales=3):
    if isinstance(valor, (int, np.integer)):
        return str(valor)
    if pd.isna(valor):
        return "-"
    if abs(valor) >= 1000:
        return f"{valor:,.0f}"
    return f"{valor:.{decimales}f}"


def tabla_markdown(tabla, columnas, encabezados=None):
    encabezados = encabezados or columnas
    lineas = ["| " + " | ".join(encabezados) + " |", "|" + "---|" * len(columnas)]
    for _, fila in tabla.iterrows():
        lineas.append("| " + " | ".join(formatear_numero(fila[columna]) if not isinstance(fila[columna], str)
                                         else fila[columna] for columna in columnas) + " |")
    return "\n".join(lineas)


def escribir_resumen(carpeta, mediciones, estadisticas_n, pendientes_n, costo_por_nivel,
                     correlacion, comparacion_con_lista, estadisticas_m, pendientes_m,
                     tabla_estabilidad=None, spearman=None, ventanas=None):
    with open(os.path.join(carpeta, "entorno.txt"), encoding="utf-8") as archivo_entorno:
        entorno = archivo_entorno.read()

    partes = ["# Resumen de resultados\n",
              "Generado automáticamente por `analisis.py` a partir de `mediciones.csv`.\n",
              "## Entorno de la medición\n", "```\n" + entorno + "```\n",
              f"Total de mediciones: {len(mediciones)} filas.\n"]

    partes.append("## Duración de las ventanas de medición\n")
    if ventanas is None:
        partes.append("No disponible: estas mediciones no registran la duración de las ventanas.\n")
    else:
        partes.append("Cada medición repite la operación hasta acumular al menos el mínimo exigido; "
                      "las tablas siguientes reportan el tiempo de UNA operación (total / repeticiones).\n")
        partes.append(tabla_markdown(ventanas, ["operacion", "mediciones", "minimo_exigido_s", "ventana_min_s",
                                                "ventana_mediana_s", "ventana_max_s", "cumplen_%"],
                                     ["Operación", "Mediciones", "Mínimo exigido (s)", "Ventana mínima (s)",
                                      "Ventana mediana (s)", "Ventana máxima (s)", "% que cumple"]) + "\n")

    partes.append("## Estabilidad del computador durante el experimento\n")
    if tabla_estabilidad is None:
        partes.append("No disponible: el archivo de mediciones no tiene la columna `momento_min`.\n")
    else:
        partes.append("Tiempo de búsqueda de cada medición dividido por la mediana de su grupo "
                      "(estructura, orden, N). Si el computador mantuvo la misma velocidad, la mediana "
                      "de cada cuarto del experimento debe ser cercana a 1.\n")
        partes.append(tabla_markdown(tabla_estabilidad,
                                     ["cuarto", "desde_min", "hasta_min", "mediciones", "mediana_relativa"],
                                     ["Parte del experimento", "Desde (min)", "Hasta (min)", "Mediciones",
                                      "Mediana del tiempo relativo"]) + "\n")
        partes.append(f"Correlación de Spearman entre el momento de la medición y el tiempo relativo: "
                      f"ρ = {spearman['rho']:.3f} (p-valor = {spearman['p']:.3g}). "
                      "Cerca de 0 = sin tendencia en el tiempo.\n")

    columnas = ["curva", "N", "repeticiones", "media", "desv_estandar", "cv_%",
                "ic95_inf", "ic95_sup", "mediana", "atipicos", "media_sin_atipicos"]
    encabezados = ["Estructura", "N", "Rep.", "Media", "Desv. est.", "CV %",
                   "IC95 inf", "IC95 sup", "Mediana", "Atípicos", "Media sin atípicos"]
    for operacion, (_, _, unidad) in OPERACIONES.items():
        tabla_operacion = estadisticas_n[estadisticas_n.operacion == operacion].sort_values(["curva", "N"])
        partes.append(f"## Experimento A — {operacion} ({unidad})\n")
        partes.append(tabla_markdown(tabla_operacion, columnas, encabezados) + "\n")

    partes.append("## Comparación con la teoría: pendientes log-log\n")
    partes.append("Pendiente k de la recta log10(tiempo) vs log10(N). "
                  "k≈1 indica O(N); k≈0 indica crecimiento muy lento (O(log N) u O(1)).\n")
    partes.append(tabla_markdown(pendientes_n.sort_values(["operacion", "curva"]),
                                 ["operacion", "curva", "pendiente", "error_pendiente", "r2", "N_min", "N_max",
                                  "pendiente_altura"],
                                 ["Operación", "Estructura", "Pendiente k", "Error de k", "R²", "N mín", "N máx",
                                  "Pendiente de la altura"]) + "\n")
    partes.append("La última columna (solo árboles, búsqueda) es la pendiente log-log de la altura media. "
                  "Si cada nivel costara siempre lo mismo, la pendiente del tiempo sería igual a esa. "
                  "Si es mayor, cada nivel se vuelve más caro al crecer N.\n")

    partes.append("## Altura del árbol y tiempo de búsqueda\n")
    partes.append(tabla_markdown(costo_por_nivel.sort_values(["curva", "N"]),
                                 ["curva", "N", "altura_media", "media", "ns_por_nivel"],
                                 ["Estructura", "N", "Altura media", "µs por búsqueda", "ns por nivel"]) + "\n")
    partes.append("Correlación de Pearson entre altura y tiempo por búsqueda (todas las mediciones):\n")
    partes.append(tabla_markdown(correlacion, ["estructura", "r_pearson", "p_valor", "mediciones"],
                                 ["Estructura", "r", "p-valor", "Mediciones"]) + "\n")

    partes.append("## ¿Desde qué N el árbol supera a la lista? (búsqueda)\n")
    partes.append("Se considera diferencia clara cuando los intervalos de confianza del 95% no se superponen.\n")
    partes.append(tabla_markdown(comparacion_con_lista,
                                 ["orden", "arbol", "N_donde_arbol_es_mas_rapido",
                                  "N_donde_arbol_es_mas_lento", "N_max_comparado", "veces_mas_rapido_en_N_max"],
                                 ["Orden", "Árbol", "N donde el árbol es más rápido",
                                  "N donde el árbol es más lento", "N máx comparado",
                                  "Veces más rápido en ese N"]) + "\n")

    partes.append(f"## Experimento B — variar M (N = {int(estadisticas_m.N.iloc[0])}, datos aleatorios, "
                  "ms por lote de M búsquedas)\n")
    partes.append(tabla_markdown(estadisticas_m.sort_values(["estructura", "M"]),
                                 ["estructura", "M", "repeticiones", "media", "desv_estandar", "cv_%",
                                  "ic95_inf", "ic95_sup", "atipicos"],
                                 ["Estructura", "M", "Rep.", "Media", "Desv. est.", "CV %",
                                  "IC95 inf", "IC95 sup", "Atípicos"]) + "\n")
    partes.append("Pendiente log-log del tiempo de un lote contra M "
                  "(se espera ≈1: el doble de búsquedas, el doble de tiempo):\n")
    partes.append(tabla_markdown(pendientes_m, ["estructura", "pendiente_vs_M", "r2"],
                                 ["Estructura", "Pendiente", "R²"]) + "\n")

    with open(os.path.join(carpeta, "resumen.md"), "w", encoding="utf-8") as archivo_resumen:
        archivo_resumen.write("\n".join(partes))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rapido", action="store_true")
    argumentos = parser.parse_args()
    carpeta = os.path.join(CARPETA_DEL_PROYECTO, "resultados_prueba" if argumentos.rapido else "resultados")

    mediciones = pd.read_csv(os.path.join(carpeta, "mediciones.csv"))
    mediciones_variar_n = mediciones[mediciones.experimento == "A_variar_N"]

    estadisticas_n = calcular_estadisticas_variar_n(mediciones_variar_n)
    pendientes_n = calcular_pendientes(estadisticas_n)
    costo_por_nivel = calcular_costo_por_nivel(estadisticas_n)
    correlacion = correlacion_altura_tiempo(mediciones)
    comparacion_con_lista = comparar_arboles_con_lista(estadisticas_n)
    estadisticas_m, pendientes_m = calcular_estadisticas_variar_m(mediciones)
    tabla_estabilidad, spearman = analizar_estabilidad(mediciones)
    ventanas = resumir_duracion_ventanas(mediciones)

    estadisticas_n.to_csv(os.path.join(carpeta, "estadisticas_A.csv"), index=False)
    estadisticas_m.to_csv(os.path.join(carpeta, "estadisticas_B.csv"), index=False)
    pendientes_n.to_csv(os.path.join(carpeta, "pendientes.csv"), index=False)
    escribir_resumen(carpeta, mediciones, estadisticas_n, pendientes_n, costo_por_nivel, correlacion,
                     comparacion_con_lista, estadisticas_m, pendientes_m,
                     tabla_estabilidad, spearman, ventanas)

    print(f"Análisis guardado en {carpeta}/ (resumen.md, estadisticas_A.csv, estadisticas_B.csv, pendientes.csv)")
    print(f"Siguiente paso: python graficas.py{' --rapido' if argumentos.rapido else ''}")


if __name__ == "__main__":
    main()
