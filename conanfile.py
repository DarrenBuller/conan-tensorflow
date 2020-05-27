#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Conan recipe package for tensorflow
"""
from conans import ConanFile, tools
import os
import sys
import shutil
import itertools


class TensorFlowConan(ConanFile):
    name = "tensorflow"
    version = "1.14.0"
    description = "https://www.tensorflow.org/"
    topics = ("conan", "tensorflow", "ML")
    url = "https://github.com/bincrafters/conan-tensorflow"
    homepage = "The core open source library to help you develop and train ML models"
    license = "Apache-2.0"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    def build_requirements(self):
        if not tools.which("bazel"):
            self.build_requires("bazel_installer/0.25.2")
        if not (tools.which("java") and tools.which("javac")):
            self.build_requires("java_installer/8.0.144@bincrafters/stable")
        if tools.os_info.is_windows and "CONAN_BASH_PATH" not in os.environ:
            self.build_requires("msys2_installer/latest@bincrafters/stable")

    def config_options(self):
        if self.settings.os == 'Windows':
            del self.options.fPIC

    def source(self):
        source_url = "https://github.com/tensorflow/tensorflow"
        tools.get("{0}/archive/v{1}.tar.gz".format(source_url, self.version),
                  sha256="aa2a6a1daafa3af66807cfe0bc77bfe1144a9a53df9a96bab52e3e575b3047ed")
        extracted_dir = self.name + "-" + self.version
        os.rename(extracted_dir, self._source_subfolder)

    def build(self):
        with tools.chdir(self._source_subfolder):
            env_build = dict()
            env_build["PYTHON_BIN_PATH"] = sys.executable
            env_build["USE_DEFAULT_PYTHON_LIB_PATH"] = "1"
            env_build["TF_ENABLE_XLA"] = '0'
            env_build["TF_NEED_OPENCL_SYCL"] = '0'
            env_build["TF_NEED_ROCM"] = '0'
            env_build["TF_NEED_CUDA"] = '0'
            env_build["TF_NEED_MPI"] = '0'
            env_build["TF_DOWNLOAD_CLANG"] = '0'
            env_build["TF_SET_ANDROID_WORKSPACE"] = "0"
            env_build["CC_OPT_FLAGS"] = "/arch:AVX" if self.settings.compiler == "Visual Studio" else "-march=native"
            env_build["TF_CONFIGURE_IOS"] = "1" if self.settings.os == "iOS" else "0"
            tools.run_in_windows_bash(self, "./tensorflow/contrib/makefile/download_dependencies.sh")
            with tools.environment_append(env_build):
                self.run("python configure.py" if tools.os_info.is_windows else "./configure")
                self.run("bazel shutdown")
                target = {"Macos": "//tensorflow:libtensorflow_cc.dylib",
                          "Linux": "//tensorflow:libtensorflow_cc.so",
                          "Windows": "//tensorflow:libtensorflow_cc.dylib"}.get(str(self.settings.os))
                          # "Windows": "//tensorflow:libtensorflow_cc.dll"}.get(str(self.settings.os))
                self.run("""bazel build --cxxopt="/Zm50" --cxxopt="/Y-" --config=opt --define=no_tensorflow_py_deps=true %s --verbose_failures""" % target)
                self.run("""bazel build --cxxopt="/Zm50" --cxxopt="/Y-" --cxxopt="/Y-" --config=opt --define=no_tensorflow_py_deps=true %s --verbose_failures""" % "//tensorflow:install_headers")
                target = {"Macos": "//tensorflow/lite:libtensorflowlite.dylib",
                          "Linux": "//tensorflow/lite:libtensorflowlite.so",
                          "Windows": "tensorflow/lite:libtensorflowlite.dll"}.get(str(self.settings.os))
                self.run("""bazel build --cxxopt="/Zm50" --cxxopt="/Y-" --config=opt --define=no_tensorflow_py_deps=true %s --verbose_failures""" % target)
                

    def packageLibs(self, src):
        libs = itertools.chain(
        self.copy("*.so", dst="lib", src=src, keep_path=False, symlinks=False),
        self.copy("*.so.*", dst="lib", src=src, keep_path=False, symlinks=False),
        self.copy("*.dll", dst="lib", src=src, keep_path=False, symlinks=False),
        self.copy("*.dylib*", dst="lib", src=src, keep_path=False, symlinks=False))

        # Conan bug?
        # bazel produces libraries with r-x perms, and conan uses shutil.copy2 to perform all copies
        # As result it preserves metadata, but internally it opens file for write, which results in error on second time you copy files
        # So just make it 777
        for lib in libs:
            os.chmod(lib, 0o777)

    def package(self):
        #self.copy(pattern="LICENSE", dst="licenses", src=self._source_subfolder)
        #self.copy(pattern="*.dll", dst="bin", src=self._source_subfolder, keep_path=False, symlinks=True)
        #self.copy(pattern="*.lib", dst="lib", src=self._source_subfolder, keep_path=False, symlinks=True)
        #self.copy(pattern="*.so*", dst="lib", src=self._source_subfolder, keep_path=False, symlinks=True)
        #self.copy(pattern="*.dylib*", dst="lib", src=self._source_subfolder, keep_path=False, symlinks=True)

        lite_lib_dir = "{}/bazel-bin/tensorflow/lite/".format(self._source_subfolder)
        inc_dir = "{}/tensorflow/lite/".format(self._source_subfolder )
        lib_dir = "{}/bazel-bin/tensorflow".format(self._source_subfolder)

        # Work-around to not fail copy below, as conan cannot handle multiple files with the same name
        # and fails with PermissionError
        shutil.rmtree("{}/libtensorflowlite.so.runfiles".format(lite_lib_dir), True)
        shutil.rmtree("{}/delegates/gpu/libtensorflowlite_gpu_gl.so.runfiles".format(lite_lib_dir), True)

        self.packageLibs(src=lib_dir)

        self.copy("*.h", dst="include/tensorflow", src=inc_dir, keep_path=True, symlinks=True)
        self.copy("*.hpp", dst="include/tensorflow", src=inc_dir, keep_path=True, symlinks=True)
    def package_info(self):
        self.cpp_info.libs = ["tensorflow"]
