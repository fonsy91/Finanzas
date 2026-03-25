import pandas as pd
import yfinance as yf
import os

# Ejecucion: python3 <nombre_archivo>
# Acepta archivos tanto xls como xlsx

# -------------------------------------------------
# 1️⃣ PEDIR TICKER AL USUARIO
# -------------------------------------------------
ticker_symbol = input("Introduce el ticker de la acción (por ejemplo PFE): ").upper()

print("\nSelecciona el sector de la empresa para ajustar la valoración:")
sectores = {
    '1': 'Tecnología/Software',
    '2': 'Farmacéutica/Biotecnología',
    '3': 'Logística y Transporte',
    '4': 'Retail/Comercio',
    '5': 'Manufactura/Industria',
    '6': 'Energía/Utilities',
    '7': 'Banca/Finanzas',
    '8': 'Alimentación/Bebidas',
    '9': 'Automoción',
    '10': 'Minería y Materiales',
    '11': 'Infraestructura y Construcción',
    '12': 'Telecomunicaciones'
}

for k, v in sectores.items():
    print(f"{k}. {v}")

sector_usuario = input("\nIntroduce el número del sector (1-12): ")

# -------------------------------------------------
# 2️⃣ RUTA DEL EXCEL
# -------------------------------------------------
excel_file = "/Users/alfonsomunoz/Desktop/Programacion/Finanzas/Excel_Financiero/Fresh_del_Monte/summary.xlsx"
#excel_file = "/Users/alfonsomunoz/Desktop/Programacion/Finanzas/Excel_Financiero/Bungle_Global/summary.xls"

# -------------------------------------------------
# 3️⃣ LEER EXCEL Y EXTRAER FILAS NECESARIAS
# -------------------------------------------------
extension = os.path.splitext(excel_file)[1].lower()

try:
    if extension == '.xlsx':
        # Para archivos modernos
        df = pd.read_excel(excel_file, engine='openpyxl')
    else:
        # Para archivos antiguos de Morningstar (.xls)
        df = pd.read_excel(excel_file, engine='xlrd')
    print(f"✅ Archivo {extension} cargado correctamente.")
except Exception as e:
    print(f"❌ Error al cargar el Excel: {e}")
    # Intento desesperado sin motor específico por si acaso
    df = pd.read_excel(excel_file)

# Filas necesarias para 1.2.1 Valoración utilizando el ratio PER o P/E (precio de una acción).
# EPS Diluted
eps_row = df[df.iloc[:, 0].str.contains("Diluted EPS", case=False)]
if eps_row.empty:
    raise ValueError("No se encontró la fila 'Diluted EPS' en el Excel.")
years = eps_row.columns[1:]
eps_values = eps_row.iloc[0, 1:]
eps_dict = {int(year): float(val) for year, val in zip(years, eps_values) if str(year).isdigit()}

# Filas necesarias para 1.2.2 Valoración utilizando el ratio P/FCF(Ratio precio a Free cash flow)
# Free Cash Flow
fcf_row = df[df.iloc[:, 0].str.contains("Free Cash Flow", case=False)]
if fcf_row.empty:
    raise ValueError("No se encontró la fila 'Free Cash Flow' en el Excel.")
fcf_values = fcf_row.iloc[0, 1:]
fcf_dict = {int(year): float(val) for year, val in zip(years, fcf_values) if str(year).isdigit()}

# Shares Outstanding Capital
shares_row = df[df.iloc[:, 0].str.contains("Shares Outstanding Capital", case=False)]
if shares_row.empty:
    raise ValueError("No se encontró la fila 'Shares Outstanding Capital' en el Excel.")
shares_values = shares_row.iloc[0, 1:]
shares_dict = {int(year): float(val) for year, val in zip(years, shares_values) if str(year).isdigit()}

# Filas necesarias para 1.2.3 Valoración utilizando el ratio PB(Price-to-Book)
# Activos Totales
assets_row = df[df.iloc[:, 0].str.contains("Total Assets", case=False, na=False)]
assets_dict = {int(year): float(val) for year, val in zip(years, assets_row.iloc[0, 1:]) if str(year).isdigit()} if not assets_row.empty else {}
# Pasivos Totales
liabilities_row = df[df.iloc[:, 0].str.contains("Total Liabilities", case=False, na=False)]
liabilities_dict = {int(year): float(val) for year, val in zip(years, liabilities_row.iloc[0, 1:]) if str(year).isdigit()} if not liabilities_row.empty else {}
# Capital Contable (Total Equity) - Lo extraemos como respaldo
equity_row = df[df.iloc[:, 0].str.contains("Total Equity", case=False, na=False)]
equity_dict = {int(year): float(val) for year, val in zip(years, equity_row.iloc[0, 1:]) if str(year).isdigit()} if not equity_row.empty else {}

# Filas necesarias para 1.2.4 Valoración utilizando el ratio PS(Precio a ventas)(Price-sales ratio)
revenue_row = df[df.iloc[:, 0].str.contains("^Revenue$", case=False, na=False)]
if revenue_row.empty:
    # Intenta con "Total Revenue" si "Revenue" a secas no aparece
    revenue_row = df[df.iloc[:, 0].str.contains("Total Revenue", case=False, na=False)]

revenue_values = revenue_row.iloc[0, 1:]
revenue_dict = {int(year): float(val) for year, val in zip(years, revenue_values) if str(year).isdigit()}

# Filas necesarias para 1.2.5 Valoración utilizando el ratio EV/EBIT
# EBIT (Operating Income o EBIT según tu Excel)
ebit_row = df[df.iloc[:, 0].str.contains("^EBIT$", case=False, na=False)]
ebit_dict = {int(year): float(val) for year, val in zip(years, ebit_row.iloc[0, 1:]) if str(year).isdigit()}

# Deuda Total
debt_row = df[df.iloc[:, 0].str.contains("Total Debt", case=False, na=False)]
debt_dict = {int(year): float(val) for year, val in zip(years, debt_row.iloc[0, 1:]) if str(year).isdigit()}

# Liquidez (Cash And Cash Equivalents)
cash_row = df[df.iloc[:, 0].str.contains("Cash And Cash Equivalents", case=False, na=False)]
cash_dict = {int(year): float(val) for year, val in zip(years, cash_row.iloc[0, 1:]) if str(year).isdigit()}

# -------------------------------------------------
# 4️⃣ DESCARGAR PRECIOS HISTÓRICOS
# -------------------------------------------------
ticker = yf.Ticker(ticker_symbol)
hist = ticker.history(period="max")
price_by_year = hist["Close"].resample("YE").last()
price_by_year.index = price_by_year.index.year
price_by_year = price_by_year.to_dict()
precio_actual = hist["Close"].iloc[-1]

# -------------------------------------------------
# 5️⃣ CALCULAR FCF POR ACCIÓN
# -------------------------------------------------
fcf_per_share = {}
eps_per_share = {}
bvps_per_share = {}
sales_per_share = {}
ev_ebit_by_year = {}

for year in shares_dict:
    # --- LIMPIEZA DE ACCIONES (Basura e+17) ---
    n_raw = shares_dict[year]
    if n_raw > 1_000_000_000_000: 
        n_acciones = n_raw / 1_000_000_000_000_000 
    elif n_raw < 10000:
        n_acciones = n_raw * 1_000_000 
    else:
        n_acciones = n_raw

    if n_acciones == 0: continue

    # 1. EPS
    if year in eps_dict:
        eps_per_share[year] = eps_dict[year]

    # 2. Ratios por acción (Normalizados)
    n_divisor = n_acciones if n_acciones > 1000 else n_acciones * 1_000_000
    
    if year in fcf_dict:
        fcf_per_share[year] = fcf_dict[year] / n_divisor
    if year in revenue_dict:
        sales_per_share[year] = revenue_dict[year] / n_divisor
    if year in assets_dict and year in liabilities_dict:
        bvps_per_share[year] = (assets_dict[year] - liabilities_dict[year]) / n_divisor

    # 3. EV/EBIT
    if year in debt_dict and year in cash_dict and year in price_by_year:
        cap_mercado = price_by_year[year] * n_divisor
        deuda_neta = debt_dict[year] - cash_dict[year]
        ev = cap_mercado + deuda_neta
        if ebit_dict.get(year, 0) > 0:
            ev_ebit_by_year[year] = ev / ebit_dict[year]

# --- VARIABLES GLOBALES (Lógica Inteligente) ---
ultimo_k = max(shares_dict.keys())

# EPS, BVPS y Ventas usamos el último (suelen ser estables)
eps_actual = eps_per_share.get(ultimo_k, 0)
bvps_actual = bvps_per_share.get(ultimo_k, 0)
sales_actual = sales_per_share.get(ultimo_k, 0)
ebit_actual = ebit_dict.get(ultimo_k, 0)
deuda_neta_actual = debt_dict.get(ultimo_k, 0) - cash_dict.get(ultimo_k, 0)

# FCF ACTUAL: Si es negativo, usamos la media de los años positivos
if fcf_per_share.get(ultimo_k, 0) <= 0:
    fcf_pos = [v for v in fcf_per_share.values() if v > 0]
    fcf_actual = sum(fcf_pos) / len(fcf_pos) if fcf_pos else 0
else:
    fcf_actual = fcf_per_share.get(ultimo_k, 0)

# -------------------------------------------------
# 5️⃣.2️⃣ CÁLCULO ESPECÍFICO PARA PB (VALOR CONTABLE)
# -------------------------------------------------
bvps_per_share = {}
for year in assets_dict:
    if year in liabilities_dict and year in shares_dict:
        acciones_reales = shares_dict[year] / 1_000_000_000_000_000
        n_acciones = acciones_reales * 1_000_000
        bvps_per_share[year] = (assets_dict[year] - liabilities_dict[year]) / n_acciones

if bvps_per_share:
    bvps_actual = list(bvps_per_share.values())[-1]
else:
    bvps_actual = 0

# -------------------------------------------------
# 5️⃣.3️⃣ CÁLCULO ESPECÍFICO PARA PS (VENTAS POR ACCIÓN)
# -------------------------------------------------
sales_per_share = {}
for year in revenue_dict:
    if year in shares_dict:
        acciones_reales = shares_dict[year] / 1_000_000_000_000_000
        n_acciones = acciones_reales * 1_000_000
        sales_per_share[year] = revenue_dict[year] / n_acciones

if sales_per_share:
    sales_actual = list(sales_per_share.values())[-1]
else:
    sales_actual = 0

# -------------------------------------------------
# 5️⃣.4️⃣ CÁLCULO ESPECÍFICO PARA EV/EBIT
# -------------------------------------------------
ev_ebit_by_year = {}
for year in ebit_dict:
    if year in debt_dict and year in cash_dict and year in price_by_year and year in shares_dict:
        acciones_reales = shares_dict[year] / 1_000_000_000_000_000
        n_acciones = acciones_reales * 1_000_000
        
        cap_mercado = price_by_year[year] * n_acciones
        deuda_neta = debt_dict[year] - cash_dict[year]
        ev = cap_mercado + deuda_neta
        if ebit_dict[year] > 0:
            ev_ebit_by_year[year] = ev / ebit_dict[year]

# Mantenemos tus nombres originales para que la función final los lea
ultimo_key = max(ebit_dict.keys())
ebit_actual = ebit_dict[ultimo_key]
deuda_neta_actual = debt_dict[ultimo_key] - cash_dict[ultimo_key]


# ---------------------METODOS DE CADA ESTIMACION -----------------------
# -------------------------------------------------
# 6️⃣ MÉTODO VALORACIÓN PER
# -------------------------------------------------
def valoracion_per():
    per_by_year = {}
    # CAMBIO AQUÍ: Usamos eps_per_share en lugar de eps_dict
    for year, eps in eps_per_share.items():
        if year in price_by_year and eps > 0:
            per_by_year[year] = price_by_year[year] / eps

    # El resto de la función se queda exactamente IGUAL
    per_positivos = [v for v in per_by_year.values() if v > 0]
    per_promedio = sum(per_positivos) / len(per_positivos) if per_positivos else 0
    precio_teorico = per_promedio * eps_actual

    if precio_actual > precio_teorico:
        valoracion = "Acción ligeramente SOBREVALORADA"
    elif precio_actual < precio_teorico:
        valoracion = "Acción INFRAVALORADA"
    else:
        valoracion = "Acción correctamente valorada"

    # SALIDA
    print("\n" + "="*50)
    print(f"📊 VALORACIÓN DE {ticker_symbol} — PER")
    print("="*50)
    print("\nEPS histórico (Diluted EPS):")
    print("Año   | EPS")
    print("-"*25)
    for year, eps in eps_dict.items():
        print(f"{year:<5} | {eps}")

    print("\nPER anual:")
    print("Año   | PER (Precio / EPS)")
    print("-"*30)
    for year, per in per_by_year.items():
        if year in price_by_year:
            print(f"{year:<5} | {per:.2f} (Precio cierre / EPS = {price_by_year[year]:.2f} / {eps_dict[year]:.2f})")

    print(f"\nPER histórico promedio: {per_promedio:.2f}  (Fórmula: ΣPER_anual / n)")
    print(f"EPS usado para valoración: {eps_actual}  (Fórmula: EPS del año a valorar)")
    print(f"Precio teórico actual: {precio_teorico:.2f} $  (Fórmula: Precio-teórico = PER_promedio * EPS_proyectado)")
    print(f"Precio actual de mercado: {precio_actual:.2f} $\n")
    print(f"➡ VALORACIÓN FINAL: {valoracion}")

    return precio_teorico

# -------------------------------------------------
# 7️⃣ MÉTODO VALORACIÓN P/FCF
# -------------------------------------------------
def valoracion_pfcf():
    pfcf_by_year = {}
    for year, fcf in fcf_per_share.items():
        if year in price_by_year and fcf != 0:
            pfcf_by_year[year] = price_by_year[year] / fcf

    # Solo promediamos los años con flujo de caja positivo (P/FCF > 0)
    pfcf_positivos = [v for v in pfcf_by_year.values() if v > 0]
    pfcf_promedio = sum(pfcf_positivos) / len(pfcf_positivos) if pfcf_positivos else 0
    precio_teorico = pfcf_promedio * fcf_actual

    if precio_actual > precio_teorico:
        valoracion = "Acción ligeramente SOBREVALORADA"
    elif precio_actual < precio_teorico:
        valoracion = "Acción INFRAVALORADA"
    else:
        valoracion = "Acción correctamente valorada"

    # SALIDA
    print("\n" + "="*50)
    print(f"📊 VALORACIÓN DE {ticker_symbol} — P/FCF")
    print("="*50)
    print("\nFCF por acción (FCF / Nº acciones):")
    print("Año   | FCF por acción")
    print("-"*30)
    for year, fcf in fcf_per_share.items():
        print(f"{year:<5} | {fcf:.2f}")

    print("\nP/FCF anual:")
    print("Año   | P/FCF (Precio / FCF por acción)")
    print("-"*40)
    for year, pfcf in pfcf_by_year.items():
        print(f"{year:<5} | {pfcf:.2f} (Precio cierre / FCF por acción = {price_by_year[year]:.2f} / {fcf_per_share[year]:.2f})")

    print(f"\nP/FCF histórico promedio: {pfcf_promedio:.2f}  (Fórmula: ΣP/FCF anual / n)")
    print(f"FCF por acción usado para valoración: {fcf_actual:.2f}  (Fórmula: último FCF por acción)")
    print(f"Precio teórico actual: {precio_teorico:.2f} $  (Fórmula: Precio-teórico = P/FCF_promedio * FCF_actual)")
    print(f"Precio actual de mercado: {precio_actual:.2f} $\n")
    print(f"➡ VALORACIÓN FINAL: {valoracion}")

    return precio_teorico

# -------------------------------------------------
# 8️⃣ MÉTODO VALORACIÓN PB (Price-to-Book)
# -------------------------------------------------
def valoracion_pb(bvps_per_share, bvps_actual):
    pb_by_year = {}
    for year, bvps in bvps_per_share.items():
        if year in price_by_year and bvps > 0:
            pb_by_year[year] = price_by_year[year] / bvps

    if not pb_by_year:
        print("\nNo hay datos suficientes para calcular el PB histórico.")
        return

    # Solo promediamos los años con Valor Contable positivo (PB > 0)
    pb_positivos = [v for v in pb_by_year.values() if v > 0]
    pb_promedio = sum(pb_positivos) / len(pb_positivos) if pb_positivos else 0
    precio_teorico = pb_promedio * bvps_actual

    if precio_actual > precio_teorico:
        valoracion = "Acción SOBREVALORADA"
    elif precio_actual < precio_teorico:
        valoracion = "Acción INFRAVALORADA"
    else:
        valoracion = "Acción correctamente valorada"

    # SALIDA
    print("\n" + "="*50)
    print(f"📊 VALORACIÓN DE {ticker_symbol} — P/B (Price-to-Book)")
    print("="*50)

    print("\nValor Contable histórico (BVPS):")
    print("Año   | BVPS ((Assets - Liabilities) / Shares)")
    print("-" * 45)
    for year, bvps in bvps_per_share.items():
        print(f"{year:<5} | {bvps:.2f}")

    print("\nP/B anual:")
    print("Año   | P/B (Precio / Valor Contable)")
    print("-" * 40)
    for year, pb in pb_by_year.items():
        print(f"{year:<5} | {pb:.2f} (Precio: {price_by_year[year]:.2f} / BVPS: {bvps_per_share[year]:.2f})")

    print(f"\nP/B histórico promedio: {pb_promedio:.2f}")
    print(f"BVPS usado para valoración: {bvps_actual:.2f}")
    print(f"Precio teórico actual: {precio_teorico:.2f} $")
    print(f"Precio actual de mercado: {precio_actual:.2f} $\n")
    print(f"➡ VALORACIÓN FINAL: {valoracion}")

    return precio_teorico

# -------------------------------------------------
# 9️⃣ MÉTODO VALORACIÓN PS (Price-to-Sales)
# -------------------------------------------------
def valoracion_ps(sales_per_share, sales_actual):
    ps_by_year = {}
    for year, sales in sales_per_share.items():
        if year in price_by_year and sales > 0:
            ps_by_year[year] = price_by_year[year] / sales

    if not ps_by_year:
        print("\nNo hay datos suficientes para calcular el PS histórico.")
        return

    # Solo promediamos los años con ventas positivas (PS > 0)
    ps_positivos = [v for v in ps_by_year.values() if v > 0]
    ps_promedio = sum(ps_positivos) / len(ps_positivos) if ps_positivos else 0
    precio_teorico = ps_promedio * sales_actual

    # Mensajes unificados con tus otros métodos
    if precio_actual > precio_teorico:
        valoracion = "Acción SOBREVALORADA"
    elif precio_actual < precio_teorico:
        valoracion = "Acción INFRAVALORADA"
    else:
        valoracion = "Acción correctamente valorada"

    # SALIDA
    print("\n" + "="*50)
    print(f"📊 1.2.4 VALORACIÓN DE {ticker_symbol} — P/S")
    print("="*50)

    print("\nVentas por Acción histórico (Revenue Per Share):")
    print("Año   | Ventas")
    print("-" * 25)
    for year, sales in sales_per_share.items():
        print(f"{year:<5} | {sales:.2f}")

    print("\nP/S anual:")
    print("Año   | P/S (Precio / Ventas por Acción)")
    print("-" * 45)
    for year, ps in ps_by_year.items():
        print(f"{year:<5} | {ps:.2f} (Precio: {price_by_year[year]:.2f} / Ventas: {sales_per_share[year]:.2f})")

    print(f"\nP/S histórico promedio: {ps_promedio:.2f}")
    print(f"Ventas por acción actual (TTM): {sales_actual:.2f} $")
    print(f"Precio teórico actual: {precio_teorico:.2f} $")
    print(f"Precio actual de mercado: {precio_actual:.2f} $\n")
    print(f"➡ VALORACIÓN FINAL: {valoracion}")

    return precio_teorico

# -------------------------------------------------
# 🔟 MÉTODO VALORACIÓN EV/EBIT
# -------------------------------------------------
def valoracion_ev_ebit(ev_ebit_by_year, ebit_actual, deuda_neta_actual):
    if not ev_ebit_by_year:
        print("\nNo hay datos suficientes para calcular el EV/EBIT.")
        return

    # Cálculos para la valoración
    acciones_ajustadas = list(shares_dict.values())[-1] / 1_000_000_000
    # Solo promediamos los años con EBIT positivo
    ev_positivos = [v for v in ev_ebit_by_year.values() if v > 0]
    ev_ebit_promedio = sum(ev_positivos) / len(ev_positivos) if ev_positivos else 0

    # Precio teórico: despejamos de la fórmula EV
    # Precio = ((Ratio_Promedio * EBIT) - Deuda_Neta) / Acciones
    precio_teorico = ((ev_ebit_promedio * ebit_actual) - deuda_neta_actual) / acciones_ajustadas

    # Lógica de valoración coherente (Prioriza el Precio sobre el Rango)
    if precio_actual < precio_teorico:
        valoracion = "Acción INFRAVALORADA"
    elif precio_actual > precio_teorico:
        valoracion = "Acción SOBREVALORADA"
    else:
        valoracion = "Acción correctamente valorada"

    # SALIDA CON FORMATO IGUAL A LOS DEMÁS
    print("\n" + "="*50)
    print(f"📊 VALORACIÓN DE {ticker_symbol} — EV/EBIT")
    print("="*50)

    print("\nEBIT histórico:")
    print("Año   | EBIT (Operating Income)")
    print("-" * 30)
    for year, ebit in ebit_dict.items():
        print(f"{year:<5} | {ebit:.2f}")

    print("\nEV/EBIT anual:")
    print("Año   | EV/EBIT (EV / EBIT)")
    print("-" * 40)
    for year, ratio in ev_ebit_by_year.items():
        print(f"{year:<5} | {ratio:.2f}")

    print(f"\nEV/EBIT histórico promedio: {ev_ebit_promedio:.2f} (ΣRatio / n)")
    print(f"EBIT usado para valoración: {ebit_actual:.2f} (Último EBIT)")
    print(f"Deuda Neta actual:         {deuda_neta_actual:.2f} (Deuda - Cash)")

    print(f"\nPrecio teórico actual: {precio_teorico:.2f} $")
    print(f"Fórmula: ((EV/EBIT_prom * EBIT) - Deuda_Neta) / Acciones")

    print(f"Precio actual de mercado: {precio_actual:.2f} $")
    print(f"\n➡ VALORACIÓN FINAL: {valoracion}")

    return precio_teorico

# -------------------------------------------------
# 1️⃣1️⃣ RESUMEN FINAL DE CONFLUENCIA
# -------------------------------------------------
def imprimir_resumen_final(p1, p2, p3, p4, p5, sector_elegido):
    # Configuración de Pesos por Sector
    # Orden de la lista de pesos: [PER, P/FCF, P/B, P/S, EV/EBIT]
    config_sectores = {
        '1': ([0.30, 0.25, 0.05, 0.30, 0.10], "Foco: Crecimiento y Ventas"), # Tecnología
        '2': ([0.35, 0.20, 0.10, 0.25, 0.10], "Foco: I+D y Patentes (Beneficios)"), # Farmacéutica
        '3': ([0.15, 0.25, 0.10, 0.10, 0.40], "Foco: Flujo de Caja y Deuda Operativa"), # Logística
        '4': ([0.25, 0.25, 0.10, 0.25, 0.15], "Foco: Rotación de Inventario y Ventas"), # Retail
        '5': ([0.20, 0.20, 0.15, 0.10, 0.35], "Foco: Activos Fijos y Margen Operativo"), # Manufactura
        '6': ([0.10, 0.20, 0.20, 0.10, 0.40], "Foco: Infraestructura y Deuda Pesada"), # Energía
        '7': ([0.40, 0.05, 0.45, 0.05, 0.05], "Foco: Capital Contable y Beneficio Neto"), # Banca
        '8': ([0.25, 0.35, 0.10, 0.10, 0.20], "Foco: Generación de Caja Consistente"), # Alimentación
        '9': ([0.20, 0.20, 0.20, 0.10, 0.30], "Foco: Ciclo Económico y Deuda"), # Automoción
        '10': ([0.15, 0.20, 0.35, 0.10, 0.20], "Foco: Valor de Reservas y Activos"), # Minería
        '11': ([0.20, 0.20, 0.15, 0.10, 0.35], "Foco: Proyectos a Largo Plazo y EV"), # Construcción
        '12': ([0.20, 0.30, 0.10, 0.10, 0.30], "Foco: Dividendos y EBITDA") # Telecom
    }

    pesos, razon = config_sectores.get(sector_elegido, ([0.2, 0.2, 0.2, 0.2, 0.2], "Ponderación Equitativa"))

    # Cálculo de Precio Medio Ponderado (solo precios > 0)
    precios = [p1, p2, p3, p4, p5]
    precio_final = 0
    peso_total_usado = 0

    for i, p in enumerate(precios):
        if p and p > 0:
            precio_final += p * pesos[i]
            peso_total_usado += pesos[i]

    if peso_total_usado > 0:
        precio_final = precio_final / peso_total_usado

    upside = ((precio_final / precio_actual) - 1) * 100

    print("\n" + "*"*60)
    print(f"🏆 RESUMEN INTELIGENTE SECTORIAL: {ticker_symbol}")
    print(f"📌 Estrategia: {razon}")
    print("*"*60)
    print(f"1. Valor por PER (Peso {pesos[0]*100:.0f}%):    {p1 if p1 and p1>0 else 0:>8.2f} $")
    print(f"2. Valor por P/FCF (Peso {pesos[1]*100:.0f}%):  {p2 if p2 and p2>0 else 0:>8.2f} $")
    print(f"3. Valor por P/B (Peso {pesos[2]*100:.0f}%):    {p3 if p3 and p3>0 else 0:>8.2f} $")
    print(f"4. Valor por P/S (Peso {pesos[3]*100:.0f}%):    {p4 if p4 and p4>0 else 0:>8.2f} $")
    print(f"5. Valor por EV/EBIT (Peso {pesos[4]*100:.0f}%):{p5 if p5 and p5>0 else 0:>8.2f} $")
    print("-" * 60)
    print(f"🎯 PRECIO OBJETIVO PONDERADO: {precio_final:.2f} $")
    print(f"💸 PRECIO ACTUAL MERCADO:    {precio_actual:.2f} $")
    print(f"📊 POTENCIAL DE REVALORIZACIÓN: {upside:.2f} %")
    print("-" * 60)

    if upside > 15:
        print("CONCLUSIÓN: 🟢 OPORTUNIDAD - Precio por debajo del valor sectorial.")
    elif -5 < upside <= 15:
        print("CONCLUSIÓN: 🟡 NEUTRAL - Cotizando en valor de mercado.")
    else:
        print("CONCLUSIÓN: 🔴 SOBREVALORADA - Riesgo de caída.")

# -------------------------------------------------
# 8️⃣ LLAMADAS A LOS MÉTODOS
# -------------------------------------------------
res_per = valoracion_per()
res_fcf = valoracion_pfcf()
res_pb  = valoracion_pb(bvps_per_share, bvps_actual)
res_ps  = valoracion_ps(sales_per_share, sales_actual)
res_ev  = valoracion_ev_ebit(ev_ebit_by_year, ebit_actual, deuda_neta_actual)

# Pasamos todos los resultados + el sector elegido
imprimir_resumen_final(res_per, res_fcf, res_pb, res_ps, res_ev, sector_usuario)