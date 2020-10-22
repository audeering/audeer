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


    NUM_SAMPLES = int(1e6)


    def is_inside(p):
        x, y = random.random(), random.random()
        return x * x + y * y < 1


    def main():
        inside_samples = audeer.run_tasks(
            is_inside,
            [([n], {}) for n in range(0, NUM_SAMPLES)],
            num_workers=4,
            progress_bar=True,
        )
        pi = 4.0 * sum(inside_samples) / NUM_SAMPLES
        print(f'Pi is roughly {pi}')


    if __name__ == '__main__':
        main()
