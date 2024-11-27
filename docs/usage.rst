Usage
=====

Look at the modules API documentation at :mod:`audeer`
to find usage examples for all available functions.

The following code example
applies multi-threading with :func:`audeer.run_tasks`
to estimate Pi with a Monte Carlo method.

.. code-block:: python

    import random

    import audeer


    def is_inside(p):
        x, y = random.random(), random.random()
        return x * x + y * y < 1


    def pi(iterations=100_000):
        inside_samples = audeer.run_tasks(
            is_inside,
            [([n], {}) for n in range(0, iterations)],
            num_workers=4,
            progress_bar=True,
            task_description="Estimate PI",
        )
        return 4.0 * sum(inside_samples) / iterations

>>> random.seed(1)
>>> pi(1000)
3.112
