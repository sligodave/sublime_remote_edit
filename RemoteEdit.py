
import os
import os.path
import tempfile
import subprocess

import sublime
import sublime_plugin


def log(msg):
    """
    Simple logging function
    """
    if get_settings().get('debug', False):
        print('[Remote Edit] ' + str(msg))


def get_settings(window=None, create_if_missing=None):
    """
    Look in the current project file and also the main settings file for settings.
    """
    if not window:
        window = sublime.active_window()

    settings = {
        'debug': False,
        'create_if_missing': create_if_missing,
        'ssh_configs': {}
    }

    for sub_settings in [
        sublime.load_settings('RemoteEdit.sublime-settings'),
        window.project_data().get('remote_edit')
    ]:
        if sub_settings is None:
            continue

        sub_settings = {} if not sub_settings else sub_settings

        if create_if_missing is not None:
            create_if_missing = sub_settings.get('create_if_missing', False)
            if isinstance(create_if_missing, bool):
                settings['create_if_missing'] = create_if_missing

        if isinstance(sub_settings.get('debug'), bool):
            settings['debug'] = sub_settings.get('debug')

        ssh_configs = sub_settings.get("ssh_configs")
        ssh_configs = {} if not isinstance(ssh_configs, dict) else ssh_configs
        settings['ssh_configs'].update(ssh_configs)

    return settings


def get_ssh_listing(address, path, warn=True):
    command = 'ssh -o StrictHostKeychecking=no "%s" ls -aF "%s"' % (address, path)
    log('Command: \'%s\'' % command)

    pipe = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    )
    pipe.wait()
    communication = pipe.communicate()
    return_code = pipe.returncode
    log('Return Code: %d' % return_code)
    log('BACK: %s' % str(communication))
    error_message = None
    items = None
    if return_code == 1 or communication[1].strip():
        error_message = communication[1].decode('utf8')
        # We have an error
        if error_message:
            log('Error: %s' % error_message)
        if warn:
            sublime.message_dialog('[Remote Edit] Could not get directory listing for "%s" from "%s".\n%s' % (
                                                                path, address, error_message))
    else:
        items = communication[0].decode('utf8')
        items = [x.strip() for x in items.split('\n') if x.strip()]
    return {'error': error_message, 'items': items}


def scp(from_path, to_path, create_if_missing=False):
    """
    Call out to the command line scp.
    Note: We don't do any authentication.
    You must have a ssh key set up.

    IMPORTANT: If you try to write to a file you don't
    have write permissions on you will not get an error!
    """
    command = 'scp -o StrictHostKeychecking=no "%s" "%s"' % (from_path, to_path)
    log('Command: \'%s\'' % command)

    pipe = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    )
    pipe.wait()
    communication = pipe.communicate()
    return_code = pipe.returncode
    log('Return Code: %d' % return_code)
    log('BACK: %s' % str(communication))
    if return_code == 1:
        error_message = communication[1].decode('utf8')
        # We have an error
        if error_message:
            log('Error: %s' % error_message)
            # It's not a missing error or src is local and it's missing or
            # we aren't creating if remote src is missing
            if not 'no such file or directory' in error_message.lower() or\
                'please try again' in error_message.lower() or\
                from_path.find('@') == -1 or not create_if_missing:
                sublime.error_message(error_message)
            # Else if it is a missing remote src error
            elif to_path.find('@') == -1 and create_if_missing:
                # We were copying to local machine
                # and file doesn't exist on remote machine
                sublime.message_dialog('[Remote Edit] Could not get file, so creating it')
                open(to_path, 'w').close()
            else:
                sublime.message_dialog('[Remote Edit] Could not get file, not creating it')


class RemoteEditOpenRemoteFilePromptCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.settings = get_settings(self.window)

        self.all_aliases = []
        self.path = './'

        for alias, ssh_config in self.settings['ssh_configs'].items():
            alias = [alias, 'Address: %s' % ssh_config.get('address', alias)]
            self.all_aliases.append(alias)
        self.all_aliases.sort(key=lambda x: x[0])
        self.all_aliases.append(['', 'MANUAL - Supply the settings now.'])
        self.window.show_quick_panel(self.all_aliases, self.on_alias_done)

    def on_alias_done(self, selection):
        if selection < 0 or selection >= len(self.all_aliases):
            return
        if selection == len(self.all_aliases) - 1:
            self.window.show_input_panel(
                '[USERNAME@]SERVER',
                '',
                self.on_manual_done,
                None,
                None
            )
        else:
            self.alias = self.all_aliases[selection][0]
            self.ssh_config = self.settings['ssh_configs'][self.alias]
            self.get_path()

    def on_manual_done(self, address):
        self.ssh_config = {}
        if '@' in address:
            username, address = address.split('@', 1)
            self.ssh_config['username'] = username
        self.alias = address
        self.get_path()

    def get_path(self, selection=None):
        if selection == -1:
            return
        if selection is not None:
            self.path += self.items[selection]
        if not self.path.endswith('/') and not self.path.endswith('@'):
            self.window.run_command(
                'remote_edit_open_remote_file',
                {'alias': self.alias, 'path': self.path}
            )
            return

        address = self.ssh_config.get('address', self.alias)
        if 'username' in self.ssh_config:
            address = '%s@%s' % (self.ssh_config['username'], address)
        # TODO: Allow for a starting directory in the settings
        link = False
        if self.path.endswith('@'):
            self.path = self.path[:-1] + '/'
            link = True
        result = get_ssh_listing(address, self.path, not link)
        if link and result['error'] is not None:
            log('Link Failback, "%s" is not a directory. Trying file.' % self.path)
            self.window.run_command(
                'remote_edit_open_remote_file',
                {'alias': self.alias, 'path': self.path[:-1]}
            )
        else:
            self.items = result.get('items')
            if self.items == None:
                return
            sublime.set_timeout(lambda: self.window.show_quick_panel(self.items, self.get_path), 0)


class RemoteEditOpenRemoteFileCommand(sublime_plugin.WindowCommand):
    def run(
            self,
            alias,
            path,
            create_if_missing=None
        ):
        """
        Given a settings alias and a path to a file on a remote server.
        Scp the file to a temp location on the local machine and open
        for editing. Record a record of the file so we know where to
        save it back to on the remote server, on save.
        """
        log('Open: %s "%s" %s' % (alias, path, create_if_missing))

        settings = get_settings(self.window, create_if_missing=create_if_missing)
        create_if_missing = settings['create_if_missing']
        ssh_config = settings['ssh_configs'].get(alias)
        if ssh_config is None:
            sublime.error_message('[Remote Edit] Cound not find ssh config alias "%s".' % alias)
            return

        log('SSH Config: %s' % str(ssh_config))

        line_no = '0'
        real_path = path
        if ':' in path:
            real_path, line_no = path.split(':', 1)

        scp_path = '%s:%s' % (ssh_config.get('address', alias), real_path)
        if 'username' in ssh_config:
            scp_path = '%s@%s' % (ssh_config['username'], scp_path)

        # Do we already have this remote file open?
        view = temp_path = None
        for cur_view in self.window.views():
            settings = cur_view.settings()
            if settings.get('remote_edit_scp_path') == scp_path:
                view = cur_view
                break
        else:
            temp_path = os.path.join(tempfile.mkdtemp(), os.path.basename(real_path))

            scp(scp_path, temp_path, create_if_missing)

            if not os.path.exists(temp_path):
                return

            view = self.window.open_file(temp_path)
            settings = view.settings()
            settings.set('remote_edit_alias', alias)
            settings.set('remote_edit_path', path)
            settings.set('remote_edit_scp_path', scp_path)
            settings.set('remote_edit_temp_path', temp_path)
            settings.set('remote_edit_create_if_missing', create_if_missing)

        log('Opened: "%s"' % scp_path)
        log('Temp: "%s"' % temp_path)
        self.window.focus_view(view)

        if line_no and line_no.isdigit():
            view.sel().clear()
            point = view.text_point(int(line_no), 0)
            region = sublime.Region(point, point)
            view.sel().add(region)
            view.show(region)


class RemoteEditReloadRemoteFileCommand(sublime_plugin.WindowCommand):
    def run(self, all=False):
        active_view = self.window.active_view()
        if all:
            views = self.window.views()
        else:
            views = [active_view]
        for view in views:
            settings = view.settings()
            if settings.get('remote_edit_scp_path') and\
                settings.get('remote_edit_temp_path'):
                save_as_active = False
                if view == active_view:
                    save_as_active = True
                self.window.focus_view(view)
                self.window.run_command('close')
                self.window.run_command(
                    'remote_edit_open_remote_file',
                    {
                        'alias': settings.get('remote_edit_alias'),
                        'path': settings.get('remote_edit_path'),
                        'create_if_missing': settings.get('remote_edit_create_if_missing')
                    }
                )
                active_view = self.window.active_view()
        self.window.focus_view(active_view)


class RemoteEditListener(sublime_plugin.EventListener):
    def on_post_save(self, view):
        """
        When a remote file is saved, save it back to the remote server.
        """
        settings = view.settings()
        if settings.has('remote_edit_create_if_missing') and\
            settings.has('remote_edit_scp_path') and\
            settings.has('remote_edit_temp_path'):
            log('Saved: "%s"' % settings.get('remote_edit_scp_path'))
            scp(
                settings.get('remote_edit_temp_path'),
                settings.get('remote_edit_scp_path'),
                settings.get('remote_edit_create_if_missing')
            )

    def on_close(self, view):
        """
        When a remote file is closed delete the local temp file and directory.
        We also no longer keep a record of it in our remote files list.
        """
        settings = view.settings()
        if settings.has('remote_edit_scp_path') and\
            settings.has('remote_edit_temp_path'):
            log('Closed: "%s"' % settings.get('remote_edit_scp_path'))
            log('Deleted: "%s"' % os.path.dirname(settings.get('remote_edit_temp_path')))
            os.unlink(settings.get('remote_edit_temp_path'))
            os.rmdir(os.path.dirname(settings.get('remote_edit_temp_path')))
