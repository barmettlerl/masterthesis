import yaml
import logging

from canary_tester.config_loader.schema import TestConfigList, TestConfigListType

logger = logging.getLogger("root")


class ConfigLoader:
    """This class is responsible for loading the configuration file."""

    def load_config(config_file_path) -> TestConfigListType:
        """Load the configuration file. It expects a yaml file and
        validates it against a schema
        """

        with open(config_file_path, "r") as file:
            try:
                config = yaml.safe_load(file)
                if config is None:
                    raise yaml.YAMLError("Empty config file")
                TestConfigList(**config)
                logger.debug("config file successfully loaded.")
                return config
            except yaml.YAMLError as exc:
                raise exc
            except Exception as exc:
                raise exc
