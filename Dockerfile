FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml setup.py README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e .
RUN useradd -r -s /bin/false mcp
USER mcp
ENTRYPOINT ["python", "-m", "proxmox_mcp.server"]
