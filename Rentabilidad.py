import pandas as pd
import yfinance as yf
import numpy as np

# -------------------------------------------------
# 0️⃣  RUTA DEL EXCEL
# -------------------------------------------------
excel_file = "/Users/alfonsomunoz/Desktop/Programacion/Python/Finanzas/Excel_Financiero/Fresh_del_Monte/summary.xlsx"

# -------------------------------------------------
# 1️⃣ EXTRACCIÓN DE DATOS DEL EXCEL (MATERIA PRIMA)
# -------------------------------------------------
df = pd.read_excel(excel_file)
years = [int(col) for col in df.columns[1:] if str(col).isdigit()]

def extraer_fila(nombre_busqueda):
    fila = df[df.iloc[:, 0].str.contains(nombre_busqueda, case=False, na=False)]
    if fila.empty:
        return {}
    return {int(year): float(val) for year, val in zip(years, fila.iloc[0, 1:]) if str(year).isdigit()}

# Extraemos las filas necesarias para ambos métodos
eps_dict = extraer_fila("Diluted EPS")          # Para PER y Método 1.8.2
fcf_dict = extraer_fila("Free Cash Flow")        # Para CAGR y Método 1.8.1
shares_dict = extraer_fila("Shares Outstanding Capital") # Para normalizar por acción

# -------------------------------------------------
# 2️⃣ DATOS DE MERCADO EN TIEMPO REAL (YAHOO)
# -------------------------------------------------
ticker_symbol = input("Introduce el ticker (ej. PFE): ").upper()
ticker = yf.Ticker(ticker_symbol)
precio_actual = ticker.fast_info['last_price']

# Obtenemos precios de cierre históricos para calcular PER medio real
price_by_year = {}
for year in years:
    hist = ticker.history(start=f"{year}-12-25", end=f"{year}-12-31")
    if not hist.empty:
        price_by_year[year] = hist['Close'].iloc[-1]
    else:
        hist = ticker.history(period="max")
        price_by_year[year] = hist[hist.index.year == year]['Close'].iloc[-1]

# -------------------------------------------------
# 3️⃣ MÉTODOS DE APOYO: PARÁMETROS CONSERVADORES
# -------------------------------------------------

def calcular_crecimiento_automatico(fcf_datos):
    """Calcula CAGR. Si es negativo o incoherente, usa 2% (media mercado)"""
    años = sorted(fcf_datos.keys())
    fcf_inicial = fcf_datos[años[0]]
    fcf_final = fcf_datos[años[-1]]
    n = años[-1] - años[0]
    
    # Evitar errores si el FCF inicial es 0 o negativo
    if fcf_inicial <= 0: return 0.03 
    
    cagr = (fcf_final / fcf_inicial) ** (1/n) - 1
    
    # Si la empresa decrece, para el modelo futuro asumimos al menos 
    # que mantiene valor (inflación 2%), si crece mucho, capamos a 15% (conservador)
    if cagr < 0: return 0.02
    return min(cagr * 0.75, 0.15)

def calcular_per_terminal(eps_datos, precios_datos):
    """Calcula el PER medio histórico y aplica el factor de seguridad del 80%"""
    per_historicos = [precios_datos[y] / eps_datos[y] for y in eps_datos if y in precios_datos and eps_datos[y] > 0]
    if not per_historicos: return 15
    per_medio = sum(per_historicos) / len(per_historicos)
    return round(per_medio * 0.80)

# -------------------------------------------------
# 4️⃣ MODO 1.8.1: ESTIMACIÓN RENTABILIDAD DCF (FLUJOS)
# -------------------------------------------------

def ejecutar_modelo_dcf(fcf_inicio, g, per_objetivo, precio_mercado):
    """Calcula la Tasa Interna de Retorno (IRR) mediante flujos descontados"""
    tasa_tir = 0
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

# -------------------------------------------------
# 5️⃣ MODO 1.8.2: ESTIMACIÓN RENTABILIDAD POR MÚLTIPLOS
# -------------------------------------------------

def ejecutar_modelo_multiplos(bpa_actual, g, per_historico, precio_compra):
    """Calcula la rentabilidad basada en el crecimiento del BPA y múltiplo final"""
    bpa_futuro = bpa_actual * ((1 + g) ** 10)
    precio_futuro = per_historico * bpa_futuro
    rentabilidad_anual = (precio_futuro / precio_compra) ** (1/10) - 1
    return bpa_futuro, precio_futuro, rentabilidad_anual

# -------------------------------------------------
# 6️⃣ FUNCIONES DE IMPRESIÓN DE RESULTADOS
# -------------------------------------------------

def mostrar_informe_final(ticker, precio, g, per, rent_dcf, bpa_f, precio_f, rent_m):
    print("\n" + "*"*60)
    print(f"       INFORME DE RENTABILIDAD PROYECTADA (10 AÑOS): {ticker}")
    print("*"*60)
    print(f"PRECIO ACTUAL: {precio:.2f} $ | CRECIMIENTO EST.: {g*100:.2f}% | PER OBJ.: {per}x")
    print("-" * 60)

    # Resultados 1.8.1
    print(f"📊 1.8.1 MÉTODO DCF (FLUJO DE CAJA):")
    print(f"   >>> RENTABILIDAD ANUAL ESPERADA (TIR): {rent_dcf*100:.2f}%")

    # Resultados 1.8.2
    print(f"\n📈 1.8.2 MÉTODO MÚLTIPLOS (BPA):")
    print(f"   >>> BPA Estimado Año 10:    {bpa_f:.2f} $")
    print(f"   >>> Precio Estimado Año 10: {precio_f:.2f} $")
    print(f"   >>> RENTABILIDAD ANUAL ESTIMADA:      {rent_m*100:.2f}%")
    print("-" * 60)

    # Conclusión final comparativa
    rent_media = (rent_dcf + rent_m) / 2
    if rent_media > 0.12:
        print("CONCLUSIÓN: 🟢 EXCELENTE. Ambas métricas sugieren infravaloración.")
    elif 0.07 <= rent_media <= 0.12:
        print("CONCLUSIÓN: 🟡 ACEPTABLE. Rentabilidad esperada acorde al mercado.")
    else:
        print("CONCLUSIÓN: 🔴 RIESGO. El precio actual ofrece poco margen de retorno.")

# -------------------------------------------------
# 7️⃣ EJECUCIÓN DEL PROGRAMA (RESTURADO A 5 PUNTOS)
# -------------------------------------------------

# 1. Preparar datos base del año más reciente
ultimo_año = max(years)
bpa_actual = eps_dict[ultimo_año]

# --- DETECCIÓN AUTOMÁTICA DE ESCALA DE ACCIONES ---
acciones_raw = shares_dict[ultimo_año]
if acciones_raw > 1_000_000_000_000:  # Si tiene demasiados ceros (como tu Excel)
    while acciones_raw > 1_000_000_000:
        acciones_raw /= 1000
    acciones_ajustadas = acciones_raw
else:
    acciones_ajustadas = acciones_raw / 1_000_000_000 # Escala estándar

fcf_por_accion = fcf_dict[ultimo_año] / acciones_ajustadas

# 2. Obtener parámetros conservadores (Dinámicos)
# Usamos la nueva función calcular_crecimiento_automatico que definimos antes
g_conservador = calcular_crecimiento_automatico(fcf_dict)
per_terminal = calcular_per_terminal(eps_dict, price_by_year)

# 3. Calcular Rentabilidad 1.8.1 (DCF)
rent_tir = ejecutar_modelo_dcf(fcf_por_accion, g_conservador, per_terminal, precio_actual)

# 4. Calcular Rentabilidad 1.8.2 (Múltiplos)
bpa_f, precio_f, rent_m = ejecutar_modelo_multiplos(bpa_actual, g_conservador, per_terminal, precio_actual)

# 5. Imprimir Informe
mostrar_informe_final(ticker_symbol, precio_actual, g_conservador, per_terminal, rent_tir, bpa_f, precio_f, rent_m)
