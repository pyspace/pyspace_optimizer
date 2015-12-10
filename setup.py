from setuptools import setup
from pySPACEOptimizer.optimizer import OPTIMIZER_ENTRY_POINT
from pySPACEOptimizer.tasks import TASK_ENTRY_POINT


description = """
This software implements a hyperparmeter optimizer for pySPACE.
It uses Hyperopt for the optimization process and is able to
optimize even very complex pipelines.
It does not only optimize the hyperparameters of the processing
pipeline but also the structure of the pipeline itself.
"""


setup(
    name="pySPACEOptimizer",
    version="0.1.0",
    description="Hyperparameter optimizer for pySPACE",
    long_description=description,
    author="Torben Hansing",
    author_email="hansa@tzi.de",
    url="https://gitlab.informatik.uni-bremen.de/hansa/pyspace_optimizer",
    packages=["pySPACEOptimizer"],
    # FIXME: Include pySPACE as depencency as soon as the setup.py of the package does install the software correctly
    install_requires=["numpy", "hyperopt"],
    entry_points={
        "console_scripts": [
            "pySPACEOptimizer = pySPACEOptimizer.__main__:main"
        ],
        OPTIMIZER_ENTRY_POINT: [
            "HyperoptOptimizer = pySPACEOptimizer.optimizer.hyperopt:HyperoptOptimizer"
        ],
        TASK_ENTRY_POINT: [
            "classification = pySPACEOptimizer.tasks.classification:ClassificationTask"
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
