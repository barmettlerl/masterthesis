import os
import pytest
import yaml
from canary_tester.config_loader.config_loader import ConfigLoader
from pydantic import ValidationError


class TestConfigLoader:
    def test_load_file_does_not_exist(self):
        with pytest.raises(FileNotFoundError):
            ConfigLoader.load_config(
                os.path.dirname(os.path.abspath(__file__)) + "/file_does_not_exist.yaml"
            )

    def test_falsy_yaml_file_structure(self):
        with pytest.raises(yaml.YAMLError):
            ConfigLoader.load_config(
                os.path.dirname(os.path.abspath(__file__)) + "/falsy_yaml_file.yaml"
            )

    def test_empty_yaml_file_structure(self):
        with pytest.raises(yaml.YAMLError):
            ConfigLoader.load_config(
                os.path.dirname(os.path.abspath(__file__)) + "/empty_config_file.yaml"
            )

    def test_load_config_should_fail(self):
        with pytest.raises(ValidationError):
            ConfigLoader.load_config(
                os.path.dirname(os.path.abspath(__file__)) + "/falsy_config.yaml"
            )

    def test_load_correct_config(self):
        config = ConfigLoader.load_config(
            os.path.dirname(os.path.abspath(__file__)) + "/correct_config.yaml"
        )
        assert config["tests"][0]["query"] == "avg (disk_free) by(host)"
