from setuptools import setup, find_packages

setup(
    name="evomorph",
    version="0.0.7",
    description="易衍·Evomorph — 六十四卦指令集进化编程语言",
    packages=find_packages(exclude=["cli", "cli.*"]),
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "evo-ai=cli.evo_ai:main",
            "evoshell=cli.evoshell:main",
            "evo-repl=cli.repl:main",
        ],
    },
)
