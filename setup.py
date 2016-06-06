import os
from setuptools import setup

from pySPACEOptimizer.framework import OPTIMIZER_ENTRY_POINT, TASK_ENTRY_POINT

directory_name = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(directory_name, "README.md"), "rb") as readme:
    description = readme.read()


setup(
    name="pySPACEOptimizer",
    version="0.1.0",
    description="Hyperparameter optimizer for pySPACE",
    long_description=description,
    author="Torben Hansing",
    author_email="hansa@tzi.de",
    url="https://gitlab.informatik.uni-bremen.de/hansa/pyspace_optimizer",
    packages=["pySPACEOptimizer"],
    # FIXME: Include pySPACE as dependency as soon as the setup.py of the package does install the software correctly
    install_requires=["numpy", "hyperopt", 'scipy', 'PyQt4', 'matplotlib'],
    extras_require={
        "graphs": "matplotlib"
    },
    entry_points={
        "console_scripts": [
            "pySPACEOptimizer = pySPACEOptimizer.core.__main__:main"
        ],
        "gui_scripts": [
            "optimizerPerformanceAnalysis = pySPACEOptimizer.hyperopt.tools.performance_analysis"
        ],
        OPTIMIZER_ENTRY_POINT: [
            "HyperoptOptimizer = pySPACEOptimizer.hyperopt.optimizer:HyperoptOptimizer",
            "SerialHyperoptOptimizer = pySPACEOptimizer.hyperopt.optimizer:SerialHyperoptOptimizer",
        ],
        TASK_ENTRY_POINT: [
            "classification = pySPACEOptimizer.hyperopt.classification_task:ClassificationTask",
            "classificationWithoutScikit = pySPACEOptimizer.hyperopt.classification_task:ClassificationTaskWithoutScikit"
        ]
    },
    classifiers=["Development Status :: 2 - Pre-Alpha",
                 "Environment :: Console",
                 "Intended Audience :: Developers",
                 "Intended Audience :: Education",
                 "Intended Audience :: Science/Research",
                 "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
                 "Programming Language :: Python :: 2.7",
                 "Topic :: Scientific/Engineering :: Artificial Intelligence",
                 "Topic :: Scientific/Engineering :: Information Analysis"],
)
