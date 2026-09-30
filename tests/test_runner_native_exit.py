from randomizer.runner import describe_native_exit


def test_unmarked_log_reports_external_termination(tmp_path):
    log = tmp_path / 'native.log'
    log.write_text('P2_CHAPPY_FSM_POS generator=1\n[PC Port] FPS: 30.0\n', encoding='utf-8')
    assert 'terminated from outside' in describe_native_exit(log)


def test_fatal_line_is_quoted(tmp_path):
    log = tmp_path / 'native.log'
    log.write_text('x\n[PC Port Fatal] abort() called (SIGABRT)\n', encoding='utf-8')
    assert describe_native_exit(log) == 'native reported: [PC Port Fatal] abort() called (SIGABRT)'


def test_orderly_exit_marker(tmp_path):
    log = tmp_path / 'native.log'
    log.write_text('[PC Port] orderly process exit (CRT atexit chain ran)\n', encoding='utf-8')
    assert 'normal exit path' in describe_native_exit(log)


def test_missing_log(tmp_path):
    assert 'unreadable' in describe_native_exit(tmp_path / 'none.log')
