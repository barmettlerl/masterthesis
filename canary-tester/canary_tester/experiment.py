import datetime as dt
from time import sleep
from typing import List, Optional
from dotenv import load_dotenv
import logging
from requests.exceptions import JSONDecodeError

from canary_tester.types import (
    GlobalConfig,
    RunningThread,
    TesterReturn,
    TesterReturnReason,
    TesterReturnType,
)
from canary_tester.version_enricher import VersionEnricher
from canary_tester.config_loader.config_loader import ConfigLoader
from canary_tester.config_loader.schema import SingleTestConfigType
from canary_tester.tester.test_builder import TestBuilder
from canary_tester.tester.tester import Tester

from canary_tester.helper import load_environment_variable


load_dotenv()


logger = logging.getLogger("root")


def run_tests_until_complete(
    enricher: VersionEnricher,
    tests: List[Tester],
    version_under_test: str,
    fetch_interval_s: int,
    thread: RunningThread,
    initial_timestamp: int,
    control_group_versions: List[str],
    simulation_speedup_factor: int,
):
    """
    Takes all tests and runs them until all tests are completed.
    But before we run the test we update the enricher with the current timestamp.
    such that we can map the correct version to the metric.
    """

    previous_timestamp = initial_timestamp
    start_time = dt.datetime.now()
    experiment_start_time = dt.datetime.fromtimestamp(initial_timestamp)
    test_run_delta = dt.timedelta(seconds=0)

    finished_tests: list[str] = []

    while True:

        with thread.lock:
            if thread.should_stop:
                thread.finished = False
                thread.started = False
                thread.should_stop = False
                logger.info("stopping the experiment!")
                break

        time_now = dt.datetime.now()

        # Wait time without test execution
        wait_time_delta = time_now - start_time - test_run_delta
        # set the start time to the current time
        start_time = time_now

        time_delta_simulated_s = (
            wait_time_delta.total_seconds() * simulation_speedup_factor
            + test_run_delta.total_seconds()
        )

        current_time = dt.datetime.fromtimestamp(previous_timestamp) + dt.timedelta(
            seconds=time_delta_simulated_s
        )
        current_timestamp = current_time.timestamp()

        logger.info({
            "previous_timestamp": dt.datetime.fromtimestamp(
                previous_timestamp
            ).isoformat(),
            "current_timestamp": dt.datetime.fromtimestamp(
                current_timestamp
            ).isoformat(),
            "time_detla_s": time_delta_simulated_s,
            "total_seconds_passed": (
                current_time - experiment_start_time
            ).total_seconds(),
        })

        test_start_time = dt.datetime.now()

        # ------- Test execution -------
        enricher.update(current_timestamp)

        for test in tests:
            if test in finished_tests:
                continue
            try:
                test_return = test.run(
                    previous_timestamp,
                    current_timestamp,
                    (current_time - experiment_start_time).total_seconds(),
                )

            except JSONDecodeError as e:
                logger.error(f"JSONDecodeError: {e}")
                test_return = TesterReturn(
                    name=test.name,
                    type=TesterReturnType.CONTINUE,
                    reason=TesterReturnReason.HTTP_ERROR,
                )
            except Exception as e:
                logger.error(f"Exception: {e}")
                test_return = TesterReturn(
                    name=test.name,
                    type=TesterReturnType.CONTINUE,
                    reason=TesterReturnReason.UNKNOWN_ERROR,
                )

            if test_return.type == TesterReturnType.TERMINATION:
                finished_tests.append(test)
                test_return.log(logger)
            else:
                test_return.log(logger)

        if len(tests) == len(finished_tests):
            raise Exception("All tests are completed")
        # ------- Test execution -------

        # set time needed for test execution
        test_run_delta = dt.datetime.now() - test_start_time

        previous_timestamp = current_timestamp

        sleep(fetch_interval_s / simulation_speedup_factor)


def create_tester(
    enricher: VersionEnricher,
    tests: list[SingleTestConfigType],
    total_peeks: int,
    version_under_test: str,
    control_group_versions: List[str],
    global_config: GlobalConfig,
) -> List[Tester]:
    """
    Build all tests based on the configuration.
    """
    tester: List[Tester] = []

    for test in tests:
        tester.append(
            TestBuilder.build(
                version_under_test=version_under_test,
                total_peeks=total_peeks,
                control_group_versions=control_group_versions,
                enricher=enricher,
                test_config=test,
                global_config=global_config,
            )
        )

    return tester


def run(
    version_under_test: str,
    max_time_s: int,
    fetch_interval_s: int,
    start_time: Optional[int],
    control_group_versions: List[str],
    simulation_speedup_factor: int,
    thread: RunningThread,
):
    logger.info("start experiment!")

    global_config = load_environment_variable()

    config = ConfigLoader.load_config(global_config.CONFIG_FILE_PATH)

    enricher = VersionEnricher(global_config)

    if start_time is not None:
        initial_timestamp = start_time
    else:
        initial_timestamp = dt.datetime.now().timestamp()

    # initial fetch of device to version mapping
    enricher.update(initial_timestamp)

    logger.debug("Initial enricher update")

    filled_control_group_versions = _fill_control_group_versions(
        enricher, control_group_versions, version_under_test
    )

    _verify_versions(enricher, version_under_test, filled_control_group_versions)

    tests: List[Tester] = create_tester(
        enricher=enricher,
        tests=config["tests"],
        total_peeks=max_time_s // fetch_interval_s,
        version_under_test=version_under_test,
        control_group_versions=filled_control_group_versions,
        global_config=global_config,
    )

    for test in tests:
        logger.info(f"Started: {test.name}")

    run_tests_until_complete(
        enricher=enricher,
        tests=tests,
        version_under_test=version_under_test,
        fetch_interval_s=fetch_interval_s,
        thread=thread,
        initial_timestamp=initial_timestamp,
        control_group_versions=filled_control_group_versions,
        simulation_speedup_factor=simulation_speedup_factor,
    )


def _fill_control_group_versions(
    enricher: VersionEnricher,
    control_group_versions: List[str],
    version_under_test: str,
) -> List[str]:
    if control_group_versions == []:
        other_versions = list(
            filter(lambda x: x != version_under_test, enricher.frequencies.keys())
        )
        return other_versions
    return control_group_versions


def _verify_versions(
    enricher: VersionEnricher,
    version_under_test: str,
    control_group_versions: List[str],
):
    if not enricher.verify_version(version_under_test):
        raise Exception(f"Version {version_under_test} is not a valid version")

    for version in control_group_versions:
        if not enricher.verify_version(version):
            raise Exception(f"Version {version} is not a valid version")

    if version_under_test in control_group_versions:
        raise Exception("Version under test is in the control group")
