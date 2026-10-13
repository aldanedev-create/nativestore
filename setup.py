from pathlib import Path

from setuptools import Distribution, setup
from wheel.bdist_wheel import bdist_wheel

NATIVE = Path("src/nativestore/native/manifest.json").is_file()


class NativeDistribution(Distribution):
    def has_ext_modules(self):
        return NATIVE


class PlatformWheel(bdist_wheel):
    def finalize_options(self):
        super().finalize_options()
        if NATIVE:
            self.root_is_pure = False

    def get_tag(self):
        python, abi, target = super().get_tag()
        return ("py3", "none", target) if NATIVE else (python, abi, target)


setup(distclass=NativeDistribution, cmdclass={"bdist_wheel": PlatformWheel})
