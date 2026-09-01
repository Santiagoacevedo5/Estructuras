import os
import random
import numpy as np
import pandas as pd

# Ajustes visuales para la consola de Python
np.set_printoptions(precision=4, suppress=True)
pd.set_option('display.max_columns', 10)
pd.set_option('display.width', 1000)

# ==============================================================================
# 1. RUTA Y CONFIGURACIÓN DE ESPACIO (OPTIMIZACIÓN DE ALMACENAMIENTO)
# ==============================================================================
home = os.path.expanduser('~')

# Detectar la ruta real del Escritorio (soporta OneDrive o Escritorio local)
posibles_escritorios = [
    os.path.join(home, 'OneDrive', 'Escritorio'),
    os.path.join(home, 'OneDrive', 'Desktop'),
    os.path.join(home, 'Escritorio'),
    os.path.join(home, 'Desktop')
]

escritorio_real = next((ruta for ruta in posibles_escritorios if os.path.exists(ruta)), os.getcwd())

# Definición de rutas
filename_dat = os.path.join(escritorio_real, 'matriz_gigante_100k.dat')
archivo_csv = os.path.join(escritorio_real, 'primera_fila_100k_para_enviar.csv')

filas, columnas = 100000, 100000

# OPTIMIZACIÓN DE ALMACENAMIENTO:
# 'float16' usa solo 2 bytes por elemento. Reduce el tamaño total de la matriz
# de 40 GB (usando float32) a solo ~20 GB, ahorrando 50% de espacio e I/O en disco.
dtype = 'float16'

print("=" * 80)
print(f"1. RUTA DEL ESCRITORIO: {escritorio_real}")
print(f"   - Matriz binaria (.dat): {os.path.basename(filename_dat)}")
print(f"   - Entregable (.csv):     {os.path.basename(archivo_csv)}")
print("=" * 80 + "\n")


# ==============================================================================
# 2. CREACIÓN Y ESCRITURA EN DISCO (SOLUCIÓN A RAM Y ESCRITURA LENTA)
# ==============================================================================
print("2. Creando y escribiendo la matriz en disco por bloques...")

# SOLUCIÓN AL CONSUMO DE RAM:
# np.memmap mapea el archivo directamente en disco en lugar de cargarlo en RAM.
matriz_creacion = np.memmap(filename_dat, dtype=dtype, mode='w+', shape=(filas, columnas))

# SOLUCIÓN A LA ESCRITURA LENTA A DISCO:
# Procesar bloques contiguos de 5,000 filas maximiza la velocidad de transferencia 
# secuencial del disco SSD/NVMe sin colapsar la memoria volátil.
tamano_bloque = 5000

for inicio in range(0, filas, tamano_bloque):
    fin = min(inicio + tamano_bloque, filas)
    
    # Se genera temporalmente solo el bloque actual en RAM (~1 GB por bloque)
    datos = np.random.rand(fin - inicio, columnas).astype(dtype)
    matriz_creacion[inicio:fin, :] = datos
    
    print(f"   -> Progreso: filas {inicio:,} a {fin:,} escritas")

# Forzar el volcado físico de búferes del sistema al disco y liberar memoria
matriz_creacion.flush()
del matriz_creacion
print("   ¡Matriz de 20 GB creada y guardada exitosamente!\n")


# ==============================================================================
# 3. LECTURA EXTREMADAMENTE RÁPIDA Y EXPORTACIÓN
# ==============================================================================
print("3. Conectando a la matriz en modo lectura y extrayendo la Fila 0...")

# OPTIMIZACIÓN EN LA LECTURA:
# mode='r' no carga la matriz completa en RAM. Accede de forma instantánea 
# apuntando únicamente a la dirección de memoria/byte que se requiere.
matriz_lectura = np.memmap(filename_dat, dtype=dtype, mode='r', shape=(filas, columnas))

# Extrae solo los primeros 200,000 bytes (100,000 elementos x 2 bytes) en milisegundos
primera_fila_dat = matriz_lectura[0, :]

# Convertir la fila extraída a DataFrame etiquetado de Pandas
df_primera_fila = pd.DataFrame(
    [primera_fila_dat],
    index=["Fila_0"],
    columns=[f"Col_{j}" for j in range(columnas)]
)

print(f"   Exportando la primera fila a CSV en el Escritorio...")
df_primera_fila.to_csv(archivo_csv)
print(f"   ¡Archivo '{os.path.basename(archivo_csv)}' generado para envío!\n")


# ==============================================================================
# 4. COMPROBACIÓN RÁPIDA DE MUESTRA ALEATORIA (AUDITORÍA LIGERA)
# ==============================================================================
print("4. Cargar el archivo CSV exportado para validación de la muestra...")
df_leido = pd.read_csv(archivo_csv, index_col=0)
primera_fila_csv = df_leido.values.flatten().astype(dtype)

# OPTIMIZACIÓN DE MANIPULACIÓN DE DATOS:
# Seleccionar solo 5 posiciones aleatorias de entre 100,000 para auditar la integridad 
# sin procesar ni sobrecargar el CPU.
posiciones_azar = sorted(random.sample(range(columnas), 5))

print("\n" + "=" * 80)
print("     COMPROBACIÓN DE MUESTRA ALEATORIA (5 POSICIONES AL AZAR)")
print("=" * 80)

coinciden_todas = True

for pos in posiciones_azar:
    val_dat = primera_fila_dat[pos]
    val_csv = primera_fila_csv[pos]
    
    # Comparar el valor binario del .dat contra el texto exportado en el .csv
    coinciden = np.isclose(val_dat, val_csv, atol=1e-3)
    if not coinciden:
        coinciden_todas = False
        
    estado = "COINCIDE (OK)" if coinciden else "ERROR"
    print(f"• Columna {pos:6d}  |  En Matriz .DAT: {val_dat:.4f}  |  En CSV: {val_csv:.4f}  | {estado}")


# ==============================================================================
# 5. RESULTADO FINAL
# ==============================================================================
print("-" * 80)
if coinciden_todas:
    print(" VEREDICTO: ¡Todo correcto! Los valores seleccionados al azar concuerdan.")
    print("            El archivo CSV del Escritorio está verificado y listo para enviar.")
else:
    print(" VEREDICTO: Se encontró una discrepancia entre la matriz y el CSV.")

print("=" * 80 + "\n")

# Abrir y seleccionar automáticamente el archivo listo en el Escritorio
try:
    os.system(f'explorer /select,"{archivo_csv}"')
except Exception:
    pass