import os

from pbpy import pblog, pbtools, pbconfig

default_drm_exec_name = "ProjectBorealis.exe"
exec_max_allowed_size = 104857600 # 100mb

# DISPATCH_APP_ID: App ID. env. variable for dispatch application
# DISPATCH_INTERNAL_BID: Branch ID env. variable for internal builds
# DISPATCH_PLAYTESTER_BID: Branch ID env. variable for playtester builds


def push_build(branch_type, dispath_exec_path, dispatch_config, dispatch_stagedir, dispatch_apply_drm_path):
    # Test if our configuration values exist
    app_id = pbconfig.get_user('dispatch', 'app_id')
    if app_id is None or app_id == "":
        pblog.error("dispatch.app_id was not configured.")
        return False

    if branch_type == "internal":
        branch_id_key = 'internal_bid'
    elif branch_type == "playtester":
        branch_id_key = 'playtester_bid'
        pblog.error("Playtester builds are not allowed at the moment.")
        return False
    else:
        pblog.error("Unknown Dispatch branch type specified.")
        return False

    branch_id = pbconfig.get_user('dispatch', branch_id_key)
    if branch_id is None or branch_id == "":
        pblog.error(f"{branch_id_key} was not configured.")
        return False

    executable_path = None
    for file in os.listdir(dispatch_apply_drm_path):
        if file.endswith(".exe"):
            executable_path = os.path.join(dispatch_apply_drm_path, str(file))

    if executable_path is None:
        pblog.error(f"Executable {dispatch_apply_drm_path} not found while attempting to apply DRM wrapper.")
        return False

    if os.path.getsize(executable_path) > exec_max_allowed_size:
        executable_path = dispatch_apply_drm_path
        for i in range(3):
            executable_path = os.path.join(executable_path, "..")
        executable_path = os.path.abspath(executable_path)
        executable_path = os.path.join(executable_path, default_drm_exec_name)

    # Wrap executable with DRM
    if False:
        proc = pbtools.run_with_combined_output([dispath_exec_path, "build", "drm-wrap", app_id, executable_path])
        pblog.info(proc.stdout)
        result = proc.returncode
        if result != 0:
            return False

    # Push and Publish the build
    proc = pbtools.run_with_combined_output([dispath_exec_path, "build", "push", branch_id, dispatch_config, dispatch_stagedir, "-p"])
    pblog.info(proc.stdout)
    result = proc.returncode
    return result == 0
