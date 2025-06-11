ARG PYTHON_MAJOR=3
ARG PYTHON_MINOR=10
ARG OS_VARIANT=slim-bookworm
FROM --platform=linux/amd64 public.ecr.aws/docker/library/python:${PYTHON_MAJOR}.${PYTHON_MINOR}-${OS_VARIANT}

# https://stackoverflow.com/a/59812588
ENV PYTHONUNBUFFERED=1

# https://docs.docker.com/engine/reference/builder/#understand-how-arg-and-from-interact
ARG PYTHON_MAJOR
ARG PYTHON_MINOR

# These make the docker_image pants target automagically resolve from its dist directory
COPY actions.import-lerobot-dataset.src.import_lerobot_dataset/import_lerobot_dataset_pex.pex /bin/import_lerobot_dataset.pex
ENTRYPOINT [ "/bin/import_lerobot_dataset.pex", "-m", "import_lerobot_dataset" ]
