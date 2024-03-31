# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV SECRET_KEY='django-insecure-1hrd@6u+u$0ouahd*z)v5ra+hu1nn&ljum=oh(r0i3noxbsg7i'
ENV DEBUG=True

# Set work directory
WORKDIR /code

# Install dependencies
RUN apt-get update && apt-get install -y libpq-dev
COPY requirements.txt /code/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project
COPY . /code/

# Run migrations
RUN python manage.py makemigrations
RUN python manage.py migrate

# Create superuser
RUN echo "from authorization.models import CustomUser; CustomUser.objects.create_superuser(name='founder', surname='lite', email='tsholo.koketso@icloud.com', password='password')" | python manage.py shell

# Expose port
EXPOSE 8000

# Run the application:
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]



