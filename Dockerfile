# Imagen base con Python 3.10 (elige la versión que quieras)
FROM python:3.10-slim

# Establece directorio de trabajo
WORKDIR /app

# Copia requirements.txt e instala dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo el contenido de tu app al contenedor
COPY . .

# Expone el puerto de Streamlit (8501)
EXPOSE 8501

# Comando para ejecutar la app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]