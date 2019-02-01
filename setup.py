from setuptools import setup


with open('requirements.txt') as f:
    requirements = [p.strip() for p in f.readlines()]


with open('extra_requirements.txt') as f:
    extra_requirements = [p.strip() for p in f.readlines()]


setup(name='watchdog_man',
      version='0.1.0',
      description='Simple library to log and monitor experiments',
      url='https://github.com/vturrisi/watchdog_man',
      author='Victor Turrisi',
      license='MIT',
      packages=['watchdog_man'],
      install_requires=requirements,
      extra_requires=extra_requirements,
      include_package_data=True,
      zip_safe=False)
