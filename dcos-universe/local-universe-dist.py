#!/usr/bin/env python3

import argparse
import concurrent.futures
import contextlib
import fnmatch
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

HTTP_ROOT    = "http://mesos-boot.sudhaker.com:8082/"
DOCKER_ROOT  = "mesos-boot.sudhaker.com:5000"

HTTP_CACHE   = pathlib.Path("/var/dcos-universe-nginx/cache")
HTTP_WEBROOT = pathlib.Path("/var/dcos-universe-nginx/tmproot")

def main():
    # jsonschema is required by the universe build process, make sure it is
    # installed before running.
    if not shutil.which("jsonschema"):
        print("You must first install jsonschema (pip install jsonschema).")
        sys.exit(1)

    # cosmos requires directories to be saved. python does it only sometimes.
    # Use zip to make sure it works.
    if not shutil.which("zip"):
        print("You must first install `zip`.")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description='This script is able to download the latest artifacts for '
        'all of the packages in the Universe repository into a zipfile. It '
        'uses a temporary file to store all of the artifacts as it downloads '
        'them because of this it requires that your temporary filesystem has '
        'enough space to store all of the artifact. You can control the path '
        'to the temporary file by setting the TMPDIR environment variable. '
        'E.g. TMPDIR=\'.\' ./scripts/local-universe.py ...')
    parser.add_argument(
        '--repository',
        required=True,
        help='Path to the top level package directory. E.g. repo/packages')
    parser.add_argument(
        '--include',
        default='',
        help='Command separated list of packages to include. If this option '
        'is not specified then all packages are downloaded. E.g. '
        '--include="marathon,chronos"')
    parser.add_argument(
        '--selected',
        action='store_true',
        default=False,
        help='Set this to include only selected packages')
    args = parser.parse_args()

    package_names = [name for name in args.include.split(',') if name != '']

    with tempfile.TemporaryDirectory() as dir_path:

        http_artifacts = dir_path / pathlib.Path("http")
        docker_artifacts = dir_path / pathlib.Path("registry")
        repo_artifacts = dir_path / pathlib.Path("universe/repo/packages")

        os.makedirs(str(http_artifacts))
        os.makedirs(str(repo_artifacts))

        failed_packages = []
        def handle_package(opts):
            package, path = opts
            try:
                prepare_repository(package, path, pathlib.Path(args.repository),
                    repo_artifacts)

                for url, archive_path in enumerate_http_resources(package, path):
                    add_http_resource(http_artifacts, url, archive_path)

                for name in enumerate_docker_images(path):
                    download_docker_image(name)
                    upload_docker_image(name)
            except (subprocess.CalledProcessError, urllib.error.HTTPError):
                print('MISSING ASSETS: {}'.format(package))
                remove_package(package, dir_path)
                failed_packages.append(package)

            return package

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            for package in executor.map(handle_package,
                    enumerate_dcos_packages(
                        pathlib.Path(args.repository),
                        package_names,
                        args.selected)):
                print("Completed: {}".format(package))

        build_repository(pathlib.Path(
            os.path.dirname(os.path.realpath(__file__)), '..', 'scripts'),
            pathlib.Path(args.repository),
            pathlib.Path(dir_path, 'universe'))

        build_universe_wwwroot(pathlib.Path(dir_path))

        if failed_packages:
            print("Errors: {}".format(failed_packages))
            print("These packages are not included in the image.")


def enumerate_dcos_packages(packages_path, package_names, only_selected):
    """Enumarate all of the package and revision to include

    :param packages_path: the path to the root of the packages
    :type pacakges_path: str
    :param package_names: list of package to include. empty list means all
                         packages
    :type package_names: [str]
    :param only_selected: filter the list of packages to only ones that are
                          selected
    :type only_selected: boolean
    :returns: generator of package name and revision
    :rtype: gen((str, str))
    """

    for letter_path in packages_path.iterdir():
        assert len(letter_path.name) == 1 and letter_path.name.isupper()
        for package_path in letter_path.iterdir():

            largest_revision = max(
                package_path.iterdir(),
                key=lambda revision: int(revision.name))


            if only_selected:
                with (largest_revision / 'package.json').open() as json_file:
                    if json.load(json_file).get('selected', False):
                        yield (package_path.name, largest_revision)

            elif not package_names or package_path.name in package_names:
                # Enumerate package if list is empty or package name in list
                yield (package_path.name, largest_revision)


def enumerate_http_resources(package, package_path):
    with (package_path / 'resource.json').open() as json_file:
        resource = json.load(json_file)

    for name, url in resource.get('images', {}).items():
        if name != 'screenshots':
            yield url, pathlib.Path(package, 'images')

    for name, url in resource.get('assets', {}).get('uris', {}).items():
        yield url, pathlib.Path(package, 'uris')

    for os_type, arch_dict in resource.get('cli', {}).get('binaries', {}).items():
        for arch in arch_dict.items():
            yield arch[1]['url'], pathlib.Path(package, 'uris')

    command_path = (package_path / 'command.json')
    if command_path.exists():
        with command_path.open() as json_file:
            commands = json.load(json_file)

        for url in commands.get("pip", []):
            yield url, pathlib.Path(package, 'commands')


def enumerate_docker_images(package_path):
    with (package_path / 'resource.json').open() as json_file:
        resource = json.load(json_file)

    dockers = resource.get('assets', {}).get('container', {}).get('docker', {})

    return (name for _, name in dockers.items())


def download_docker_image(name):
    print('Pull docker images: {}'.format(name))
    command = ['docker', 'pull', name]

    subprocess.check_call(command)


def format_image_name(host, name):
    # Probably has a hostname at the front, get rid of it.
    if '.' in name.split(':')[0]:
        return '{}/{}'.format(host, "/".join(name.split("/")[1:]))

    return '{}/{}'.format(host, name)

def upload_docker_image(name):
    print('Pushing docker image: {}'.format(name))

    command = ['docker', 'tag', name,
        format_image_name(DOCKER_ROOT, name)]
    subprocess.check_call(command)

    command = ['docker', 'push', format_image_name(DOCKER_ROOT, name)]
    subprocess.check_call(command)


def my_copytree(src, dst):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)

def build_universe_wwwroot(dir_path):
    print('Building the universe wwwroot')
    dest_dir = str(HTTP_WEBROOT)
    shutil.rmtree(dest_dir, ignore_errors=True)

    os.mkdir(dest_dir)
    my_copytree(str(dir_path / 'http'), dest_dir)
    my_copytree(str(dir_path / 'universe' / 'target'), dest_dir)


def add_http_resource(dir_path, url, base_path):
    archive_path = (dir_path / base_path /
        pathlib.Path(urllib.parse.urlparse(url).path).name)
    print('Adding {} at {}.'.format(url, archive_path))
    os.makedirs(str(archive_path.parent), exist_ok=True)
    cache_path = (HTTP_CACHE / base_path /
        pathlib.Path(urllib.parse.urlparse(url).path).name)
    if not(cache_path.is_file()):
        print('>> Caching {} at {}.'.format(url, cache_path))
        os.makedirs(str(cache_path.parent), exist_ok=True)
        urllib.request.urlretrieve(url, str(cache_path))
    shutil.copy2(str(cache_path), str(archive_path))


def prepare_repository(package, package_path, source_repo, dest_repo):
    dest_path = dest_repo / package_path.relative_to(source_repo)
    shutil.copytree(str(package_path), str(dest_path))

    with (package_path / 'resource.json').open() as source_file, \
            (dest_path / 'resource.json').open('w') as dest_file:
        resource = json.load(source_file)

        # Change the root for images (ignore screenshots)
        if 'images' in resource:
            resource["images"] = {
                n: urllib.parse.urljoin(
                    HTTP_ROOT, str(pathlib.PurePath(
                        package, "images", pathlib.Path(uri).name)))
                for n,uri in resource.get("images", {}).items() if 'icon' in n}

        # Change the root for asset uris.
        if 'assets' in resource:
            resource["assets"]["uris"] = {
                n: urllib.parse.urljoin(
                    HTTP_ROOT, str(pathlib.PurePath(
                        package, "uris", pathlib.Path(uri).name)))
                for n, uri in resource["assets"].get("uris", {}).items()}

        # Change the root for cli uris.
        if 'cli' in resource:
            for os_type, arch_dict in resource.get('cli', {}).get('binaries', {}).items():
                for arch in arch_dict.items():
                    uri = arch[1]["url"]
                    arch[1]["url"] = urllib.parse.urljoin(HTTP_ROOT, str(pathlib.PurePath(
                        package, "uris", pathlib.Path(uri).name)))

        # Add the local docker repo prefix.
        if 'container' in resource["assets"]:
            resource["assets"]["container"]["docker"] = {
                n: format_image_name(DOCKER_ROOT, image_name)
                for n, image_name in resource["assets"]["container"].get(
                    "docker", {}).items() }

        json.dump(resource, dest_file, indent=4)

    command_path = (package_path / 'command.json')
    if not command_path.exists():
        return

    with command_path.open() as source_file, \
            (dest_path / 'command.json').open('w') as dest_file:
        command = json.load(source_file)

        command['pip'] = [
            urllib.parse.urljoin(
                HTTP_ROOT, str(pathlib.PurePath(
                    package, "commands", pathlib.Path(uri).name)))
            for uri in command.get("pip", [])
        ]
        json.dump(command, dest_file, indent=4)


def build_repository(scripts_dir, repo_dir, dest_dir):
    shutil.copytree(str(scripts_dir), str(dest_dir / "scripts"))
    shutil.copytree(str(repo_dir / '..' / 'meta'),
        str(dest_dir / 'repo' / 'meta'))

    command = [ "bash", "scripts/build.sh" ]
    subprocess.check_call(command, cwd=str(dest_dir))


def remove_package(package, base_dir):
    for root, dirnames, filenames in os.walk(base_dir):
        for dirname in fnmatch.filter(dirnames, package):
            shutil.rmtree(os.path.join(root, dirname))


if __name__ == '__main__':
    sys.exit(main())
