"""

   ALGORITMO DE PROCESAMIENTO DE SEÑALES - SISTEMA HÁPTICO MUSICAL          
   Proyecto: MusicHaptic (Prácticas Sistemas Computacionales)               
                                                                              
   Función: Analiza archivos de audio (.wav/.mp3) mediante FFT              
   (Transformada Rápida de Fourier) y detecta las notas musicales           
   presentes, generando una secuencia de comandos hápticos compatibles      
   con la app móvil (Kotlin) y el hardware ESP32 (Arduino).                 
                                                                              
   Dependencias: numpy, scipy, librosa, soundfile, matplotlib               
   Instalación: pip install numpy scipy librosa soundfile matplotlib        

"""

import sys

# MOCK NUMBA: Librosa requiere numba para JIT, pero no está disponible para Android.
# Este bloque permite que librosa se importe y funcione en modo pure-python.
class MockNumba:
    @staticmethod
    def jit(*args, **kwargs):
        # Si se usa como decorador @jit
        if len(args) == 1 and hasattr(args[0], "__call__"):
            return args[0]
        # Si se usa como @jit(nopython=True)
        return lambda f: f

    njit = jit
    vectorize = jit
    guvectorize = jit
    stencil = jit

# Inyectar el mock antes de importar librosa
sys.modules["numba"] = MockNumba
sys.modules["numba.np.ufunc"] = MockNumba

import numpy as np
import json
import os
import time
from datetime import datetime
import librosa
import matplotlib.pyplot as plt
import soundfile as sf
import audioread
import decorator
import joblib
import pooch
import packaging
import lazy_loader

# ============================================================================
# PARTE 1: TABLA DE TRIPLE CODIFICACIÓN HÁPTICA
# Basada en BaseDatosHelper.kt de la app móvil de 5to semestre
# y el esquemático output.pdf del equipo de Industrial
# ============================================================================

ESCALA_CROMATICA = {
    "DO":   {"frecuencia_hz": 62.15,   "ubicacion": 0.0,  "amplitud": 255, "mux": "U4", "canal": 0, "lra": [1]},   # Fila 1 - Izquierda
    "DO#":  {"frecuencia_hz": 75.82,   "ubicacion": 0.9,  "amplitud": 245, "mux": "U4", "canal": 1, "lra": [2]},   # Fila 1 - Derecha
    "RE":   {"frecuencia_hz": 92.50,   "ubicacion": 1.8,  "amplitud": 240, "mux": "U4", "canal": 2, "lra": [3]},   # Fila 2 - Izquierda
    "RE#":  {"frecuencia_hz": 112.85,  "ubicacion": 2.7,  "amplitud": 235, "mux": "U4", "canal": 3, "lra": [4]},   # Fila 2 - Derecha
    "MI":   {"frecuencia_hz": 137.68,  "ubicacion": 3.6,  "amplitud": 230, "mux": "U4", "canal": 4, "lra": [5]},   # Fila 3 - Izquierda
    "FA":   {"frecuencia_hz": 167.97,  "ubicacion": 4.5,  "amplitud": 225, "mux": "U4", "canal": 5, "lra": [6]},   # Fila 3 - Derecha
    "FA#":  {"frecuencia_hz": 204.92,  "ubicacion": 5.4,  "amplitud": 220, "mux": "U5", "canal": 0, "lra": [7]},   # Fila 4 - Izquierda
    "SOL":  {"frecuencia_hz": 250.00,  "ubicacion": 6.3,  "amplitud": 225, "mux": "U5", "canal": 1, "lra": [8]},   # Fila 4 - Derecha
    "SOL#": {"frecuencia_hz": 305.00,  "ubicacion": 7.2,  "amplitud": 230, "mux": "U5", "canal": 2, "lra": [9]},   # Fila 5 - Izquierda
    "LA":   {"frecuencia_hz": 372.10,  "ubicacion": 8.1,  "amplitud": 235, "mux": "U5", "canal": 3, "lra": [10]},  # Fila 5 - Derecha
    "LA#":  {"frecuencia_hz": 453.96,  "ubicacion": 9.0,  "amplitud": 245, "mux": "U5", "canal": 4, "lra": [11]},  # Fila 6 - Izquierda
    "SI":   {"frecuencia_hz": 553.83,  "ubicacion": 10.0, "amplitud": 255, "mux": "U5", "canal": 5, "lra": [12]},  # Fila 6 - Derecha
}

# Generar tabla de frecuencias de referencia para TODAS las octavas (C0-C8)
# Esto permite detectar notas en cualquier rango del audio
FRECUENCIAS_REFERENCIA = {}
NOTAS_ORDEN = ["DO", "DO#", "RE", "RE#", "MI", "FA", "FA#", "SOL", "SOL#", "LA", "LA#", "SI"]

for octava in range(0, 9):
    for i, nombre_nota in enumerate(NOTAS_ORDEN):
        # Fórmula estándar: f = 440 * 2^((n-69)/12) donde n = nota MIDI
        nota_midi = 12 * (octava + 1) + i  # C1 = 24, A4 = 69
        frecuencia = 440.0 * (2.0 ** ((nota_midi - 69) / 12.0))
        clave = f"{nombre_nota}{octava}"
        FRECUENCIAS_REFERENCIA[clave] = {
            "frecuencia": frecuencia,
            "nombre_base": nombre_nota,
            "octava": octava,
            "midi": nota_midi
        }


# ============================================================================
# PARTE 2: FUNCIONES DE PROCESAMIENTO DE SEÑALES (FFT)
# ============================================================================

def cargar_audio(ruta_archivo):
    """
    Carga un archivo de audio (.wav o .mp3) y lo convierte a mono.
    Usa librosa para compatibilidad con múltiples formatos.
    
    Args:
        ruta_archivo: Ruta al archivo de audio
    
    Returns:
        tuple: (señal_audio, tasa_muestreo)
    """
    import librosa
    
    print(f"\n{'='*60}")
    print(f"  CARGANDO AUDIO: {os.path.basename(ruta_archivo)}")
    print(f"{'='*60}")
    
    # librosa carga a mono y normaliza automáticamente a float32 [-1.0, 1.0]
    senal, sr = librosa.load(ruta_archivo, sr=22050, mono=True)
    
    duracion = len(senal) / sr
    print(f"  [OK] Tasa de muestreo: {sr} Hz")
    print(f"  [OK] Duración: {duracion:.2f} segundos")
    print(f"  [OK] Muestras totales: {len(senal):,}")
    
    return senal, sr


def aplicar_fft_por_ventanas(senal, sr, tamano_ventana_ms=200, solapamiento=0.5):
    """
    Aplica la Transformada Rápida de Fourier (FFT) al audio dividido en
    ventanas temporales. Cada ventana produce un espectro de frecuencias.
    
    Este es el NÚCLEO del procesamiento de señales:
    - Divide el audio en segmentos pequeños (ventanas)
    - A cada ventana le aplica una función de ventaneo (Hann) para suavizar bordes
    - Calcula la FFT para obtener las frecuencias dominantes
    - Detecta la frecuencia fundamental (pitch) de cada ventana
    
    Args:
        senal: Array numpy con la señal de audio
        sr: Tasa de muestreo en Hz
        tamano_ventana_ms: Duración de cada ventana en milisegundos
        solapamiento: Fracción de solapamiento entre ventanas (0.0 a 0.9)
    
    Returns:
        list: Lista de diccionarios con {tiempo, frecuencia_dominante, amplitud}
    """
    print(f"\n{'='*60}")
    print(f"  APLICANDO FFT (Transformada Rápida de Fourier)")
    print(f"{'='*60}")
    
    # Calcular parámetros de ventaneo
    muestras_por_ventana = int(sr * tamano_ventana_ms / 1000)
    paso = int(muestras_por_ventana * (1 - solapamiento))
    ventana_hann = np.hanning(muestras_por_ventana)
    
    print(f"  [OK] Tamaño de ventana: {tamano_ventana_ms} ms ({muestras_por_ventana} muestras)")
    print(f"  [OK] Solapamiento: {solapamiento*100:.0f}%")
    print(f"  [OK] Paso entre ventanas: {paso} muestras")
    
    resultados = []
    total_ventanas = (len(senal) - muestras_por_ventana) // paso + 1
    
    print(f"  [OK] Ventanas a procesar: {total_ventanas}")
    print(f"\n  Procesando", end="")
    
    for i in range(0, len(senal) - muestras_por_ventana, paso):
        # 1. Extraer segmento de audio (ventana)
        segmento = senal[i : i + muestras_por_ventana]
        
        # 2. Aplicar ventana de Hann (suaviza los bordes para evitar artefactos)
        segmento_ventaneado = segmento * ventana_hann
        
        # 3. Calcular la FFT con zero-padding (4x) para mayor resolución de frecuencia
        # Sin padding: resolución = sr/ventana = 22050/4410 = 5 Hz por bin
        # Con padding 4x: resolución = 22050/17640 = ~1.25 Hz por bin
        nfft = muestras_por_ventana * 4
        espectro = np.fft.rfft(segmento_ventaneado, n=nfft)
        magnitudes = np.abs(espectro)
        frecuencias = np.fft.rfftfreq(nfft, 1.0 / sr)
        
        # 4. Filtrar rango musical útil (30 Hz a 2000 Hz)
        # Las notas musicales que nos interesan están entre ~60 Hz (DO2) y ~554 Hz (SI)
        # pero buscamos hasta 2000 Hz para detectar armónicos
        mascara = (frecuencias >= 30) & (frecuencias <= 2000)
        frecuencias_filtradas = frecuencias[mascara]
        magnitudes_filtradas = magnitudes[mascara]
        
        if len(magnitudes_filtradas) == 0:
            continue
        
        # 5. Encontrar la frecuencia con mayor energía (pico dominante)
        indice_pico = np.argmax(magnitudes_filtradas)
        frecuencia_dominante = frecuencias_filtradas[indice_pico]
        amplitud_pico = magnitudes_filtradas[indice_pico]
        
        # 6. Calcular el tiempo en segundos
        tiempo_seg = i / sr
        
        # 7. Filtrar silencios (amplitud muy baja = no hay nota)
        umbral_silencio = np.max(magnitudes) * 0.08  # 8% del pico máximo global
        if amplitud_pico > umbral_silencio:
            resultados.append({
                "tiempo_s": round(tiempo_seg, 3),
                "frecuencia_hz": round(float(frecuencia_dominante), 2),
                "amplitud": round(float(amplitud_pico), 2)
            })
        
        # Progreso visual
        progreso = len(resultados)
        if progreso % 50 == 0:
            print(".", end="", flush=True)
    
    print(f"\n  [OK] Ventanas con notas detectadas: {len(resultados)} de {total_ventanas}")
    
    return resultados


def frecuencia_a_nota(frecuencia_hz):
    """
    Convierte una frecuencia en Hz a su nota musical más cercana.
    Usa la tabla de frecuencias del PROYECTO (ESCALA_CROMATICA) en lugar de
    la afinación estándar A440, ya que el proyecto usa frecuencias personalizadas
    (ej: DO=62.15Hz en vez del estándar C2=65.41Hz).
    
    Busca en múltiples octavas (0-8) multiplicando/dividiendo por 2.
    
    Args:
        frecuencia_hz: Frecuencia a identificar
    
    Returns:
        dict: {nombre, nombre_base, octava, frecuencia_referencia, desviacion_cents}
    """
    if frecuencia_hz <= 0:
        return None
    
    menor_diferencia = float('inf')
    nota_encontrada = None
    
    # Buscar en la tabla del proyecto, expandida a múltiples octavas
    for nombre_nota, info in ESCALA_CROMATICA.items():
        freq_base = info["frecuencia_hz"]
        
        # Probar en octavas -3 a +5 (cubre todo el rango audible)
        for octava_offset in range(-3, 6):
            freq_octava = freq_base * (2.0 ** octava_offset)
            
            if freq_octava <= 0:
                continue
            
            # Diferencia en cents (1200 cents = 1 octava, 100 cents = 1 semitono)
            cents = 1200 * np.log2(frecuencia_hz / freq_octava)
            diferencia = abs(cents)
            
            if diferencia < menor_diferencia:
                menor_diferencia = diferencia
                nota_encontrada = {
                    "nombre_completo": f"{nombre_nota}{octava_offset + 3}",
                    "nombre_base": nombre_nota,
                    "octava": octava_offset + 3,
                    "frecuencia_referencia": freq_octava,
                    "desviacion_cents": round(cents, 1)
                }
    
    return nota_encontrada


def detectar_secuencia_notas(resultados_fft, duracion_minima_ms=180):
    """
    Convierte los resultados de FFT/pYIN en una secuencia limpia de notas musicales.
    
    Aplica 3 técnicas de posprocesamiento para máxima limpieza:
    1. Filtro de Mayoría Temporal (Pitch Smoothing): Una ventana deslizante de 5 frames
       (~230 ms) elimina micro-transiciones o falsos positivos en el ataque de las notas.
    2. Consolidación Agrupada: Concatena frames consecutivos con la misma nota.
    3. Fusión y Absorción Inteligente: Si dos notas iguales están separadas por una
       micro-interrupción (<150 ms), las fusiona. Si una nota dura menos de duracion_minima_ms
       (180 ms), se absorbe como transición.
    
    Args:
        resultados_fft: Lista de resultados del análisis (tiempo, frecuencia, amplitud)
        duracion_minima_ms: Duración mínima en ms para considerar una nota válida (def: 180ms)
    
    Returns:
        list: Secuencia de notas limpia compatible con la app y el ESP32
    """
    print(f"\n{'='*60}")
    print(f"  DETECTANDO SECUENCIA DE NOTAS MUSICALES (CON SUAVIZADO)")
    print(f"{'='*60}")
    
    if not resultados_fft:
        print("  [ADVERTENCIA] No se detectaron frecuencias en el audio.")
        return []
    
    # 1. Convertir cada frecuencia detectada a su nota más cercana
    frames_raw = []
    for r in resultados_fft:
        nota = frecuencia_a_nota(r["frecuencia_hz"])
        if nota and abs(nota["desviacion_cents"]) < 60:  # Tolerancia 60 cents
            frames_raw.append({
                "tiempo_s": r["tiempo_s"],
                "nota_base": nota["nombre_base"],
                "frecuencia_detectada": r["frecuencia_hz"],
                "amplitud_raw": r["amplitud"]
            })
    
    print(f"  [OK] Frames válidos antes de suavizado: {len(frames_raw)}")
    if not frames_raw:
        return []
    
    # 2. Filtro de Mayoría Temporal (Sliding Majority Window - 11 frames)
    # Suaviza el pitch asignando a cada frame la nota más frecuente de sus vecinos inmediatos
    frames_suavizados = []
    w_size = 5  # radio 5 = ventana de 11 frames (~250ms)
    for i in range(len(frames_raw)):
        inicio_idx = max(0, i - w_size)
        fin_idx = min(len(frames_raw), i + w_size + 1)
        vecinos = [frames_raw[j]["nota_base"] for j in range(inicio_idx, fin_idx)]
        
        # Encontrar la nota mayoritaria en el vecindario
        nota_mayoritaria = max(set(vecinos), key=vecinos.count)
        
        frame_copy = dict(frames_raw[i])
        frame_copy["nota_base"] = nota_mayoritaria
        frames_suavizados.append(frame_copy)
    
    # 3. Agrupar notas consecutivas iguales
    secuencia_preliminar = []
    nota_actual = frames_suavizados[0]
    inicio_actual = nota_actual["tiempo_s"]
    amplitud_acumulada = [nota_actual["amplitud_raw"]]
    
    for i in range(1, len(frames_suavizados)):
        n = frames_suavizados[i]
        
        if n["nota_base"] == nota_actual["nota_base"]:
            amplitud_acumulada.append(n["amplitud_raw"])
        else:
            duracion_ms = (n["tiempo_s"] - inicio_actual) * 1000
            secuencia_preliminar.append({
                "nota": nota_actual["nota_base"],
                "duracion_ms": round(duracion_ms),
                "tiempo_inicio_s": round(inicio_actual, 3),
                "amplitud_prom": round(np.mean(amplitud_acumulada), 2)
            })
            nota_actual = n
            inicio_actual = n["tiempo_s"]
            amplitud_acumulada = [n["amplitud_raw"]]
            
    # Guardar último grupo
    duracion_final = (frames_suavizados[-1]["tiempo_s"] - inicio_actual) * 1000 + 46
    secuencia_preliminar.append({
        "nota": nota_actual["nota_base"],
        "duracion_ms": round(duracion_final),
        "tiempo_inicio_s": round(inicio_actual, 3),
        "amplitud_prom": round(np.mean(amplitud_acumulada), 2)
    })
    
    # 4. Fusión post-procesamiento (Unir notas iguales separadas por transiciones cortas)
    secuencia_fusionada = []
    for elem in secuencia_preliminar:
        if not secuencia_fusionada:
            secuencia_fusionada.append(elem)
            continue
        
        anterior = secuencia_fusionada[-1]
        # Si es exactamente la misma nota y el silencio o transición entre ellas es muy corta (<180ms)
        tiempo_diferencia = (elem["tiempo_inicio_s"] - (anterior["tiempo_inicio_s"] + anterior["duracion_ms"]/1000.0)) * 1000
        
        if elem["nota"] == anterior["nota"] and tiempo_diferencia < 180:
            # Fusionar en la nota anterior
            anterior["duracion_ms"] += round(tiempo_diferencia + elem["duracion_ms"])
        else:
            secuencia_fusionada.append(elem)
            
    # 5. Filtrar por duración mínima (eliminar micro-pulsos transitorios < duracion_minima_ms)
    secuencia_limpia = []
    for elem in secuencia_fusionada:
        if elem["duracion_ms"] >= duracion_minima_ms:
            cod = ESCALA_CROMATICA.get(elem["nota"], None)
            secuencia_limpia.append({
                "nota": elem["nota"],
                "frecuencia_hz": cod["frecuencia_hz"] if cod else 150.0,
                "ubicacion_espacial": cod["ubicacion"] if cod else 5.0,
                "amplitud": cod["amplitud"] if cod else 220,
                "duracion_ms": elem["duracion_ms"],
                "tiempo_inicio_s": elem["tiempo_inicio_s"],
                "mux": cod["mux"] if cod else "U4",
                "canal_mux": cod["canal"] if cod else 0,
                "actuadores_lra": cod["lra"] if cod else [1],
                "amplitud_promedio_raw": elem["amplitud_prom"]
            })
    
    print(f"  [OK] Notas consolidadas en secuencia final: {len(secuencia_limpia)}")
    return secuencia_limpia


# ============================================================================
# PARTE 3: GENERACIÓN DE SALIDA - JSON COMPATIBLE CON APP Y ESP32
# ============================================================================

def generar_salida_json(secuencia, nombre_archivo, ruta_salida=None):
    """
    Exporta la secuencia de notas detectadas como JSON.
    Este JSON es directamente consumible por:
    - La app móvil (Kotlin) -> para reproducir la secuencia háptica
    - El ESP32 (Arduino) -> como tabla de comandos BLE
    
    Args:
        secuencia: Lista de notas detectadas
        nombre_archivo: Nombre del archivo de audio procesado
        ruta_salida: Ruta donde guardar el JSON (opcional)
    """
    salida = {
        "metadata": {
            "archivo_original": nombre_archivo,
            "fecha_procesamiento": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "algoritmo_version": "1.0",
            "total_notas_detectadas": len(secuencia),
            "notas_unicas": list(set(n["nota"] for n in secuencia)),
            "duracion_total_ms": sum(n["duracion_ms"] for n in secuencia)
        },
        "secuencia_haptica": [],
        "diccionario_frecuencias": []
    }
    
    # Secuencia completa para reproducción
    for i, nota in enumerate(secuencia):
        salida["secuencia_haptica"].append({
            "orden": i + 1,
            "nota": nota["nota"],
            "frecuencia_hz": nota["frecuencia_hz"],
            "ubicacion_espacial": nota["ubicacion_espacial"],
            "amplitud": nota["amplitud"],
            "duracion_ms": nota["duracion_ms"],
            "tiempo_inicio_s": nota["tiempo_inicio_s"],
            "comando_ble": f'{{"n":"{nota["nota"]}","f":{nota["frecuencia_hz"]},"u":{nota["ubicacion_espacial"]},"a":{nota["amplitud"]},"d":{nota["duracion_ms"]}}}',
            "hardware": {
                "mux": nota["mux"],
                "canal_mux": nota["canal_mux"],
                "actuadores_lra": nota["actuadores_lra"]
            }
        })
    
    # Diccionario de frecuencias únicas (compatible con tabla diccionario_frecuencias de la BD)
    notas_unicas = {}
    for nota in secuencia:
        if nota["nota"] not in notas_unicas:
            notas_unicas[nota["nota"]] = {
                "nota_musical": nota["nota"],
                "frecuencia_hz": nota["frecuencia_hz"],
                "ubicacion_espacial": nota["ubicacion_espacial"]
            }
    salida["diccionario_frecuencias"] = list(notas_unicas.values())
    
    # Guardar archivo
    if ruta_salida is None:
        nombre_base = os.path.splitext(nombre_archivo)[0]
        ruta_salida = f"salida_haptica_{nombre_base}.json"
    
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    
    print(f"\n  [OK] JSON exportado: {ruta_salida}")
    
    return salida


def imprimir_secuencia(secuencia):
    """
    Muestra la secuencia detectada en formato tabla en la terminal.
    Útil para verificación visual y demostración en clase.
    """
    print(f"\n{'='*90}")
    print(f"  SECUENCIA DE NOTAS DETECTADAS - TRIPLE CODIFICACIÓN HÁPTICA")
    print(f"{'='*90}")
    print(f"  {'#':>3}  {'Nota':<5}  {'Freq (Hz)':>9}  {'Ubic (0-10)':>11}  {'Amplitud':>8}  {'Duración':>8}  {'MUX':>3}  {'LRA':<8}")
    print(f"  {''*3}{''*5}{''*9}{''*11}{''*8}{''*8}{''*3}{''*8}")
    
    for i, nota in enumerate(secuencia):
        lra_str = ",".join(str(l) for l in nota["actuadores_lra"])
        print(f"  {i+1:>3}  {nota['nota']:<5}  {nota['frecuencia_hz']:>9.2f}  {nota['ubicacion_espacial']:>11.1f}  {nota['amplitud']:>8}  {nota['duracion_ms']:>6}ms  {nota['mux']:>3}  LRA {lra_str:<4}")
    
    print(f"  {''*90}")
    print(f"  Total: {len(secuencia)} notas  Duración: {sum(n['duracion_ms'] for n in secuencia)/1000:.1f}s  Notas únicas: {len(set(n['nota'] for n in secuencia))}")


def generar_espectrograma(senal, sr, secuencia, nombre_archivo):
    """
    Genera una visualización del espectrograma con las notas detectadas marcadas.
    Requiere matplotlib. Si no está disponible, se omite sin error.
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        
        print(f"\n  Generando espectrograma...")
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={'height_ratios': [3, 1]})
        fig.suptitle(f'Análisis de Procesamiento de Señales\n"{nombre_archivo}"', fontsize=14, fontweight='bold')
        
        # Espectrograma (arriba)
        ax1.specgram(senal, Fs=sr, NFFT=2048, noverlap=1024, cmap='magma')
        ax1.set_ylabel('Frecuencia (Hz)')
        ax1.set_ylim(0, 1000)
        ax1.set_title('Espectrograma FFT - Distribución de Frecuencias en el Tiempo')
        
        # Marcar las frecuencias de la escala cromática
        colores_notas = {
            "DO": "#FF6B35", "DO#": "#FF8C42", "RE": "#FFD166", "RE#": "#E8E852",
            "MI": "#06D6A0", "FA": "#118AB2", "FA#": "#5E60CE", "SOL": "#7B2CBF",
            "SOL#": "#9D4EDD", "LA": "#C77DFF", "LA#": "#E0AAFF", "SI": "#F72585"
        }
        
        for nota_info in secuencia:
            color = colores_notas.get(nota_info["nota"], "#FFFFFF")
            ax1.axhline(y=nota_info["frecuencia_hz"], color=color, alpha=0.4, linewidth=0.8, linestyle='--')
        
        # Secuencia de notas (abajo)
        for nota_info in secuencia:
            color = colores_notas.get(nota_info["nota"], "#888888")
            x = nota_info["tiempo_inicio_s"]
            w = nota_info["duracion_ms"] / 1000
            ax2.barh(nota_info["ubicacion_espacial"], w, left=x, height=0.6, color=color, alpha=0.8, edgecolor='white', linewidth=0.5)
            if w > 0.15:  # Solo mostrar texto si la barra es suficientemente ancha
                ax2.text(x + w/2, nota_info["ubicacion_espacial"], nota_info["nota"], 
                        ha='center', va='center', fontsize=7, fontweight='bold', color='white')
        
        ax2.set_xlabel('Tiempo (segundos)')
        ax2.set_ylabel('Ubicación (muñeca->codo)')
        ax2.set_ylim(-0.5, 10.5)
        ax2.set_yticks([0, 2.5, 5, 7.5, 10])
        ax2.set_yticklabels(['Muñeca\n(0.0)', '', 'Centro\n(5.0)', '', 'Codo\n(10.0)'])
        ax2.set_title('Secuencia Háptica - Ubicación Espacial en el Antebrazo')
        
        plt.tight_layout()
        
        ruta_imagen = f"espectrograma_{os.path.splitext(nombre_archivo)[0]}.png"
        plt.savefig(ruta_imagen, dpi=150, bbox_inches='tight')
        print(f"  [OK] Espectrograma guardado: {ruta_imagen}")
        
        plt.show()
        
    except ImportError:
        print("  [ADVERTENCIA] matplotlib no instalado. Omitiendo visualización.")
    except Exception as e:
        print(f"  [ADVERTENCIA] Error generando espectrograma: {e}")


# ============================================================================
# PARTE 4: MODO DEMO - GENERADOR DE AUDIO DE PRUEBA
# Crea un archivo WAV sintético con notas musicales conocidas
# para demostrar el algoritmo sin necesitar un archivo real
# ============================================================================

def generar_audio_demo(nombre_salida="demo_escala_musical.wav"):
    """
    Genera un archivo WAV de demostración con la escala cromática completa de 12 notas:
    DO, DO#, RE, RE#, MI, FA, FA#, SOL, SOL#, LA, LA#, SI.
    Cada nota dura 450ms con 100ms de silencio entre ellas.
    Permite validar y calibrar los 12 actuadores LRA y los multiplexores U4/U5.
    """
    from scipy.io import wavfile
    
    print(f"\n{'='*60}")
    print(f"  GENERANDO AUDIO DE DEMOSTRACIÓN — ESCALA CROMÁTICA (12 NOTAS)")
    print(f"{'='*60}")
    
    sr = 22050
    duracion_nota = 0.80  # segundos por nota
    silencio = 0.25  # segundos de silencio entre notas
    
    notas_demo = ["DO", "DO#", "RE", "RE#", "MI", "FA", "FA#", "SOL", "SOL#", "LA", "LA#", "SI"]
    senal_completa = np.array([], dtype=np.float32)
    
    for nombre in notas_demo:
        freq = ESCALA_CROMATICA[nombre]["frecuencia_hz"]
        t = np.linspace(0, duracion_nota, int(sr * duracion_nota), endpoint=False)
        
        # Generar onda sinusoidal con ligero armónico para estructura acústica realista (pYIN)
        onda = np.sin(2 * np.pi * freq * t) + 0.15 * np.sin(4 * np.pi * freq * t)
        
        # Envolvente: ataque 20ms, sustain, release 20ms
        envolvente = np.ones_like(t)
        ataque = int(0.02 * sr)
        release = int(0.02 * sr)
        envolvente[:ataque] = np.linspace(0, 1, ataque)
        envolvente[-release:] = np.linspace(1, 0, release)
        
        onda *= envolvente * 0.8  # Escalar para no saturar
        
        # Añadir silencio entre notas
        silencio_array = np.zeros(int(sr * silencio), dtype=np.float32)
        
        senal_completa = np.concatenate([senal_completa, onda.astype(np.float32), silencio_array])
        print(f"  [OK] Nota {nombre}: {freq:.2f} Hz - {duracion_nota*1000:.0f}ms")
    
    # Normalizar y guardar
    senal_completa = senal_completa / np.max(np.abs(senal_completa))
    senal_16bit = (senal_completa * 32767).astype(np.int16)
    
    wavfile.write(nombre_salida, sr, senal_16bit)
    print(f"\n  [OK] Audio generado: {nombre_salida} ({len(senal_completa)/sr:.1f}s)")
    
    return nombre_salida



# ============================================================================
# PARTE 4b: DETECCIÓN DE PITCH ROBUSTA (pYIN - Probabilistic YIN)
# Alternativa superior a FFT puro para detección de frecuencia fundamental
# ============================================================================

def detectar_pitch_pyin(senal, sr):
    """
    Usa librosa.pyin() para detectar la frecuencia fundamental (F0) del audio.
    
    pYIN es SUPERIOR a FFT puro porque:
    - Detecta correctamente la frecuencia FUNDAMENTAL, no los armónicos
    - Maneja bien las frecuencias bajas (DO a 62Hz)
    - Distingue entre nota y silencio automáticamente
    - Es el estándar en musicología computacional
    
    Args:
        senal: Array numpy con la señal de audio
        sr: Tasa de muestreo
    
    Returns:
        list: Lista de {tiempo_s, frecuencia_hz, amplitud} compatible con el pipeline
    """
    import librosa
    
    print(f"\n{'='*60}")
    print(f"  DETECCIÓN DE PITCH (pYIN - Probabilistic YIN)")
    print(f"{'='*60}")
    
    # Rango de frecuencias del proyecto: DO (62 Hz) a SI (554 Hz)
    fmin = 50   # Un poco debajo de DO para margen
    fmax = 600  # Un poco arriba de SI para margen
    
    print(f"  [OK] Rango de búsqueda: {fmin}-{fmax} Hz")
    print(f"  [OK] Algoritmo: pYIN (Probabilistic YIN)")
    
    # pYIN devuelve: f0 (frecuencias), voiced_flag (si hay nota), voiced_prob (confianza)
    f0, voiced_flag, voiced_probs = librosa.pyin(
        senal, 
        fmin=fmin, 
        fmax=fmax, 
        sr=sr,
        frame_length=4096,   # Ventana larga (4096 muestras ~185ms) para resolver con alta precisión DO (62 Hz) y graves
        hop_length=512       # Salto de ~23ms entre frames
    )
    
    # Calcular tiempos de cada frame
    tiempos = librosa.frames_to_time(np.arange(len(f0)), sr=sr, hop_length=512)
    
    # Calcular amplitudes RMS por frame para filtrar silencios
    rms = librosa.feature.rms(y=senal, frame_length=4096, hop_length=512)[0]
    if len(rms) > len(f0):
        rms = rms[:len(f0)]
    elif len(rms) < len(f0):
        rms = np.pad(rms, (0, len(f0) - len(rms)))
    
    resultados = []
    frames_con_nota = 0
    
    for i in range(len(f0)):
        # Solo procesar frames donde pYIN detectó una nota con confianza y con energía acústica real
        if voiced_flag[i] and not np.isnan(f0[i]) and f0[i] > 0 and rms[i] > 0.10:
            frames_con_nota += 1
            resultados.append({
                "tiempo_s": round(float(tiempos[i]), 3),
                "frecuencia_hz": round(float(f0[i]), 2),
                "amplitud": round(float(rms[i] * 10000), 2)  # Escalar para compatibilidad
            })
    
    print(f"  [OK] Frames analizados: {len(f0)}")
    print(f"  [OK] Frames con nota detectada: {frames_con_nota}")
    print(f"  [OK] Frames en silencio: {len(f0) - frames_con_nota}")
    
    return resultados


# ============================================================================
# PARTE 5: FUNCIÓN PRINCIPAL - PIPELINE COMPLETO
# ============================================================================

def procesar_audio(ruta_archivo=None, generar_visualizacion=True):
    """
    Pipeline completo de procesamiento de señales:
    1. Cargar audio
    2. Aplicar FFT por ventanas
    3. Detectar notas musicales
    4. Aplicar triple codificación háptica
    5. Exportar JSON y visualización
    
    Args:
        ruta_archivo: Ruta al .wav o .mp3. Si es None, genera un demo.
        generar_visualizacion: Si True, genera espectrograma con matplotlib
    
    Returns:
        dict: JSON con la secuencia háptica completa
    """
    print("\n" + "" * 60)
    print("  ALGORITMO DE PROCESAMIENTO DE SEÑALES                  ")
    print("  Sistema Háptico Musical - MusicHaptic                  ")
    print("" * 60)
    
    inicio = time.time()
    
    # PASO 1: Obtener audio
    if ruta_archivo is None or not os.path.exists(ruta_archivo):
        print("\n  [INFO] No se proporcionó archivo. Generando audio de demostración...")
        ruta_archivo = generar_audio_demo()
    
    nombre_archivo = os.path.basename(ruta_archivo)
    
    # PASO 2: Cargar audio
    senal, sr = cargar_audio(ruta_archivo)
    
    # PASO 3: Detectar frecuencias - Método Dual (pYIN + FFT)
    # pYIN (probabilistic YIN) es el estándar para detección de pitch fundamental.
    # A diferencia de FFT puro, pYIN NO confunde armónicos con el fundamental
    # (ej: DO a 62Hz tiene armónicos a 124, 186, 248 Hz - FFT puro puede
    #  confundir el armónico 248Hz con SOL, pero pYIN detecta correctamente 62Hz)
    resultados_fft = detectar_pitch_pyin(senal, sr)
    
    # PASO 4: Detectar notas (con filtro de duración mínima de 350 ms para eliminar transitorios intermedios)
    secuencia = detectar_secuencia_notas(resultados_fft, duracion_minima_ms=350)
    
    # PASO 5: Mostrar resultados
    if secuencia:
        imprimir_secuencia(secuencia)
        
        # PASO 6: Exportar JSON
        salida = generar_salida_json(secuencia, nombre_archivo)
        
        # PASO 7: Visualización
        if generar_visualizacion:
            generar_espectrograma(senal, sr, secuencia, nombre_archivo)
        
        tiempo_total = time.time() - inicio
        print(f"\n{'='*60}")
        print(f"  [ÉXITO] PROCESAMIENTO COMPLETO en {tiempo_total:.2f} segundos")
        print(f"  [ÉXITO] Notas detectadas: {len(secuencia)}")
        print(f"  [ÉXITO] JSON listo para la app y el ESP32")
        print(f"{'='*60}\n")
        
        return salida
    else:
        print("\n  [ERROR] No se detectaron notas musicales en el audio.")
        return None


# ============================================================================
# EJECUCIÓN
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Si se pasa un archivo como argumento: python algoritmo.py cancion.wav
        ruta = sys.argv[1]
        procesar_audio(ruta)
    else:
        # Sin argumentos: ejecutar modo demo
        print("\n  Uso: python algoritmo_procesamiento_senales.py [archivo.wav/mp3]")
        print("  Sin archivo -> se ejecuta modo demo con escala musical sintética\n")
        procesar_audio()
