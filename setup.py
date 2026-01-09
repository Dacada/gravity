from setuptools import setup, Extension
from pathlib import Path

ROOT = Path(__file__).parent

physics_core = Extension(
    name="gravity.physics._core",
    sources=[
        "src/gravity/physics/native/bindings.c",
        "src/gravity/physics/native/gravity.c",
    ],
    include_dirs=[
        "src/gravity/physics/native/include",
    ],
    extra_compile_args=["-std=c17", "-Ofast", "-march=native"],
)

setup(
    name="gravity",
    version="0.1.0",
    package_dir={"": "src"},
    packages=[
        "gravity",
        "gravity.camera",
        "gravity.config",
        "gravity.config.schema",
        "gravity.core",
        "gravity.physics",
        "gravity.render",
        "gravity.ui",
    ],
    ext_modules=[physics_core],
)
