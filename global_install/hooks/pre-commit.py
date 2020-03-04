#!/usr/bin/env python
"""File generated by pre-commit: https://pre-commit.com"""
from __future__ import print_function

import distutils.spawn
import os
import subprocess
import sys
from os.path import expanduser

# work around https://github.com/Homebrew/homebrew-core/issues/30445
os.environ.pop("__PYVENV_LAUNCHER__", None)

HERE = os.path.dirname(os.path.abspath(__file__))
Z40 = "0" * 40
ID_HASH = "138fd403232d2ddd5efb44317e38bf03"
# start templated

# global_config = 'gds/git-template/.pre-commit-config.yaml'
cmd = ("git", "rev-parse", "--show-toplevel")
top_level = subprocess.check_output(cmd).decode("UTF-8").strip()

hook_location_cmd = ("git", "config", "core.hooksPath")
GLOBAL_CONFIG = subprocess.check_output(hook_location_cmd).decode("UTF-8").strip()

LOCAL_CONFIG = os.path.join(top_level, ".pre-commit-config.yaml")
HOOK_TYPE = "pre-commit"
INSTALL_PYTHON = "/usr/local/Cellar/pre-commit/1.20.0/libexec/bin/python3.7"
SKIP_ON_MISSING_CONFIG = False
# end templated


class EarlyExit(RuntimeError):
    pass


class FatalError(RuntimeError):
    pass


def _norm_exe(exe):
    """Necessary for shebang support on windows.

    roughly lifted from `identify.identify.parse_shebang`
    """
    with open(exe, "rb") as f:
        if f.read(2) != b"#!":
            return ()
        try:
            first_line = f.readline().decode("UTF-8")
        except UnicodeDecodeError:
            return ()

        cmd = first_line.split()
        if cmd[0] == "/usr/bin/env":
            del cmd[0]
        return tuple(cmd)


def _run_legacy():
    if __file__.endswith(".legacy"):
        raise SystemExit(
            "bug: pre-commit's script is installed in migration mode\n"
            "run `pre-commit install -f --hook-type {}` to fix this\n\n"
            "Please report this bug at "
            "https://github.com/pre-commit/pre-commit/issues".format(HOOK_TYPE)
        )

    if HOOK_TYPE == "pre-push":
        stdin = getattr(sys.stdin, "buffer", sys.stdin).read()
    else:
        stdin = None

    legacy_hook = os.path.join(HERE, "{}.legacy".format(HOOK_TYPE))
    if os.access(legacy_hook, os.X_OK):
        cmd = _norm_exe(legacy_hook) + (legacy_hook,) + tuple(sys.argv[1:])
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE if stdin else None)
        proc.communicate(stdin)
        return proc.returncode, stdin
    else:
        return 0, stdin


def _find_config():
    if os.path.isfile(LOCAL_CONFIG):
        return LOCAL_CONFIG
    else:
        return GLOBAL_CONFIG


def _validate_config(config):
    if os.path.isfile(config):
        pass
    elif SKIP_ON_MISSING_CONFIG or os.getenv("PRE_COMMIT_ALLOW_NO_CONFIG"):
        print("`{}` config file not found. " "Skipping `pre-commit`.".format(config))
        raise EarlyExit()
    else:
        raise FatalError(
            "No {} file was found\n"
            "- To temporarily silence this, run "
            "`PRE_COMMIT_ALLOW_NO_CONFIG=1 git ...`\n"
            "- To permanently silence this, install pre-commit with the "
            "--allow-missing-config option\n"
            "- To uninstall pre-commit run "
            "`pre-commit uninstall`".format(config)
        )


def _exe():
    with open(os.devnull, "wb") as devnull:
        for exe in (INSTALL_PYTHON, sys.executable):
            try:
                if not subprocess.call(
                    (exe, "-c", "import pre_commit.main"),
                    stdout=devnull,
                    stderr=devnull,
                ):
                    return (exe, "-m", "pre_commit.main", "run")
            except OSError:
                pass

    if distutils.spawn.find_executable("pre-commit"):
        return ("pre-commit", "run")

    raise FatalError("`pre-commit` not found. Did you `pip install pre-commit`?")


def _rev_exists(rev):
    return not subprocess.call(("git", "rev-list", "--quiet", rev))


def _pre_push(stdin):
    remote = sys.argv[1]

    opts = ()
    for line in stdin.decode("UTF-8").splitlines():
        _, local_sha, _, remote_sha = line.split()
        if local_sha == Z40:
            continue
        elif remote_sha != Z40 and _rev_exists(remote_sha):
            opts = ("--origin", local_sha, "--source", remote_sha)
        else:
            # ancestors not found in remote
            ancestors = (
                subprocess.check_output(
                    (
                        "git",
                        "rev-list",
                        local_sha,
                        "--topo-order",
                        "--reverse",
                        "--not",
                        "--remotes={}".format(remote),
                    )
                )
                .decode()
                .strip()
            )
            if not ancestors:
                continue
            else:
                first_ancestor = ancestors.splitlines()[0]
                cmd = ("git", "rev-list", "--max-parents=0", local_sha)
                roots = set(subprocess.check_output(cmd).decode().splitlines())
                if first_ancestor in roots:
                    # pushing the whole tree including root commit
                    opts = ("--all-files",)
                else:
                    cmd = ("git", "rev-parse", "{}^".format(first_ancestor))
                    source = subprocess.check_output(cmd).decode().strip()
                    opts = ("--origin", local_sha, "--source", source)

    if opts:
        return opts
    else:
        # An attempt to push an empty changeset
        raise EarlyExit()


def _opts(stdin, config):
    fns = {
        "prepare-commit-msg": lambda _: ("--commit-msg-filename", sys.argv[1]),
        "commit-msg": lambda _: ("--commit-msg-filename", sys.argv[1]),
        "pre-commit": lambda _: (),
        "pre-push": _pre_push,
    }
    stage = HOOK_TYPE.replace("pre-", "")
    return ("--config", config, "--hook-stage", stage) + fns[HOOK_TYPE](stdin)


if sys.version_info < (3, 7):  # https://bugs.python.org/issue25942

    def _subprocess_call(cmd):  # this is the python 2.7 implementation
        return subprocess.Popen(cmd).wait()


else:
    _subprocess_call = subprocess.call


def main():
    config_path = os.path.join(top_level, ".git/config")
    baseline_path = os.path.join(top_level, ".secrets.baseline")
    with open(config_path) as config:
        if "alphagov" not in config.read():
            print("This is not an alphagov repo, secrets detection skipped")
            sys.exit(0)

    if not os.path.isfile(baseline_path):
        print("Unable to open baseline file: `REPO_ROOT`/.secrets.baseline")
        print("Please create it via")
        print("   `detect-secrets scan > " + baseline_path + "`")
        sys.exit(1)

    retv, stdin = _run_legacy()
    try:
        config_location = _find_config()
        _validate_config(config_location)
        return retv | _subprocess_call(_exe() + _opts(stdin, config_location))
    except EarlyExit:
        return retv
    except FatalError as e:
        print(e.args[0])
        return 1
    except KeyboardInterrupt:
        return 1


if __name__ == "__main__":
    exit(main())
