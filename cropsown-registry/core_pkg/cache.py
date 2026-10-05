from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend


def init_cache():
    FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache-registry")


# Custom key builder
def metadata_key_builder(func, namespace: str, *args, **kwargs):
    """
    Build a custom cache key with `uuid`.
    """
    args: list = kwargs.get("args")
    uuid: str = args[1]

    return f"{namespace}{uuid}"
