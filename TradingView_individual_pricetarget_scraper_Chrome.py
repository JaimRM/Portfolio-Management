!pip install selenium pandas webdriver_manager
!apt-get update
!apt-get install chromium-browser -y

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd

# Configuración del navegador (modo invisible con Chrome)
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920,1080')
options.add_argument('--disable-extensions')
options.add_argument('--disable-features=NetworkService')
options.add_argument('--disable-setuid-sandbox')
options.add_argument('--remote-debugging-port=9222')
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument('--incognito')
options.binary_location = '/usr/bin/chromium-browser'

# Configurar el servicio de Chrome con webdriver_manager
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

url = "https://www.tradingview.com/symbols/LSE-BARC/forecast/"
driver.get(url)

# Buscamos el valor del "Average" target
try:
    # Este selector busca el contenedor del precio objetivo
    target_element = driver.find_element(By.CLASS_NAME, "priceWrapper-S99_JovX")
    valor = target_element.text.split('\n')[0]

    # Guardar en un CSV que Excel abre sin problemas
    df = pd.DataFrame([{'Ticker': 'BARC', 'Target': valor}])
    df.to_csv('precios_tradingview.csv', index=False)
    print(f"Éxito: {valor} guardado.")

except Exception as e:
    print(f"No se pudo encontrar el dato: {e}")

driver.quit()
