FROM python:3.12-slim

ARG INSTALL_RUNNER=0

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY . /workspace

RUN python -m pip install --no-cache-dir --upgrade pip \
    && if [ "$INSTALL_RUNNER" = "1" ]; then \
         python -m pip install --no-cache-dir -e '.[dev,runner]'; \
       else \
         python -m pip install --no-cache-dir -e '.[dev]'; \
       fi

CMD ["sh", "-c", "aria-evals doctor && aria-evals validate && python -m pytest -q tests"]
