from setuptools import setup, find_packages

setup(
    name="evomorph",
    version="3.0.0",
    description="易衍·Evomorph — 六十四卦指令集进化编程语言",
    packages=find_packages(),
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "evo-ai=evomorph.cli.evo_ai:main",
        ],
    },
)
