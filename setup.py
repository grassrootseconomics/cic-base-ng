from setuptools import setup

requirements = []
f = open('requirements.txt', 'r')
while True:
    l = f.readline()
    if l == '':
        break
    requirements.append(l.rstrip())
f.close()

test_requirements = []
f = open('test_requirements.txt', 'r')
while True:
    l = f.readline()
    if l == '':
        break
    test_requirements.append(l.rstrip())
f.close()

legacy_requirements = []
f = open('legacy_requirements.txt', 'r')
while True:
    l = f.readline()
    if l == '':
        break
    legacy_requirements.append(l.rstrip())
f.close()

setup(
        include_package_data=True,
        install_requires=requirements,
        tests_require=test_requirements,
        extras_require={
            'legacy': legacy_requirements,
            }
        )
