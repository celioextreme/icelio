# Use a imagem base do Python
FROM python:3.9-slim

# Defina o diretório de trabalho
WORKDIR /app

# Copie o arquivo requirements.txt e instale as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie o restante do código do aplicativo
COPY . .

# Exponha a porta que o Flask usa
EXPOSE 5000

# Defina a variável de ambiente para o Flask
ENV FLASK_APP=app.py

# Comando para rodar o aplicativo
CMD ["flask", "run", "--host=0.0.0.0"]
