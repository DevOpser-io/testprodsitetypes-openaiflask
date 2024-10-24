# start by pulling the python image
FROM python:3.11.2-slim-bullseye

# Create a non-root user with UID 1000
RUN useradd -m -u 1000 appuser

ENV PATH="/usr/local/bin:$PATH"
ENV DOCKER_BUILDKIT=1
ENV FLASK_APP=run
ENV FLASK_ENV=production
ARG OPENAI_SECRET_NAME
ARG FLASK_SECRET_NAME
ARG REDIS_URL
ARG REGION
ARG CACHE_VERSION
ENV CACHE_VERSION=${CACHE_VERSION}
ENV OPENAI_SECRET_NAME=${OPENAI_SECRET_NAME}
ENV FLASK_SECRET_NAME=${FLASK_SECRET_NAME}
ENV REDIS_URL=${REDIS_URL}
ENV REGION=${REGION}

# Create necessary directories and set permissions
RUN mkdir -p /app /app/instance /app/logs /data && \
    chown -R appuser:appuser /app /data

# switch working directory
WORKDIR /app

# copy the requirements file into the image
COPY --chown=appuser:appuser ./app/requirements.txt /app/requirements.txt

# install the dependencies and packages in the requirements file
RUN pip3.11 install -r requirements.txt

# copy every content from the local file to the image
COPY --chown=appuser:appuser . /app

ENV FLASK_RUN_HOST=0.0.0.0

EXPOSE 8000

# Switch to the non-root user
USER appuser

# configure the container to run in an executed manner
ENTRYPOINT ["gunicorn", "--workers", "2", "--threads", "3", "--worker-class", "gthread", "--worker-tmp-dir", "/dev/shm", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-", "--capture-output", "--enable-stdio-inheritance", "run:app", "--bind=0.0.0.0:8000"]
