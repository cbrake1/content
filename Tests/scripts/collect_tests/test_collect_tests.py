from pathlib import Path
from typing import Callable, Iterable, Optional

import pytest
from Tests.scripts.collect_tests.constants import XSOAR_SANITY_TEST_NAMES
from Tests.scripts.collect_tests.path_manager import PathManager
from Tests.scripts.collect_tests.utils import PackManager

import collect_tests
# importing Machine from collect_tests (rather than utils) to compare class member values
from collect_tests import (Machine, XSIAMNightlyTestCollector,
                           XSOARNightlyTestCollector)

"""
Test Collection Unit-Test cases 
- `empty` has no packs
- `A` has a single pack with an integration and two test playbooks. 
- `B` has a single pack, with only test playbooks. (they should be collected) 
- `C` has a pack supported by both marketplaces, and one only for marketplacev2 and one only for XSOAR.
"""


class CollectTestsMocker:
    """
    Allows testing Test Collection, by "mocking" (changing reference in memory) collect_tests.
    """

    def __init__(self, content_path: Path):
        self.path_manager = PathManager(content_path)
        self.previous_path_manager = None

    def __enter__(self):
        print(f'mocking content root={self.path_manager.content_path}')
        self.previous_path_manager = collect_tests.PATHS
        self._mock(self.path_manager)

    def __exit__(self, *args):
        self._mock(self.previous_path_manager)
        self.previous_path_manager = None

    @staticmethod
    def _mock(path_manager: PathManager):
        collect_tests.PATHS = path_manager
        collect_tests.PACK_MANAGER = PackManager(path_manager)

    def __repr__(self):
        return str(self.path_manager.content_path)


class MockerCases:
    empty = CollectTestsMocker(Path('test_data/empty'))
    empty_xsiam = CollectTestsMocker(Path('test_data/empty_xsiam'))
    A_xsoar = CollectTestsMocker(Path('test_data/A_xsoar'))
    A_xsiam = CollectTestsMocker(Path('test_data/A_xsiam'))
    B_xsiam = CollectTestsMocker(Path('test_data/B_xsiam'))
    B_xsoar = CollectTestsMocker(Path('test_data/B_xsoar'))
    C = CollectTestsMocker(Path('test_data/C'))


def _test(mocker: CollectTestsMocker, run_nightly: bool, run_master: bool, collector_class: Callable,
          expected_tests: Iterable[str], expected_packs: Iterable[str],
          expected_machines: Optional[Iterable[Machine]], collector_class_args: tuple[str] = ()):
    with mocker:
        collected = collector_class(*collector_class_args).collect(run_nightly, run_master)

        if not any((expected_tests, expected_packs, expected_machines)):
            assert not collected, f'collected packs {collected.packs}, tests {collected.tests}'

        if expected_tests:
            assert collected.tests == set(expected_tests)
        if expected_packs:
            assert collected.packs == set(expected_packs)
        if expected_machines:
            assert set(collected.machines) == set(expected_machines)

        assert run_nightly == (Machine.NIGHTLY in collected.machines)
        assert run_master == (Machine.MASTER in collected.machines)

    for test in collected.tests:
        print(f'collected test {test}')
    for machine in collected.machines:
        print(f'machine {machine}')
    for pack in collected.packs:
        print(f'collected pack {pack}')


@pytest.mark.parametrize('mocker,collector_class,expected_tests,expected_packs', (
        (MockerCases.empty, XSOARNightlyTestCollector, XSOAR_SANITY_TEST_NAMES, ()),
        (MockerCases.empty, XSIAMNightlyTestCollector, (), ()),
        (MockerCases.empty_xsiam, XSIAMNightlyTestCollector, ('some_xsiam_test',), ()),
        (MockerCases.C, XSOARNightlyTestCollector,
         ('myXSOAROnlyTestPlaybook', 'myTestPlaybook'), ('myXSOAROnlyPack', 'bothMarketplacesPack')),
        (MockerCases.C, XSIAMNightlyTestCollector,
         ('myXSIAMOnlyTestPlaybook',), ('bothMarketplacesPack', 'myXSIAMOnlyPack')),
))
@pytest.mark.parametrize('run_master', (True, False))
def test_nightly_empty(mocker, run_master: bool, collector_class: Callable,
                       expected_tests: tuple[str], expected_packs: tuple[str]):
    """
    given:  a content folder
    when:   collecting tests with a NightlyTestCollector
    then:   make sure sanity tests are collected for XSOAR, and that XSIAM tests are collected from conf.json
    """
    _test(mocker, run_nightly=True, run_master=run_master, collector_class=collector_class,
          expected_tests=expected_tests, expected_packs=expected_packs, expected_machines=None)


@pytest.mark.parametrize('mocker,collector_class', (
        (MockerCases.A_xsoar, XSOARNightlyTestCollector),
        (MockerCases.A_xsiam, XSIAMNightlyTestCollector),
        (MockerCases.B_xsoar, XSOARNightlyTestCollector),
        (MockerCases.B_xsiam, XSIAMNightlyTestCollector)
))
@pytest.mark.parametrize('run_master', (True, False))
@pytest.mark.parametrize('run_nightly', (True, False))
def test_nightly(mocker, run_master: bool, collector_class: Callable, run_nightly: bool):
    """
    given:  a content folder
    when:   collecting tests with a NightlyTestCollector
    then:   make sure tests are collected from integration and id_set
    """
    # noinspection PyTypeChecker
    expected_pack = {XSOARNightlyTestCollector: ('myXSOAROnlyPack',),
                     XSIAMNightlyTestCollector: ('myXSIAMOnlyPack',)}[collector_class]

    _test(mocker, run_nightly=run_nightly, run_master=run_master, collector_class=collector_class,
          expected_tests=('myTestPlaybook', 'myOtherTestPlaybook'),
          expected_packs=expected_pack,
          expected_machines=None)
