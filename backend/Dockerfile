FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home sporthub && mkdir -p media staticfiles && chown -R sporthub:sporthub /app
USER sporthub
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && waitress-serve --listen=0.0.0.0:8000 config.wsgi:application"]
