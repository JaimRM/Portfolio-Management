# -*- coding: utf-8 -*-
import logging
import httpx
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.status import HTTP_401_UNAUTHORIZED

# --- 1. CONFIGURACIÓN DEL SISTEMA DE AUDITORÍA (LOGGING) ---
logging.basicConfig(
    filename='auditoria_tesoreria.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = FastAPI(
    title="Asynchronous, Secure Real-Time Price API",
    description="API segura conectada en tiempo real a Financial Modeling Prep Database."
)

# --- 2. CONFIGURACIÓN DE SEGURIDAD ---
security_scheme = HTTPBearer()
TOKEN_SECRETO_INTERNO = "SherlockHolmes18"


async def verificar_token(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)):
    if credentials.credentials == TOKEN_SECRETO_INTERNO:
        return credentials.credentials

    # AUDITORÍA: Intento de acceso no autorizado
    logging.warning(
        "ALERTA DE SEGURIDAD: Intento de acceso denegado con token incorrecto o ausente.")
    raise HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Token de seguridad inválido o ausente. Acceso denegado."
    )

# --- 3. CONFIGURACIÓN DE CREDENCIALES ---
FMP_API_KEY = "xi7IGuHipNB4H6FuWcctxKy1GbOLg9R5"

# --- 4. ENDPOINT REAL-TIME PRECIO ---


@app.get("/precio-real/{ticker}")
async def obtener_precio_fmp(ticker: str, token: str = Depends(verificar_token)):
    ticker_upper = ticker.upper()

    # Endpoint de la API FMP (v3 sustituido por la ruta moderna /stable/)
    url_fmp = "https://financialmodelingprep.com/stable/quote"
    params = {
        "symbol": ticker_upper,
        "apikey": FMP_API_KEY
    }

    try:
        # Petición asíncrona no bloqueante
        async with httpx.AsyncClient() as client:
            respuesta = await client.get(url_fmp, params=params, timeout=10.0)

        if respuesta.status_code != 200:
            logging.error(
                f"FALLO DE RESPUESTA FMP: Código de estado {respuesta.status_code} para '{ticker_upper}'.")
            raise HTTPException(
                status_code=respuesta.status_code,
                detail="Error en la respuesta del proveedor externo."
            )

        datos = respuesta.json()

        # Validación: FMP devuelve un diccionario con "Error Message" o una lista vacía si falla
        if isinstance(datos, dict) and "Error Message" in datos:
            error_msg = datos.get("Error Message")
            logging.error(f"ERROR DE API FMP: {error_msg}")
            raise HTTPException(
                status_code=400, detail=f"Error retornado por FMP: {error_msg}")

        if not datos or not isinstance(datos, list):
            logging.warning(
                f"CONSULTA FALLIDA: No se encontraron datos para el activo '{ticker_upper}'.")
            raise HTTPException(
                status_code=404, detail=f"No se encontraron datos válidos para '{ticker_upper}'.")

        # Extraer primer elemento de la respuesta
        info_activo = datos[0]

        logging.info(
            f"CONSULTA FMP EXITOSA: Se sirvió el precio en tiempo real de {ticker_upper}.")

        return {
            "activo": info_activo.get("symbol"),
            "nombre_empresa": info_activo.get("name"),
            "precio_mercado": info_activo.get("price"),
            "cambio_porcentual": info_activo.get("changePercentage"),
            "volumen_diario": info_activo.get("volume"),
            "estado_seguridad": "Conexión Cifrada y Verificada con Token Bearer",
            "fuente_origen": "Financial Modeling Prep API (Stable Route)"
        }

    except httpx.RequestError as exc:
        logging.critical(
            f"FALLO DE INFRAESTRUCTURA DE RED: Error al conectar con FMP. Detalles: {exc}")
        raise HTTPException(
            status_code=503, detail="Error de infraestructura de red externa")
    except Exception as e:
        logging.error(f"ERROR INTERNO: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}")

# --- 5. EJECUCIÓN DIRECTA DEL SERVIDOR ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("pricefeed:app", host="127.0.0.1", port=8000, reload=True)
