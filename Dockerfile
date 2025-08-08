#Imagen base con Python 3.10
FROM python:3.10-slim

#Directorio de trabajo
WORKDIR /app

#Copiar requirements.txt e instalar lo que sea necesario
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

#Copiar todo el contenido al contenedor
COPY . .

#Se expone el puerto de Streamlit (8501)
EXPOSE 8501

# Comando para ejecutar la app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]