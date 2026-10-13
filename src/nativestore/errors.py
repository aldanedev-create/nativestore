class NativeStoreError(Exception):
    """Base exception for actionable framework errors."""


class ConfigurationError(NativeStoreError):
    pass


class RouteError(NativeStoreError):
    pass


class BridgeError(NativeStoreError):
    pass


class AssetError(NativeStoreError):
    pass


class BuildError(NativeStoreError):
    pass
