# pypi-cloudfiles

A setuptools wrapper script for uploading packages to Rackspace CloudFiles and building a PyPI compatible index.

## Configuration

pypi-cloudfiles takes advantage of setuptools command line arguments and also the `~/.pypirc` file

### ~/.pypirc

```ini
[cloudfiles]
username: myapiusername
password: myapikey
repository: pypi
```

The password option, should be your API Key, and the repository option, should be the container to use.

## Usage

```bash
cd my-cool-package
pypicf setup.py sdist upload -r cloudfiles
```
