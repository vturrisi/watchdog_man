from setuptools import setup

setup(name='watchdog_man',
      version='0.1.0',
      description='Simple library to monitor experiments',
      url='https://github.com/vturrisi/watchdog_man',
      author='Victor Turrisi',
      license='MIT',
      packages=['watchdog_man'],
      install_requires=[p.strip() for p in open('requirements.txt').readlines()],
      include_package_data=True,
      zip_safe=False)