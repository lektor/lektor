import importlib

import lektor.i18n


def test_loading_i18n_triggers_no_warnings(recwarn):
    importlib.reload(lektor.i18n)
    for warning in recwarn.list:
        print(warning)  # debugging: display warnings on stdout
    assert len(recwarn) == 0
