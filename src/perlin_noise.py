import numpy as np

# simple Perlin 1D noise
def perlin_noise(n, seed=None):
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 4*np.pi, n)
    noise = (
        0.6*np.sin(x) +
        0.3*np.sin(2*x + rng.uniform()) +
        0.1*np.sin(4*x + rng.uniform())
    )
    return noise
