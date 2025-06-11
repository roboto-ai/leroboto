resource(
    name="py_typed",
    source="py.typed",
)

python_sources()

pex_binary(
    name="import_lerobot_dataset_pex",
    complete_platforms=["build-support/pex_platforms:debian_py310"],
    entry_point="import_lerobot_dataset.__main__",
    execution_mode="venv"
)