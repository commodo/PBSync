from pbpy.pbtools import error_state
import os.path
import os
import sys
import argparse
import webbrowser

from pathlib import Path

from pbpy import pblog
from pbpy import pbgh
from pbpy import pbtools
from pbpy import pbunreal
from pbpy import pbgit
from pbpy import pbconfig
from pbpy import pbpy_version
from pbpy import pbdispatch
from pbpy import pbuac

import pbsync_version

default_config_name = "PBSync.xml"


def config_handler(config_var, config_parser_func):
    if not pbconfig.generate_config(config_var, config_parser_func):
        # Logger is not initialized yet, so use print instead
        error_state(f"{str(config_var)} config file is not valid or not found. Please check the integrity of the file", hush=True, term=True)


def sync_handler(sync_val: str, repository_val=None, requested_bundle_name=None):

    sync_val = sync_val.lower()

    if sync_val == "all" or sync_val == "force" or sync_val == "partial":
        # Firstly, check our remote connection before doing anything
        remote_state, remote_url = pbgit.check_remote_connection()
        if not remote_state:
            error_state(
                f"Remote connection was not successful. Please verify that you have a valid git remote URL and internet connection. Current git remote URL: {remote_url}")
        else:
            pblog.info("Remote connection is up")

        pblog.info("------------------")

        pblog.info(f"Executing {sync_val} sync command")
        pblog.info(f"PBpy Library Version: {pbpy_version.ver}")
        pblog.info(f"PBSync Program Version: {pbsync_version.ver}")

        pblog.info("------------------")

        detected_git_version = pbgit.get_git_version()
        needs_git_update = False
        if detected_git_version == pbconfig.get('supported_git_version'):
            pblog.info(f"Current Git version: {detected_git_version}")
        else:
            pblog.error("Git is not updated to the supported version in your system")
            pblog.error(f"Supported Git Version: {pbconfig.get('supported_git_version')}")
            pblog.error(f"Current Git Version: {detected_git_version}")
            pblog.error("Please install the supported Git version from https://github.com/microsoft/git/releases")
            pblog.error("Visit https://github.com/ProjectBorealisTeam/pb/wiki/Prerequisites for installation instructions")
            if os.name == "nt":
                webbrowser.open(f"https://github.com/microsoft/git/releases/download/v{pbconfig.get('supported_git_version')}/Git-{pbconfig.get('supported_git_version')}-64-bit.exe")
            needs_git_update = True


        if os.name == "nt" and pbgit.get_git_executable() == "git" and pbgit.get_lfs_executable() == "git-lfs":
            # find Git/cmd/git.exe
            git_paths = [path for path in pbtools.whereis("git") if "cmd" in path.parts]

            if len(git_paths) > 0:
                bundled_git_lfs = False

                is_admin = pbuac.isUserAdmin()

                delete_paths = []

                for git_path in git_paths:
                    # find Git from Git/cmd/git.exe
                    git_root = git_path.parents[1]
                    possible_lfs_paths = ["cmd/git-lfs.exe", "mingw64/bin/git-lfs.exe", "mingw64/libexec/git-core/git-lfs.exe"]
                    for possible_lfs_path in possible_lfs_paths:
                        path = git_root / possible_lfs_path
                        if path.exists():
                            try:
                                if is_admin:
                                    path.unlink()
                                else:
                                    delete_paths.append(str(path))
                            except FileNotFoundError:
                                pass
                            except OSError:
                                pblog.error(f"Git LFS is bundled with Git, overriding your installed version. Please remove {path}.")
                                bundled_git_lfs = True

                if not is_admin and len(delete_paths) > 0:
                    pblog.info("Requesting permission to delete bundled Git LFS which is overriding your installed version...")
                    quoted_paths = [f'"{path}"' for path in delete_paths]
                    delete_cmdline = ["cmd.exe", "/c", "DEL", "/q", "/f"] + quoted_paths
                    try:
                        ret = pbuac.runAsAdmin(delete_cmdline)
                    except OSError:
                        pblog.error("User declined permission. Automatic delete failed.")

                for delete_path in delete_paths:
                    path = Path(delete_path)
                    if path.exists():
                        bundled_git_lfs = True
                        pblog.error(f"Git LFS is bundled with Git, overriding your installed version. Please remove {path}.")

                if bundled_git_lfs:
                    error_state()

        detected_lfs_version = pbgit.get_lfs_version()
        supported_lfs_version = pbconfig.get('supported_lfs_version')
        if detected_lfs_version == supported_lfs_version:
            pblog.info(f"Current Git LFS version: {detected_lfs_version}")
        else:
            pblog.error("Git LFS is not updated to the supported version in your system")
            pblog.error(f"Supported Git LFS Version: {supported_lfs_version}")
            pblog.error(f"Current Git LFS Version: {detected_lfs_version}")
            pblog.error("Please install the supported Git LFS version from https://git-lfs.github.com")
            if os.name == "nt":
                webbrowser.open(f"https://github.com/git-lfs/git-lfs/releases/download/v{supported_lfs_version}/git-lfs-windows-v{supported_lfs_version}.exe")
            needs_git_update = True

        detected_gcm_version = pbgit.get_gcm_version()
        supported_gcm_version_raw = pbconfig.get('supported_gcm_version')
        supported_gcm_version = f"{supported_gcm_version_raw}{pbconfig.get('supported_gcm_version_suffix')}"
        if detected_gcm_version == supported_gcm_version:
            pblog.info(f"Current Git Credential Manager Core version: {detected_gcm_version}")
        else:
            pblog.error("Git Credential Manager Core is not updated to the supported version in your system")
            pblog.error(f"Supported Git Credential Manager Core Version: {supported_gcm_version}")
            pblog.error(f"Current Git Credential Manager Core Version: {detected_gcm_version}")
            if detected_gcm_version.startswith("diff"):
                # remove the old credential helper (it may get stuck, and Core won't be able to install)
                pbtools.run_with_combined_output([pbgit.get_git_executable(), "config", "--unset-all", "credential.helper"])
                pbtools.run_with_combined_output([pbgit.get_git_executable(), "config", "--global", "--unset-all", "credential.helper"])
                exe_location = detected_gcm_version.split(".", 1)[1]
                # if they actually have a Windows program installed, inform them.
                if exe_location.endswith(".exe"):
                    pblog.error(f"It seems like you have another Git credential helper installed at: {exe_location}.")
                    pblog.error("Please uninstall this and Git Credential Manager Core if you have it in \"Add or remove programs\" and then install Git Credential Manager Core again.")
                else:
                    pblog.error("Please uninstall Git Credential Manager Core if you have it in \"Add or remove programs\" and then install Git Credential Manager Core again.")
            pblog.error("Please install the supported Git Credential Manager Core version from https://github.com/microsoft/Git-Credential-Manager-Core/releases")
            if os.name == "nt":
                webbrowser.open(f"https://github.com/microsoft/Git-Credential-Manager-Core/releases/download/v{supported_gcm_version}/gcmcore-win-x86-{supported_gcm_version_raw}.{pbconfig.get('gcm_download_suffix')}.exe")
            needs_git_update = True

        if needs_git_update:
            error_state()

        pblog.info("------------------")

        # Do some housekeeping for git configuration
        pbgit.setup_config()

        # Check if we have correct credentials
        pbgit.check_credentials()

        partial_sync = sync_val == "partial"
        is_ci = pbconfig.get("is_ci")

        status_out = pbtools.run_with_combined_output([pbgit.get_git_executable(), "status", "-uno"]).stdout
        # continue a trivial rebase
        if "rebase" in status_out:
            if pbtools.it_has_any(status_out, "nothing to commit", "git rebase --continue", "all conflicts fixed"):
                pbunreal.ensure_ue4_closed()
                rebase_out = pbtools.run_with_combined_output([pbgit.get_git_executable(), "rebase", "--continue"]).stdout
                if pbtools.it_has_any(rebase_out, "must edit all merge conflicts"):
                    # this is an improper state, since git told us otherwise before. abort all.
                    pbgit.abort_all()
            else:
                error_state("You are in the middle of a rebase. Changes on one of your commits will be overridden by incoming changes. Please request help in #tech-support to resolve conflicts, and please do not run UpdateProject until the issue is resolved.",
                                    fatal_error=True)

        current_branch = pbgit.get_current_branch_name()
        expected_branch = pbconfig.get('expected_branch_name')
        is_on_expected_branch = current_branch == expected_branch

        # undo single branch clone
        if not is_ci:
            pbtools.run([pbgit.get_git_executable(), "config", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*"])

        # repo was already fetched in UpdateProject for the expected branch, so do it here only for dev
        if not partial_sync and not is_on_expected_branch:
            pblog.info("Fetching recent changes on the repository...")
            fetch_base = [pbgit.get_git_executable(), "fetch", "origin"]
            branches = {expected_branch, "master", "trunk", current_branch}
            fetch_base.extend(branches)
            pbtools.get_combined_output(fetch_base)

            pblog.info("------------------")

        # Execute synchronization part of script if we're on the expected branch, or force sync is enabled
        if sync_val == "force" or is_on_expected_branch:
            if partial_sync:
                pbtools.maintain_repo()
            else:
                pbtools.resolve_conflicts_and_pull()

                pblog.info("------------------")

            project_version = pbunreal.get_project_version()
            is_custom_version = pbunreal.is_using_custom_version()
            if project_version is not None:
                if is_custom_version:
                    pblog.info(f"User selected project version: {project_version}")
                else:
                    pblog.info(f"Current project version: {project_version}")
            else:
                error_state("Something went wrong while fetching project version. Please request help in #tech-support.")

            checksum_json_path = pbconfig.get("checksum_file")
            if is_custom_version:
                # checkout old md5 from tag
                pbgit.sync_file(checksum_json_path, project_version)
            else:
                # force restore .md5 file
                pbgit.sync_file(checksum_json_path, "HEAD")

            if pbgh.is_pull_binaries_required():
                pblog.info("Binaries are not up to date, pulling new binaries...")
                ret = pbgh.pull_binaries(project_version)
                if ret == 0:
                    pblog.info("Binaries were pulled successfully")
                elif ret < 0:
                    error_state("Binaries pull failed, please view log for instructions.")
                elif ret > 0:
                    error_state("An error occurred while pulling binaries. Please request help in #tech-support to resolve it, and please do not run UpdateProject until the issue is resolved.", True)
            else:
                pblog.info("Binaries are up-to-date")

            # restore md5
            if is_custom_version:
                pbgit.sync_file(checksum_json_path, "HEAD")
        elif pbconfig.get_user("project", "autosync", default=False):
            pbtools.resolve_conflicts_and_pull()
        else:
            pblog.info(f"Current branch does not need auto synchronization: {pbgit.get_current_branch_name()}.")
            pbtools.maintain_repo()

        pblog.info("------------------")

        pblog.info("Checking for engine updates...")
        uproject_file = pbconfig.get('uproject_name')
        if pbgit.sync_file(uproject_file) != 0:
            error_state("Something went wrong while updating the .uproject file. Please request help in #tech-support.")

        engine_version = pbunreal.get_engine_version_with_prefix()

        pblog.info("Registering current engine build if it exists. Otherwise, the build will be downloaded...")

        symbols_needed = pbunreal.is_versionator_symbols_enabled()
        bundle_name = pbconfig.get("ue4v_default_bundle")

        if pbunreal.download_engine(bundle_name, symbols_needed):
            pblog.info(f"Engine build {bundle_name}-{engine_version} successfully registered")
        else:
            error_state(f"Something went wrong while registering engine build {bundle_name}-{engine_version}. Please request help in #tech-support.")

        # Clean old engine installations, do that only in expected branch
        if is_on_expected_branch:
            if pbunreal.clean_old_engine_installations():
                pblog.info("Old engine installations are successfully cleaned")
            else:
                pblog.warning("Something went wrong while cleaning old engine installations. You may want to clean them manually.")

        pblog.info("------------------")

        pbunreal.update_source_control()

        if pbunreal.check_ue4_file_association() and pbunreal.is_ue4_closed():
            path = str(Path(uproject_file).resolve())
            try:
                os.startfile(path)
            except NotImplementedError:
                if sys.platform.startswith('linux'):
                    pbtools.run_non_blocking([f"xdg-open {path}"])
                else:
                    pblog.info(f"You may now launch {uproject_file} with Unreal Engine 4.")
        else:
            error_state(".uproject extension is not correctly set into Unreal Engine. Make sure you have Epic Games Launcher installed. If problem still persists, please get help in #tech-support.")

    elif sync_val == "engineversion":
        repository_val = pbunreal.get_versionator_gsuri(repository_val)
        if repository_val is None:
                error_state("--repository <URL> argument should be provided with --sync engine command")
        engine_version = pbunreal.get_latest_available_engine_version(str(repository_val))
        if engine_version is None:
            error_state("Error while fetching latest engine version")
        if not pbunreal.set_engine_version(engine_version):
            error_state("Error while updating engine version in .uproject file")
        pblog.info(f"Successfully changed engine version as {str(engine_version)}")

    elif sync_val == "ddc":
        pbunreal.generate_ddc_data()

    elif sync_val == "binaries":
        project_version = pbunreal.get_project_version()
        ret = pbgh.pull_binaries(project_version, True)
        if ret == 0:
            pblog.info(f"Binaries for {project_version} pulled and extracted successfully")
        else:
            error_state(f"Failed to pull binaries for {project_version}")

    elif sync_val == "engine":
        # Pull engine build with ue4versionator and register it
        if requested_bundle_name is None:
            requested_bundle_name = pbconfig.get("ue4v_default_bundle")

        engine_version = pbunreal.get_engine_version_with_prefix()
        symbols_needed = pbunreal.is_versionator_symbols_enabled()
        if pbunreal.download_engine(requested_bundle_name, symbols_needed):
            pblog.info(f"Engine build {requested_bundle_name}-{engine_version} successfully registered")
            if pbconfig.get("is_ci"):
                keep = 3
                pblog.info(f"Keeping the last {keep} engine versions and removing the rest.")
                pbunreal.clean_old_engine_installations(keep=keep)
        else:
            error_state(f"Something went wrong while registering engine build {requested_bundle_name}-{engine_version}")


def clean_handler(clean_val):
    if clean_val == "workspace":
        if pbtools.wipe_workspace():
            pblog.info("Workspace wipe successful")
        else:
            error_state("Something went wrong while wiping the workspace")

    elif clean_val == "engine":
        if not pbunreal.clean_old_engine_installations():
            error_state(
                "Something went wrong while cleaning old engine installations. You may want to clean them manually.")


def printversion_handler(print_val, repository_val=None):
    if print_val == "latest-engine":
        repository_val = pbunreal.get_versionator_gsuri(repository_val)
        if repository_val is None:
            error_state("--repository <URL> argument should be provided with --print latest-engine command")
        engine_version = pbunreal.get_latest_available_engine_version(str(repository_val))
        if engine_version is None:
            error_state("Could not find latest engine version.")
        print(engine_version, end="")

    elif print_val == "current-engine":
        engine_version = pbunreal.get_engine_version()
        if engine_version is None:
            error_state("Could not find latest engine version.")
        print(engine_version, end="")

    elif print_val == "project":
        project_version = pbunreal.get_project_version()
        if project_version is None:
            error_state("Could not find latest engine version.")
        print(project_version, end="")


def autoversion_handler(autoversion_val):
    if pbunreal.project_version_increase(autoversion_val):
        pblog.info("Successfully increased project version")
    else:
        error_state("Error occurred while increasing project version")


def publish_handler(publish_val, dispatch_exec_path):
    if dispatch_exec_path is None:
        error_state(
            "--dispatch argument should be provided for --publish command", hush=True)

    if not pbdispatch.push_build(publish_val, dispatch_exec_path, pbconfig.get('dispatch_config'), pbconfig.get('dispatch_stagedir'), pbconfig.get('dispatch_drm')):
       error_state("Something went wrong while pushing a new playable build.")


def main(argv):
    parser = argparse.ArgumentParser(description=f"Project Borealis Workspace Synchronization Tool | PBpy Library Version: {pbpy_version.ver} | PBSync Program Version: {pbsync_version.ver}")

    parser.add_argument("--sync", help="Main command for the PBSync, synchronizes the project with latest changes from the repo, and does some housekeeping",
                        choices=["all", "partial", "binaries", "engineversion", "engine", "force", "ddc"])
    parser.add_argument("--printversion", help="Prints requested version information into console.",
                        choices=["current-engine", "latest-engine", "project"])
    parser.add_argument(
        "--repository", help="gcloud repository url for --printversion latest-engine and --sync engine commands")
    parser.add_argument("--autoversion", help="Automatic version update for project version",
                        choices=["hotfix", "stable", "public"])
    parser.add_argument("--clean", help="""Do cleanup according to specified argument. If engine is provided, old engine installations will be cleared
    If workspace is provided, workspace will be reset with latest changes from current branch (not revertible)""", choices=["engine", "workspace"])
    parser.add_argument("--config", help=f"Path of config XML file. If not provided, ./{default_config_name} is used as default", default=default_config_name)
    parser.add_argument("--publish", help="Publishes a playable build with provided build type",
                        choices=["internal", "playtester"])
    parser.add_argument(
        "--dispatch", help="Required dispatch executable path for --publish command")
    parser.add_argument(
        "--bundle", help="Engine bundle name for --sync engine command. If not provided, engine download will use the default bundle supplied by the config file")
    parser.add_argument(
        "--debugpath", help="If provided, PBSync will run in provided path")
    parser.add_argument(
        "--debugbranch", help="If provided, PBSync will use provided branch as expected branch")

    if len(argv) > 0:
        args = parser.parse_args(argv)
    else:
        pblog.error("At least one valid argument should be passed!")
        pblog.error("Did you mean to launch UpdateProject?")
        input("Press enter to continue...")
        error_state(hush=True, term=True)

    if not (args.debugpath is None):
        # Work on provided debug path
        os.chdir(str(args.debugpath))

    # Parser function object for PBSync config file
    def pbsync_config_parser_func(root): return {
        'supported_git_version': root.find('git/version').text,
        'supported_lfs_version': root.find('git/lfsversion').text,
        'supported_gcm_version': root.find('git/gcmversion').text,
        'supported_gcm_version_suffix': root.find('git/gcmversionsuffix').text,
        'gcm_download_suffix': root.find('git/gcmsuffix').text,
        'expected_branch_name': root.find('git/expectedbranch').text if args.debugbranch is None else str(args.debugbranch),
        'git_url': root.find('git/url').text,
        'checksum_file': root.find('git/checksumfile').text,
        'log_file_path': root.find('log/file').text,
        'ue4v_user_config': root.find('versionator/userconfig').text,
        'ue4v_ci_config': root.find('versionator/ciconfig').text,
        'ue4v_default_bundle': root.find('versionator/defaultbundle').text,
        'ue4v_ci_bundle': root.find('versionator/cibundle').text,
        'engine_base_version': root.find('project/enginebaseversion').text,
        'uproject_name': root.find('project/uprojectname').text,
        'defaultgame_path': root.find('project/defaultgameinipath').text,
        'dispatch_config': root.find('dispatch/config').text,
        'dispatch_drm': root.find('dispatch/drm').text,
        'dispatch_stagedir': root.find('dispatch/stagedir').text
    }

    # Preparation
    config_handler(args.config, pbsync_config_parser_func)
    pblog.setup_logger(pbconfig.get('log_file_path'))

    # Do not process further if we're in an error state
    if pbtools.check_error_state():
        error_state(f"""Repository is currently in an error state. Please fix the issues in your workspace 
        before running PBSync.\nIf you have already fixed the problem, you may remove {pbtools.error_file} from your project folder and 
        run UpdateProject again.""", True)

    # Parse args
    if not (args.sync is None):
        sync_handler(args.sync, args.repository, args.bundle)
    elif not (args.printversion is None):
        printversion_handler(args.printversion, args.repository)
    elif not (args.autoversion is None):
        autoversion_handler(args.autoversion)
    elif not (args.clean is None):
        clean_handler(args.clean)
    elif not (args.publish is None):
        publish_handler(args.publish, args.dispatch)
    else:
        pblog.error("At least one valid argument should be passed!")
        pblog.error("Did you mean to launch UpdateProject?")
        input("Press enter to continue...")
        error_state(hush=True)

    pbconfig.shutdown()

if __name__ == '__main__':
    if "Scripts" in os.getcwd():
        # Working directory fix for scripts calling PBSync from Scripts folder
        os.chdir("..")
    main(sys.argv[1:])
