from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import pandas as pd
import io

# Ejecucion del servidor: uvicorn FinanzasApi:app --reload
# Ruta en el navegador para ver el swagger: http://127.0.0.1:8000/docs

app = FastAPI(title="Prueba de Lectura Excel")

@app.post("/test-excel")
async def test_excel(
  ticker: str = Form(...),
  archivo: UploadFile = File(...)
):
  # Verificación básica de extensión
  if not archivo.filename.endswith(('.xlsx', '.xls')):
    raise HTTPException(status_code=400, detail="Por favor, sube un archivo Excel válido.")

  try:
    # 1. Leer el contenido del archivo en memoria
    contenido = await archivo.read()
    
    # 2. Convertir los bytes a un DataFrame de Pandas
    # Usamos io.BytesIO para que Pandas crea que es un archivo físico
    df = pd.read_excel(io.BytesIO(contenido))

    # 3. Intentar buscar la fila de "Diluted EPS" (como en tu script original)
    # Buscamos en la primera columna (índice 0)
    eps_row = df[df.iloc[:, 0].str.contains("Diluted EPS", case=False, na=False)]

    if eps_row.empty:
      return {
        "mensaje": f"Archivo leído correctamente para {ticker}, pero no encontré la fila 'Diluted EPS'.",
        "columnas_detectadas": list(df.columns)
    }

    # 4. Extraer los años y los valores para el JSON
    años = [str(col) for col in eps_row.columns[1:]]
    valores = [float(val) for val in eps_row.iloc[0, 1:]]
    
    # 5. Responder con el JSON
    return {
      "status": "Exito",
      "ticker_recibido": ticker,
      "datos_extraidos": {
          "concepto": "Diluted EPS",
          "lectura": dict(zip(años, valores))
      }
    }

  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error procesando el Excel: {str(e)}")