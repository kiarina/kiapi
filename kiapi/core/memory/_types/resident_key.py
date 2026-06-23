type ResidentKey = str
"""Identity of a resident model in the cache — equals :attr:`ModelSpec.key`
(``"family:repo"``), unique per loaded set of weights. Used as the ``_loaded``
dict key and as the ``exclude_key`` that spares the in-use model from eviction."""
