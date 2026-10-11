"""
Gráficas del Laboratorio 3.

Lee los archivos que produce analisis.py y guarda las imágenes en graficas/
(o graficas_prueba/ con --rapido). No vuelve a correr ningún experimento.

Uso:
    python graficas.py
    python graficas.py --rapido
"""
import argparse
import os

import matplotlib
matplotlib.use("Agg")  # guardar imágenes sin abrir ventanas
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

COLOR_POR_ESTRUCTURA = {"Lista": "tab:red", "ABB": "tab:blue", "B+": "tab:green"}
LINEA_POR_ORDEN = {"aleatorio": "-", "ordenado": "--"}
MARCADOR_POR_ORDEN = {"aleatorio": "o", "ordenado": "s"}
NOTA_INTERVALO_CONFIANZA = ("Puntos = media de las repeticiones (cada una medida en una ventana de al menos 1 s); "
                            "barras = IC del 95 %.")


# Las estadísticas vienen en µs (búsqueda, inserción) o ms (listar, experimento B).
# Para las gráficas se convierten a SEGUNDOS. Las pendientes log-log no cambian al
# cambiar de unidad, porque multiplicar por una constante solo sube o baja la recta.
FACTOR_A_SEGUNDOS = {"busqueda": 1e-6, "insercion": 1e-6, "listar": 1e-3}
# Carpeta donde están estos archivos .py (Arboles): los resultados y gráficas se leen y guardan aquí.
CARPETA_DEL_PROYECTO = os.path.dirname(os.path.abspath(__file__))
COLUMNAS_DE_TIEMPO = ["media", "ic95_inf", "ic95_sup", "mediana", "media_sin_atipicos"]


def convertir_a_segundos(estadisticas):
    estadisticas = estadisticas.copy()
    factor = estadisticas["operacion"].map(FACTOR_A_SEGUNDOS)
    for columna in COLUMNAS_DE_TIEMPO:
        estadisticas[columna] = estadisticas[columna] * factor
    return estadisticas


def aplicar_estilo(ejes, titulo, etiqueta_eje_x, etiqueta_eje_y, nota=None):
    ejes.set_title(titulo, fontsize=12, fontweight="bold")
    ejes.set_xlabel(etiqueta_eje_x)
    ejes.set_ylabel(etiqueta_eje_y)
    ejes.grid(True, which="both", alpha=0.3)
    ejes.legend(fontsize=8)
    if nota:
        ejes.figure.text(0.01, 0.01, nota, fontsize=7.5, color="dimgray")


def guardar_grafica(figura, carpeta, nombre_archivo):
    figura.tight_layout(rect=(0, 0.04, 1, 1))
    ruta = os.path.join(carpeta, nombre_archivo)
    figura.savefig(ruta, dpi=150)
    plt.close(figura)
    print("  ", ruta)


def dibujar_curvas(ejes, estadisticas, operacion, pendientes=None):
    """Una curva por (estructura, orden) con barras de error del IC 95 %."""
    datos_operacion = estadisticas[estadisticas.operacion == operacion]
    for (estructura, orden), grupo in datos_operacion.groupby(["estructura", "orden"]):
        grupo = grupo.sort_values("N")
        etiqueta = f"{estructura}, IDs {orden}s"
        if pendientes is not None:
            fila_pendiente = pendientes[(pendientes.operacion == operacion) &
                                        (pendientes.curva == f"{estructura} ({orden})")]
            if len(fila_pendiente):
                etiqueta += f"  (pendiente = {fila_pendiente.pendiente.iloc[0]:.2f})"
        error_inferior = (grupo["media"] - grupo["ic95_inf"]).clip(lower=0)
        error_superior = grupo["ic95_sup"] - grupo["media"]
        ejes.errorbar(grupo["N"], grupo["media"], yerr=[error_inferior, error_superior], label=etiqueta,
                      color=COLOR_POR_ESTRUCTURA[estructura], linestyle=LINEA_POR_ORDEN[orden],
                      marker=MARCADOR_POR_ORDEN[orden], markersize=4, capsize=3, linewidth=1.5)


def grafica_busqueda_lineal(estadisticas, carpeta, busquedas_por_lote):
    figura, ejes = plt.subplots(figsize=(9, 5.5))
    dibujar_curvas(ejes, estadisticas, "busqueda")
    aplicar_estilo(ejes, f"Tiempo de búsqueda vs. número de estudiantes (escala lineal, M = {busquedas_por_lote})",
                   "N (número de estudiantes)", "Tiempo por búsqueda (s)", NOTA_INTERVALO_CONFIANZA)
    ejes.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))  # muestra ×10⁻³ arriba del eje
    guardar_grafica(figura, carpeta, "1_busqueda_vs_N_lineal.png")


def grafica_loglog(estadisticas, pendientes, carpeta, operacion, titulo, etiqueta_eje_y,
                   nombre_archivo, nota_extra=""):
    figura, ejes = plt.subplots(figsize=(9, 5.5))
    dibujar_curvas(ejes, estadisticas, operacion, pendientes)
    ejes.set_xscale("log")
    ejes.set_yscale("log")
    aplicar_estilo(ejes, titulo, "N (número de estudiantes, escala log)", etiqueta_eje_y,
                   NOTA_INTERVALO_CONFIANZA + " La pendiente k de cada recta indica tiempo ∝ N^k." + nota_extra)
    guardar_grafica(figura, carpeta, nombre_archivo)


def grafica_altura(estadisticas, carpeta):
    datos_arboles = estadisticas[(estadisticas.operacion == "busqueda") & estadisticas.altura_media.notna()]
    figura, ejes = plt.subplots(figsize=(9, 5.5))
    for (estructura, orden), grupo in datos_arboles.groupby(["estructura", "orden"]):
        grupo = grupo.sort_values("N")
        ejes.plot(grupo["N"], grupo["altura_media"], label=f"{estructura}, IDs {orden}s",
                  color=COLOR_POR_ESTRUCTURA[estructura], linestyle=LINEA_POR_ORDEN[orden],
                  marker=MARCADOR_POR_ORDEN[orden], markersize=4)
    valores_n = np.array(sorted(estadisticas.N.unique()), dtype=float)
    ejes.plot(valores_n, np.ceil(np.log2(valores_n + 1)), color="black", linestyle=":",
              label="Mínima posible para un ABB: ⌈log₂(N+1)⌉")
    ejes.plot(valores_n, valores_n, color="gray", linestyle="-.", label="Altura = N (árbol degenerado)")
    ejes.set_xscale("log")
    ejes.set_yscale("log")
    aplicar_estilo(ejes, "Altura del árbol vs. número de estudiantes", "N (número de estudiantes, escala log)",
                   "Altura (niveles, escala log)", "Altura media de las repeticiones.")
    guardar_grafica(figura, carpeta, "3_altura_vs_N.png")


def grafica_tiempo_vs_altura(estadisticas, carpeta):
    datos_arboles = estadisticas[(estadisticas.operacion == "busqueda") & estadisticas.altura_media.notna()]
    figura, ejes = plt.subplots(figsize=(9, 5.5))
    for (estructura, orden), grupo in datos_arboles.groupby(["estructura", "orden"]):
        ejes.scatter(grupo["altura_media"], grupo["media"], label=f"{estructura}, IDs {orden}s",
                     color=COLOR_POR_ESTRUCTURA[estructura], marker=MARCADOR_POR_ORDEN[orden], s=35, alpha=0.8)
    ejes.set_xscale("log")
    ejes.set_yscale("log")
    aplicar_estilo(ejes, "Tiempo de búsqueda vs. altura del árbol", "Altura del árbol (niveles, escala log)",
                   "Tiempo por búsqueda (s, escala log)", "Cada punto es un valor de N (media de las repeticiones).")
    guardar_grafica(figura, carpeta, "4_tiempo_vs_altura.png")


def grafica_busqueda_vs_m(estadisticas_m, carpeta):
    figura, ejes = plt.subplots(figsize=(9, 5.5))
    for estructura, grupo in estadisticas_m.groupby("estructura"):
        grupo = grupo.sort_values("M")
        error_inferior = (grupo["media"] - grupo["ic95_inf"]).clip(lower=0)
        error_superior = grupo["ic95_sup"] - grupo["media"]
        ejes.errorbar(grupo["M"], grupo["media"], yerr=[error_inferior, error_superior], label=estructura,
                      color=COLOR_POR_ESTRUCTURA[estructura], marker="o", markersize=4, capsize=3)
    ejes.set_xscale("log")
    ejes.set_yscale("log")
    cantidad_estudiantes = int(estadisticas_m.N.iloc[0])
    aplicar_estilo(ejes, f"Tiempo de un lote de búsquedas vs. tamaño del lote M "
                         f"(N = {cantidad_estudiantes}, IDs aleatorios)",
                   "M (número de búsquedas, escala log)", "Tiempo de un lote de M búsquedas (s, escala log)",
                   NOTA_INTERVALO_CONFIANZA)
    guardar_grafica(figura, carpeta, "7_busqueda_vs_M.png")


def grafica_dispersion(mediciones, carpeta):
    """Cajas y bigotes: muestra la distribución de las repeticiones y los atípicos."""
    mediciones_a = mediciones[mediciones.experimento == "A_variar_N"].copy()
    cantidad_estudiantes = 10000 if 10000 in mediciones_a.N.values else mediciones_a.N.max()
    mediciones_a = mediciones_a[mediciones_a.N == cantidad_estudiantes]
    mediciones_a["segundos_por_busqueda"] = mediciones_a["t_busqueda_s"] / mediciones_a["M"]
    grupos, etiquetas, colores = [], [], []
    for estructura in ("Lista", "ABB", "B+"):
        for orden in ("ordenado", "aleatorio"):
            tiempos = mediciones_a[(mediciones_a.estructura == estructura) &
                                   (mediciones_a.orden == orden)]["segundos_por_busqueda"]
            if len(tiempos):
                grupos.append(tiempos.values)
                etiquetas.append(f"{estructura}\n{orden}")
                colores.append(COLOR_POR_ESTRUCTURA[estructura])
    figura, ejes = plt.subplots(figsize=(9, 5.5))
    cajas = ejes.boxplot(grupos, patch_artist=True, whis=1.5)
    ejes.set_xticks(range(1, len(etiquetas) + 1), etiquetas)
    for caja, color in zip(cajas["boxes"], colores):
        caja.set_facecolor(color)
        caja.set_alpha(0.4)
    ejes.set_yscale("log")
    ejes.set_title(f"Dispersión de las repeticiones del tiempo de búsqueda (N = {cantidad_estudiantes})",
                   fontsize=12, fontweight="bold")
    ejes.set_xlabel("Estructura y orden de inserción")
    ejes.set_ylabel("Tiempo por búsqueda (s, escala log)")
    ejes.grid(True, axis="y", which="both", alpha=0.3)
    figura.text(0.01, 0.01, "Caja = 50 % central (Q1 a Q3); línea = mediana; "
                            "círculos = atípicos según la regla 1.5·IQR.", fontsize=7.5, color="dimgray")
    guardar_grafica(figura, carpeta, "8_dispersion_busqueda.png")


def grafica_estabilidad(mediciones, carpeta):
    """Tiempo relativo (medición / mediana de su grupo) a lo largo del experimento."""
    if "momento_min" not in mediciones.columns:
        print("   (sin columna momento_min: se omite la gráfica de estabilidad)")
        return
    from analisis import tiempos_normalizados
    normalizadas = tiempos_normalizados(mediciones).sort_values("momento_min")
    figura, ejes = plt.subplots(figsize=(9, 5.5))
    ejes.scatter(normalizadas["momento_min"], normalizadas["relativo"], s=6, alpha=0.25, color="tab:gray",
                 label="Cada medición de búsqueda")
    tendencia = normalizadas["relativo"].rolling(max(len(normalizadas) // 40, 5), center=True).median()
    ejes.plot(normalizadas["momento_min"], tendencia, color="tab:purple", linewidth=2,
              label="Mediana móvil (tendencia)")
    ejes.axhline(1, color="black", linestyle=":", label="1 = tiempo típico de su grupo")
    ejes.set_ylim(0, 3)
    aplicar_estilo(ejes, "Estabilidad del computador durante el experimento",
                   "Momento de la medición (minutos desde el inicio)",
                   "Tiempo relativo (medición / mediana de su grupo)",
                   "Si el computador mantuvo la misma velocidad, la línea morada debe quedarse cerca de 1. "
                   "Valores por encima de 3 no se muestran.")
    guardar_grafica(figura, carpeta, "9_estabilidad_en_el_tiempo.png")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rapido", action="store_true")
    argumentos = parser.parse_args()
    carpeta_origen = os.path.join(CARPETA_DEL_PROYECTO, "resultados_prueba" if argumentos.rapido else "resultados")
    carpeta_destino = os.path.join(CARPETA_DEL_PROYECTO, "graficas_prueba" if argumentos.rapido else "graficas")
    os.makedirs(carpeta_destino, exist_ok=True)

    estadisticas_n = pd.read_csv(os.path.join(carpeta_origen, "estadisticas_A.csv"))
    estadisticas_n = convertir_a_segundos(estadisticas_n)
    estadisticas_m = pd.read_csv(os.path.join(carpeta_origen, "estadisticas_B.csv"))
    for columna in ["media", "ic95_inf", "ic95_sup"]:
        estadisticas_m[columna] = estadisticas_m[columna] * 1e-3  # ms -> s
    pendientes = pd.read_csv(os.path.join(carpeta_origen, "pendientes.csv"))
    mediciones = pd.read_csv(os.path.join(carpeta_origen, "mediciones.csv"))
    busquedas_por_lote = int(mediciones[mediciones.experimento == "A_variar_N"].M.iloc[0])

    print("Gráficas guardadas:")
    grafica_busqueda_lineal(estadisticas_n, carpeta_destino, busquedas_por_lote)
    grafica_loglog(estadisticas_n, pendientes, carpeta_destino, "busqueda",
                   f"Tiempo de búsqueda vs. N (escala log-log, M = {busquedas_por_lote})",
                   "Tiempo por búsqueda (s, escala log)", "2_busqueda_vs_N_loglog.png")
    grafica_altura(estadisticas_n, carpeta_destino)
    grafica_tiempo_vs_altura(estadisticas_n, carpeta_destino)
    grafica_loglog(estadisticas_n, pendientes, carpeta_destino, "insercion",
                   "Tiempo de inserción vs. N (escala log-log)",
                   "Tiempo medio por inserción (s, escala log)", "5_insercion_vs_N.png",
                   " Por inserción = tiempo de construir / N.")
    grafica_loglog(estadisticas_n, pendientes, carpeta_destino, "listar",
                   "Tiempo de listar todos los estudiantes en orden vs. N (escala log-log)",
                   "Tiempo del listado completo (s, escala log)", "6_listar_vs_N.png")
    grafica_busqueda_vs_m(estadisticas_m, carpeta_destino)
    grafica_dispersion(mediciones, carpeta_destino)
    grafica_estabilidad(mediciones, carpeta_destino)


if __name__ == "__main__":
    main()
