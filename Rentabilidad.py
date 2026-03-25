import pandas as pd
import yfinance as yf
import numpy as np
import os

# Acepta archivos tanto xls como xlsx

# -------------------------------------------------
# 0️⃣  RUTA DEL EXCEL (SELECTOR INTELIGENTE)
# -------------------------------------------------
# Asegúrate de que el nombre del archivo coincida (summary.xlsx o summary.xls)
#excel_file = "/Users/alfonsomunoz/Desktop/Programacion/Finanzas/Excel_Financiero/Fresh_del_Monte/summary.xlsx"
excel_file = "/Users/alfonsomunoz/Desktop/Programacion/Finanzas/Excel_Financiero/Bungle_Global/summary.xls"

# Detectamos la extensión para elegir el motor adecuado
extension = os.path.splitext(excel_file)[1].lower()

try:
    if extension == '.xlsx':
        df = pd.read_excel(excel_file, engine='openpyxl')
    elif extension == '.xls':
        df = pd.read_excel(excel_file, engine='xlrd')
    else:
        df = pd.read_excel(excel_file) # Intento genérico
    print(f"✅ Archivo {extension} cargado correctamente.")
except Exception as e:
    print(f"❌ Error crítico al cargar el Excel: {e}")
    exit() # Si no hay archivo, no podemos seguir

# -------------------------------------------------
# 1️⃣ EXTRACCIÓN DE DATOS DEL EXCEL
# -------------------------------------------------
years = [int(col) for col in df.columns[1:] if str(col).isdigit()]

def extraer_fila(nombre_busqueda):
    fila = df[df.iloc[:, 0].str.contains(nombre_busqueda, case=False, na=False)]
    if fila.empty:
        return {}
    return {int(year): float(val) for year, val in zip(years, fila.iloc[0, 1:]) if str(year).isdigit()}

eps_dict = extraer_fila("Diluted EPS")
fcf_dict = extraer_fila("Free Cash Flow")
shares_dict = extraer_fila("Shares Outstanding Capital")

# -------------------------------------------------
# 2️⃣ DATOS DE MERCADO EN TIEMPO REAL (YAHOO)
# -------------------------------------------------
ticker_symbol = input("Introduce el ticker (ej. FDP): ").upper()
ticker = yf.Ticker(ticker_symbol)
# Usamos try/except por si ticker.fast_info falla
try:
    precio_actual = ticker.fast_info['last_price']
except:
    precio_actual = ticker.history(period="1d")['Close'].iloc[-1]

price_by_year = {}
for year in years:
    try:
        hist = ticker.history(start=f"{year}-12-25", end=f"{year}-12-31")
        if not hist.empty:
            price_by_year[year] = hist['Close'].iloc[-1]
        else:
            hist = ticker.history(period="max")
            price_by_year[year] = hist[hist.index.year == year]['Close'].iloc[-1]
    except:
        continue

# -------------------------------------------------
# 3️⃣ MÉTODOS DE APOYO Y LÓGICA
# -------------------------------------------------

def calcular_crecimiento_automatico(fcf_datos):
    años = sorted(fcf_datos.keys())
    if len(años) < 2: return 0.02
    
    fcf_inicial = fcf_datos[años[0]]
    fcf_final = fcf_datos[años[-1]]
    n = años[-1] - años[0]
    
    # --- SEGURO ANTI-ERRORES MATEMÁTICOS ---
    # Si empezamos en negativo o terminamos en negativo, la fórmula CAGR falla.
    # En ese caso, usamos un crecimiento estándar del 3% por prudencia.
    if fcf_inicial <= 0 or fcf_final <= 0: 
        return 0.03 
    
    try:
        # Calculamos el crecimiento
        ratio = fcf_final / fcf_inicial
        cagr = (ratio ** (1/n)) - 1
        
        # Si el resultado es un número complejo (ocurre a veces en Python con negativos)
        if isinstance(cagr, complex):
            return 0.02
            
        # Si decrece, ponemos 2%. Si crece mucho, capamos al 15%.
        if cagr < 0: return 0.02
        return min(cagr * 0.75, 0.15)
        
    except:
        # Ante cualquier otro error matemático (división por cero, etc.)
        return 0.02

def calcular_per_terminal(eps_datos, precios_datos):
    per_historicos = [precios_datos[y] / eps_datos[y] for y in eps_datos if y in precios_datos and eps_datos[y] > 0]
    if not per_historicos: return 15
    per_medio = sum(per_historicos) / len(per_historicos)
    return round(per_medio * 0.80)

def ejecutar_modelo_dcf(fcf_inicio, g, per_objetivo, precio_mercado):
    tasa_tir = 0
    # Buscamos la R que iguala el valor intrínseco al precio actual
    for r in np.arange(0.001, 0.50, 0.001):
        fcf_temp = fcf_inicio
        proyectados = []
        v_presentes = []
        for i in range(1, 11):
            fcf_temp *= (1 + g)
            proyectados.append(fcf_temp)
            v_presentes.append(fcf_temp / ((1 + r) ** i))

        suma_vp = sum(v_presentes)
        v_terminal_desc = (proyectados[-1] * per_objetivo) / ((1 + r) ** 10)
        v_intrinseco = suma_vp + v_terminal_desc

        if v_intrinseco <= precio_mercado:
            tasa_tir = r
            break
    return tasa_tir

def ejecutar_modelo_multiplos(bpa_actual, g, per_historico, precio_compra):
    bpa_futuro = bpa_actual * ((1 + g) ** 10)
    precio_futuro = per_historico * bpa_futuro
    rentabilidad_anual = (precio_futuro / precio_compra) ** (1/10) - 1
    return bpa_futuro, precio_futuro, rentabilidad_anual

def mostrar_informe_final(ticker, precio, g, per, rent_dcf, bpa_f, precio_f, rent_m):
    print("\n" + "="*60)
    print(f"       ESTIMACIÓN DE RENTABILIDAD A 10 AÑOS: {ticker}")
    print("="*60)
    print(f"PRECIO MERCADO: {precio:.2f} $ | CRECIMIENTO: {g*100:.2f}% | PER SALIDA: {per}x")
    print("-" * 60)
    print(f"📊 MÉTODO 1 (FLUJOS/DCF): TIR ESTIMADA -> {rent_dcf*100:.2f}%")
    print(f"📈 MÉTODO 2 (BPA/EPS):   RENT. ESTIMADA -> {rent_m*100:.2f}%")
    print("-" * 60)
    rent_media = (rent_dcf + rent_m) / 2
    if rent_media > 0.12:
        print(f"RESULTADO: 🟢 {rent_media*100:.1f}% - MUY ATRACTIVA")
    elif 0.07 <= rent_media <= 0.12:
        print(f"RESULTADO: 🟡 {rent_media*100:.1f}% - NORMAL (MERCADO)")
    else:
        print(f"RESULTADO: 🔴 {rent_media*100:.1f}% - RIESGO/BAJO RETORNO")

# -------------------------------------------------
# 7️⃣ EJECUCIÓN (LÓGICA DE LIMPIEZA)
# -------------------------------------------------

ultimo_año = max(years)
bpa_actual = eps_dict.get(ultimo_año, 0)

# Limpieza de acciones (Igual que en el otro script para evitar ceros)
n_raw = shares_dict.get(ultimo_año, 1)
if n_raw > 1_000_000_000_000:
    n_acciones = n_raw / 1_000_000_000_000_000
elif n_raw < 10000:
    n_acciones = n_raw # Ya viene en millones
else:
    n_acciones = n_raw / 1_000_000 # Normalizamos a millones

# El FCF del Excel suele venir en unidades, así que dividimos por acciones en unidades
fcf_total = fcf_dict.get(ultimo_año, 0)
fcf_por_accion = fcf_total / (n_acciones * 1_000_000)

g_conservador = calcular_crecimiento_automatico(fcf_dict)
per_terminal = calcular_per_terminal(eps_dict, price_by_year)

rent_tir = ejecutar_modelo_dcf(fcf_por_accion, g_conservador, per_terminal, precio_actual)
bpa_f, precio_f, rent_m = ejecutar_modelo_multiplos(bpa_actual, g_conservador, per_terminal, precio_actual)

mostrar_informe_final(ticker_symbol, precio_actual, g_conservador, per_terminal, rent_tir, bpa_f, precio_f, rent_m)