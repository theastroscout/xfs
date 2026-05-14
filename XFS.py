import sublime
import sublime_plugin
import os
import subprocess
from shutil import copyfile, rmtree
import json
import re

# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def statusbar(msg):
    sublime.active_window().status_message(' >>> [ XFS ] ' + msg)
    print('[XFS]', msg)


def confirm(title, message):
    """Show a yes/no dialog. Returns True if user confirms."""
    return sublime.ok_cancel_dialog(message, ok_title='Yes', title=title)


def run_cmd(cmd):
    """Run a shell command and return (returncode, stdout, stderr)."""
    proc = subprocess.Popen(
        cmd, shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    out, err = proc.communicate()
    return proc.returncode, out.decode('utf-8'), err.decode('utf-8')


def shell_quote(path):
    """Wrap a path in single quotes, escaping any single quotes within."""
    return "'" + path.replace("'", "'\\''") + "'"


# ─────────────────────────────────────────────
#  Config
# ─────────────────────────────────────────────

# Config file name — always excluded from every operation
CONFIG_FILE = 'xfs-config.json'


def get_config(path):
    """
    Walk up the directory tree looking for xfs-config.json.
    Returns an enriched conf dict, or False if none found.
    """
    chunks = path.split('/')
    while chunks:
        local_dir = '/'.join(chunks)
        config_path = local_dir + '/' + CONFIG_FILE
        if os.path.isfile(config_path):
            try:
                with open(config_path) as f:
                    conf = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                statusbar('Error reading config: {}'.format(e))
                return False

            conf['_filePath'] = path
            conf['_localDir'] = local_dir

            if os.path.isfile(path):
                conf['_fileName'] = os.path.basename(path)
                conf['_clearDir'] = os.path.dirname(path.replace(local_dir, ''))
            else:
                conf['_fileName'] = False
                conf['_clearDir'] = path.replace(local_dir, '')

            if conf['_clearDir'] + '/' == local_dir:
                conf['_clearDir'] = ''

            # Always protect xfs-config.json — append if not already listed
            exclude = list(conf.get('exclude', []))
            if CONFIG_FILE not in exclude:
                exclude.append(CONFIG_FILE)

            # Build rsync --exclude flags
            exclude_flags = ['--exclude={}'.format(p.strip().strip('/')) for p in exclude]
            conf['excludePattern'] = ' '.join(exclude_flags)
            conf['exclude'] = exclude

            return conf

        chunks.pop()

    return False


# ─────────────────────────────────────────────
#  Core operations
# ─────────────────────────────────────────────

def upload(conf):
    """Upload a file or folder to the remote server."""
    remote_base = conf['remoteDir'] + conf['_clearDir']

    # Ensure remote directory exists
    rc, _, err = run_cmd('ssh {} "mkdir -p {}"'.format(
        conf['ssh'], shell_quote(remote_base)))
    if rc != 0:
        statusbar('mkdir failed: ' + err.strip())
        return False

    remote_dir = remote_base + '/'
    local_dir  = conf['_localDir'] + conf['_clearDir'] + '/'

    if conf['_fileName']:
        file_name   = conf['_fileName']
        local_file  = local_dir + file_name
        remote_file = remote_dir + file_name
        # No --chmod: let the server assign ownership/perms via the SSH cert user
        cmd = 'rsync -az {} {}:{}'.format(
            shell_quote(local_file),
            conf['ssh'],
            shell_quote(remote_file)
        )
        rc, _, err = run_cmd(cmd)
        if rc == 0:
            statusbar('File uploaded: ' + file_name)
        else:
            statusbar('Upload failed: ' + err.strip())
    else:
        cmd = 'rsync -az {} {} {}:{}'.format(
            conf['excludePattern'],
            shell_quote(local_dir),
            conf['ssh'],
            shell_quote(remote_dir)
        )
        rc, _, err = run_cmd(cmd)
        if rc == 0:
            statusbar('Folder uploaded')
        else:
            statusbar('Folder upload failed: ' + err.strip())

    return rc == 0


def download(conf):
    """Download a file or folder from the remote server."""
    remote_base = conf['remoteDir'] + conf['_clearDir']

    if conf['_fileName']:
        file_name   = conf['_fileName']

        # Respect exclude list
        for pattern in conf.get('exclude', []):
            p = pattern.strip('/')
            if file_name == p or file_name.endswith('/' + p):
                statusbar('Skipped excluded file: ' + p)
                return False

        remote_file = remote_base + '/' + file_name
        local_file  = conf['_localDir'] + conf['_clearDir'] + '/' + file_name
        cmd = 'rsync -az {}:{} {}'.format(
            conf['ssh'],
            shell_quote(remote_file),
            shell_quote(local_file)
        )
        rc, _, err = run_cmd(cmd)
        if rc == 0:
            statusbar('File downloaded: ' + file_name)
        else:
            statusbar('Download failed: ' + err.strip())
        return rc == 0

    else:
        remote_dir = remote_base + '/'
        local_dir  = conf['_localDir'] + conf['_clearDir'] + '/'
        statusbar('Downloading folder…')
        cmd = 'rsync -az {} {}:{} {}'.format(
            conf['excludePattern'],
            conf['ssh'],
            shell_quote(remote_dir),
            shell_quote(local_dir)
        )
        rc, _, err = run_cmd(cmd)
        if rc == 0:
            statusbar('Folder downloaded')
        else:
            statusbar('Folder download failed: ' + err.strip())
        return rc == 0


def delete(conf, window, sync_type=False):
    """
    Delete remote file/folder, and optionally the local copy too.
    Always asks for confirmation first.
    sync_type: 'remote' | 'both'
    """
    target = conf['_fileName'] or os.path.basename(conf['_clearDir'])
    scope  = 'remote only' if sync_type != 'both' else 'remote AND local'

    if not confirm(
        'XFS — Confirm Delete',
        'Delete {} ({})?\n\n{}'.format(target, scope,
            'This cannot be undone.' if sync_type == 'both'
            else 'Local copy will be kept.')
    ):
        statusbar('Delete cancelled')
        return False

    if conf['_fileName']:
        remote_path = '{}{}/{}'.format(
            conf['remoteDir'], conf['_clearDir'], conf['_fileName'])
        rc, _, err = run_cmd('ssh {} "rm -f {}"'.format(
            conf['ssh'], shell_quote(remote_path)))

        if rc != 0:
            statusbar('Remote delete failed: ' + err.strip())
            return False

        if sync_type == 'both':
            local_path = '{}{}/{}'.format(
                conf['_localDir'], conf['_clearDir'], conf['_fileName'])
            if os.path.exists(local_path):
                os.remove(local_path)
            sublime.set_timeout(lambda: window.run_command('revert'), 10)
            statusbar('Remote & local file deleted')
        else:
            statusbar('Remote file deleted')

    else:
        remote_path = conf['remoteDir'] + conf['_clearDir']
        rc, _, err = run_cmd('ssh {} "rm -rf {}"'.format(
            conf['ssh'], shell_quote(remote_path)))

        if rc != 0:
            statusbar('Remote delete failed: ' + err.strip())
            return False

        if sync_type == 'both':
            local_path = conf['_localDir'] + conf['_clearDir']
            if os.path.exists(local_path):
                rmtree(local_path)
            statusbar('Remote & local folder deleted')
        else:
            statusbar('Remote folder deleted')

    return True


def sync(conf, target='local'):
    """
    Bidirectional sync helper.
    target='remote' : push local → remote
    target='local'  : pull remote → local
    """
    local_dir  = conf['_localDir'] + conf['_clearDir']
    remote_dir = conf['remoteDir'] + conf['_clearDir']

    if not local_dir.endswith('/'):
        local_dir += '/'
    if not remote_dir.endswith('/'):
        remote_dir += '/'

    if target == 'remote':
        statusbar('Syncing local → remote…')
        cmd = 'rsync -az --delete --delete-excluded {} {} {}:{}'.format(
            conf['excludePattern'],
            shell_quote(local_dir),
            conf['ssh'],
            shell_quote(remote_dir)
        )
    else:
        statusbar('Syncing remote → local…')
        # No --delete-excluded here: excluded files (e.g. xfs-config.json)
        # must never be removed from the local side even if absent on remote.
        cmd = 'rsync -az --delete {} {}:{} {}'.format(
            conf['excludePattern'],
            conf['ssh'],
            shell_quote(remote_dir),
            shell_quote(local_dir)
        )

    rc, out, err = run_cmd(cmd)
    if out:
        print('[XFS sync]', out)
    if err:
        print('[XFS sync err]', err)

    if rc == 0:
        statusbar('Sync complete ({} → {})'.format(
            'local', 'remote') if target == 'remote' else 'Sync complete (remote → local)')
    else:
        statusbar('Sync failed: ' + err.strip())

    return rc == 0


# ─────────────────────────────────────────────
#  Rename (global state — Sublime input panel)
# ─────────────────────────────────────────────

_rename_conf = None


def rename(new_name=False):
    global _rename_conf
    if not new_name:
        _rename_conf = None
        return

    conf = _rename_conf

    if conf['_fileName']:
        remote_dir      = conf['remoteDir'] + conf['_clearDir'] + '/'
        old_remote_file = remote_dir + conf['_fileName']
        new_remote_file = remote_dir + new_name
        rc, _, err = run_cmd('ssh {} "mv {} {}"'.format(
            conf['ssh'],
            shell_quote(old_remote_file),
            shell_quote(new_remote_file)
        ))
        if rc != 0:
            statusbar('Remote rename failed: ' + err.strip())
            return

        local_dir      = conf['_localDir'] + conf['_clearDir'] + '/'
        old_local_file = local_dir + conf['_fileName']
        new_local_file = local_dir + new_name
        os.rename(old_local_file, new_local_file)
        statusbar('File renamed')

    else:
        old_folder_name = os.path.basename(conf['_clearDir'])
        root_changed    = conf['_filePath'] == conf['_clearDir']

        old_remote_folder = (conf['remoteDir']
                             if root_changed
                             else conf['remoteDir'] + conf['_clearDir'] + '/')
        new_remote_folder = re.sub(
            re.escape(old_folder_name) + r'/?$',
            new_name,
            old_remote_folder
        )
        if not new_remote_folder.endswith('/'):
            new_remote_folder += '/'

        old_local_folder = conf['_filePath']
        new_local_folder = re.sub(
            re.escape(old_folder_name) + r'$',
            new_name,
            old_local_folder
        )

        rc, _, err = run_cmd('ssh {} "mv {} {}"'.format(
            conf['ssh'],
            shell_quote(old_remote_folder),
            shell_quote(new_remote_folder)
        ))
        if rc != 0:
            statusbar('Remote rename failed: ' + err.strip())
            return

        if root_changed:
            config_path = conf['_localDir'] + '/' + CONFIG_FILE
            try:
                with open(config_path) as f:
                    raw = json.load(f)
                raw['remoteDir'] = new_remote_folder
                with open(config_path, 'w') as f:
                    json.dump(raw, f, indent=4)
            except OSError as e:
                statusbar('Could not update config: ' + str(e))

        os.rename(old_local_folder, new_local_folder)
        statusbar('Folder renamed')


# ─────────────────────────────────────────────
#  Upload-on-save: skip newly created files
# ─────────────────────────────────────────────

class XfsSyncCommand(sublime_plugin.ViewEventListener):
    """
    Uploads on every save EXCEPT the very first save of a brand-new file.

    Detection: on_pre_save checks whether the file exists on disk yet.
    If it doesn't, this save is the creation event — flag it and skip once.
    Every subsequent save (file already on disk) uploads normally.
    """

    # view ids whose current save is a creation event — skip upload once
    _creating = set()

    @classmethod
    def is_applicable(cls, settings):
        return True

    def on_pre_save(self):
        file_name = self.view.file_name()
        if file_name and not os.path.exists(file_name):
            XfsSyncCommand._creating.add(self.view.id())

    def on_post_save(self):
        file_name = self.view.file_name()
        if not file_name:
            return

        # Creation save — skip upload, clear the flag
        if self.view.id() in XfsSyncCommand._creating:
            XfsSyncCommand._creating.discard(self.view.id())
            statusbar('New file created — skipping upload')
            return

        conf = get_config(file_name)
        if not conf or not conf.get('upload_on_save'):
            return

        # Respect exclude list
        rel_path  = os.path.relpath(file_name, conf['_localDir'])
        base_name = os.path.basename(file_name)
        for pattern in conf.get('exclude', []):
            p = pattern.strip('/')
            if base_name == p or rel_path.startswith(p + os.sep) or rel_path == p:
                statusbar('Skipped excluded file: ' + p)
                return

        upload(conf)

    def on_close(self):
        XfsSyncCommand._creating.discard(self.view.id())


# ─────────────────────────────────────────────
#  Window commands — Files
# ─────────────────────────────────────────────

class XfsUploadFileCommand(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        conf = get_config(paths[0])
        if conf:
            upload(conf)

    def is_visible(self, paths=[]):
        return bool(paths) and os.path.isfile(paths[0]) and bool(get_config(paths[0]))


class XfsDownloadFileCommand(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        conf = get_config(paths[0])
        if conf:
            download(conf)

    def is_visible(self, paths=[]):
        return bool(paths) and os.path.isfile(paths[0]) and bool(get_config(paths[0]))


class XfsDeleteRemoteFileCommand(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        conf = get_config(paths[0])
        if conf:
            delete(conf, self.window, 'remote')

    def is_visible(self, paths=[]):
        return bool(paths) and os.path.isfile(paths[0]) and bool(get_config(paths[0]))


class XfsDeleteBothFilesCommand(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        conf = get_config(paths[0])
        if conf:
            delete(conf, self.window, 'both')

    def is_visible(self, paths=[]):
        return bool(paths) and os.path.isfile(paths[0]) and bool(get_config(paths[0]))


class XfsRenameFileCommand(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        conf = get_config(paths[0])
        if not conf:
            return
        global _rename_conf
        _rename_conf = conf
        self.window.show_input_panel(
            'Rename File', conf['_fileName'], rename, None, rename)

    def is_visible(self, paths=[]):
        return bool(paths) and os.path.isfile(paths[0]) and bool(get_config(paths[0]))


# ─────────────────────────────────────────────
#  Window commands — Folders
# ─────────────────────────────────────────────

class XfsUploadFolderCommand(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        conf = get_config(paths[0])
        if conf:
            upload(conf)

    def is_visible(self, paths=[]):
        return bool(paths) and os.path.isdir(paths[0]) and bool(get_config(paths[0]))


class XfsDownloadFolderCommand(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        conf = get_config(paths[0])
        if conf:
            download(conf)

    def is_visible(self, paths=[]):
        return bool(paths) and os.path.isdir(paths[0]) and bool(get_config(paths[0]))


class XfsSyncLocalFolderCommand(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        conf = get_config(paths[0])
        if conf:
            sync(conf, 'local')

    def is_visible(self, paths=[]):
        return bool(paths) and os.path.isdir(paths[0]) and bool(get_config(paths[0]))


class XfsSyncRemoteFolderCommand(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        conf = get_config(paths[0])
        if conf:
            sync(conf, 'remote')

    def is_visible(self, paths=[]):
        return bool(paths) and os.path.isdir(paths[0]) and bool(get_config(paths[0]))


class XfsDeleteRemoteFolderCommand(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        conf = get_config(paths[0])
        if conf:
            delete(conf, self.window, 'remote')

    def is_visible(self, paths=[]):
        return bool(paths) and os.path.isdir(paths[0]) and bool(get_config(paths[0]))


class XfsDeleteBothFoldersCommand(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        conf = get_config(paths[0])
        if conf:
            delete(conf, self.window, 'both')

    def is_visible(self, paths=[]):
        return bool(paths) and os.path.isdir(paths[0]) and bool(get_config(paths[0]))


class XfsRenameFolderCommand(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        conf = get_config(paths[0])
        if not conf:
            return
        global _rename_conf
        _rename_conf = conf
        self.window.show_input_panel(
            'Rename Folder',
            os.path.basename(conf['_clearDir']),
            rename, None, rename
        )

    def is_visible(self, paths=[]):
        return bool(paths) and os.path.isdir(paths[0]) and bool(get_config(paths[0]))


# ─────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────

class XfsConfigurationCommand(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        if not paths:
            return
        conf_path = paths[0] + '/' + CONFIG_FILE
        if not os.path.isfile(conf_path):
            default = sublime.packages_path() + '/XFS/XFS.default-config'
            try:
                copyfile(default, conf_path)
            except OSError as e:
                statusbar('Could not create config: ' + str(e))
                return
        self.window.open_file(conf_path, sublime.ENCODED_POSITION)

    def is_visible(self, paths=[]):
        return True