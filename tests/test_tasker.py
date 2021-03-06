from __future__ import print_function

from fixtures import temp_image_name

from dock.core import DockerTasker
from tests.constants import INPUT_IMAGE, DOCKERFILE_GIT

import git
import docker, docker.errors
import pytest


# TEST-SUITE SETUP

def setup_module(module):
    d = docker.Client()
    try:
        d.inspect_image(INPUT_IMAGE)
        setattr(module, 'HAS_IMAGE', True)
    except docker.errors.APIError:
        _ = [x for x in d.pull("busybox:latest", stream=True)]
        setattr(module, 'HAS_IMAGE', False)


def teardown_module(module):
    if not getattr(module, 'HAS_IMAGE', False):
        d = docker.Client()
        d.remove_image(INPUT_IMAGE)


# TESTS

def test_run():
    t = DockerTasker()
    container_id = t.run(INPUT_IMAGE, command="id")
    try:
        t.wait(container_id)
    finally:
        t.remove_container(container_id)


def test_run_invalid_command():
    t = DockerTasker()
    command = "eporeporjgpeorjgpeorjgpeorjgpeorjgpeorjg"  # I hope this doesn't exist
    try:
        with pytest.raises(docker.errors.APIError):
            t.run(INPUT_IMAGE, command=command)
    finally:
        # remove the container
        containers = t.d.containers(all=True)
        container_id = [c for c in containers if c["Command"] == command][0]['Id']
        t.remove_container(container_id)


def test_image_exists():
    t = DockerTasker()
    assert t.image_exists(INPUT_IMAGE) is True


def test_image_doesnt_exist():
    t = DockerTasker()
    assert t.image_exists("lerknglekrnglekrnglekrnglekrng") is False


def test_logs():
    t = DockerTasker()
    container_id = t.run(INPUT_IMAGE, command="id")
    try:
        t.wait(container_id)
        output = t.logs(container_id, stderr=True, stream=False)
        assert "\n".join(output).startswith("uid=")
    finally:
        t.remove_container(container_id)


def test_remove_container():
    t = DockerTasker()
    container_id = t.run(INPUT_IMAGE, command="id")
    try:
        t.wait(container_id)
    finally:
        t.remove_container(container_id)


def test_remove_image(temp_image_name):
    t = DockerTasker()
    container_id = t.run(INPUT_IMAGE, command="id")
    t.wait(container_id)
    image_id = t.commit_container(container_id, repository=temp_image_name)
    try:
        t.remove_container(container_id)
    finally:
        t.remove_image(image_id)
    assert not t.image_exists(temp_image_name)


def test_commit_container(temp_image_name):
    t = DockerTasker()
    container_id = t.run(INPUT_IMAGE, command="id")
    t.wait(container_id)
    image_id = t.commit_container(container_id, message="test message", repository=temp_image_name)
    try:
        assert t.image_exists(image_id)
    finally:
        t.remove_container(container_id)
        t.remove_image(image_id)


def test_inspect_image():
    t = DockerTasker()
    inspect_data = t.inspect_image(INPUT_IMAGE)
    assert isinstance(inspect_data, dict)


def test_tag_image(temp_image_name):
    t = DockerTasker()
    expected_img = "somewhere.example.com/%s:1" % temp_image_name
    img = t.tag_image(INPUT_IMAGE, temp_image_name, reg_uri="somewhere.example.com", tag='1')
    try:
        assert t.image_exists(expected_img)
        assert img == expected_img
    finally:
        t.remove_image(expected_img)


def test_push_image(temp_image_name):
    t = DockerTasker()
    expected_img = "localhost:5000/%s:1" % temp_image_name
    t.tag_image(INPUT_IMAGE, temp_image_name, reg_uri="localhost:5000", tag='1')
    output = t.push_image(expected_img, insecure=True)
    assert output is not None
    t.remove_image(expected_img)


def test_tag_and_push(temp_image_name):
    t = DockerTasker()
    expected_img = "localhost:5000/%s:1" % temp_image_name
    output = t.tag_and_push_image(INPUT_IMAGE, temp_image_name, reg_uri="localhost:5000", tag='1', insecure=True)
    assert output is not None
    assert t.image_exists(expected_img)
    t.remove_image(expected_img)


def test_pull_image():
    t = DockerTasker()
    expected_img = "localhost:5000/busybox"
    t.tag_and_push_image('busybox', 'busybox', 'localhost:5000', insecure=True)
    got_image = t.pull_image('busybox', 'localhost:5000', insecure=True)
    assert expected_img == got_image
    assert len(t.last_logs) > 0
    t.remove_image(got_image)


def test_get_image_info_by_id_nonexistent():
    t = DockerTasker()
    response = t.get_image_info_by_image_id("asd")
    assert response is None


def test_get_image_info_by_id():
    t = DockerTasker()
    image_id = t.get_image_info_by_image_name("busybox")[0]['Id']
    response = t.get_image_info_by_image_id(image_id)
    assert isinstance(response, dict)


def test_get_image_info_by_name_tag_in_name():
    t = DockerTasker()
    response = t.get_image_info_by_image_name(image_name=INPUT_IMAGE)
    assert len(response) == 0


def test_build_image_from_path(tmpdir, temp_image_name):
    tmpdir_path = str(tmpdir.realpath())
    git.Repo.clone_from(DOCKERFILE_GIT, tmpdir_path)
    df = tmpdir.join("Dockerfile")
    assert df.check()
    t = DockerTasker()
    response = t.build_image_from_path(tmpdir_path, temp_image_name, use_cache=True)
    list(response)
    assert response is not None
    assert t.image_exists(temp_image_name)
    t.remove_image(temp_image_name)


def test_build_image_from_git(temp_image_name):
    t = DockerTasker()
    response = t.build_image_from_git(DOCKERFILE_GIT, temp_image_name, use_cache=True)
    list(response)
    assert response is not None
    assert t.image_exists(temp_image_name)
    t.remove_image(temp_image_name)
