FROM python:3.11-alpine

# Install dependencies for lxml
RUN apk add --no-cache gcc musl-dev libxml2-dev libxslt-dev

# Upgrade pip
RUN pip install --upgrade pip

# Create non-root user
RUN adduser -D taxi
USER taxi
WORKDIR /home/taxi

# Copy and install requirements
COPY --chown=taxi:taxi requirements.txt requirements.txt
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=taxi:taxi . .

# Set Python to run in unbuffered mode for better logging
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "main.py"]
