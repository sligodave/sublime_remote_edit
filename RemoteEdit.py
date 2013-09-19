
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
    settings = sublime.load_settings('RemoteEdit.sublime-settings')
    if settings.get('debug', False):
        print('[Remote Edit]: ' + str(msg))


def get_ssh_config(alias, window=None):
    """
    Find the scp configuration based on the alias supplied.
    Look in the current project and then the plugin's settings file.
    """
    if not window:
        window = sublime.active_window()

    settings = window.project_data()
    settings = {} if not settings else settings.get('remote_edit')
    settings = {} if not isinstance(settings, dict) else settings
    create_if_missing = settings.get('create_if_missing')
    settings = settings.get('ssh_configs')
    settings = {} if not isinstance(settings, dict) else settings
    config = settings.get(alias)

    settings = sublime.load_settings('RemoteEdit.sublime-settings')
    settings = {} if not settings else settings
    if create_if_missing is None:
        create_if_missing = settings.get('create_if_missing')
    settings = settings.get("ssh_configs")
    settings = {} if not isinstance(settings, dict) else settings
    if config is None:
        config = settings.get(alias)
    if config is not None:
        if create_if_missing is not None and not 'create_if_missing' in config:
            config['create_if_missing'] = create_if_missing
        return config


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
            elif to_path.find('@') == -1:
                # We were copying to local machine
                # and file doesn't exist on remote machine
                sublime.status_message('Could not get file, so creating it')
                open(to_path, 'w').close()


class RemoteEditOpenRemoteFilePromptCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.all_aliases = []

        settings = sublime.load_settings('RemoteEdit.sublime-settings')
        settings = {} if not settings else settings
        settings = settings.get("ssh_configs")
        settings = {} if not isinstance(settings, dict) else settings

        for alias, config in settings.items():
            alias = alias if config.get('address', alias) == alias else\
                [alias, 'Address: %s' % config.get('address', alias)]
            self.all_aliases.append(alias)

        settings = self.window.project_data()
        settings = {} if not settings else settings.get('remote_edit')
        settings = {} if not isinstance(settings, dict) else settings
        settings = settings.get('ssh_configs')
        settings = {} if not isinstance(settings, dict) else settings

        for alias, config in settings.items():
            alias = [alias, 'Address: %s' % config.get('address', alias)]
            self.all_aliases.append(alias)
        self.all_aliases.sort(key=lambda x: x[0])

        self.window.show_quick_panel(self.all_aliases, self.on_alias_done)

    def on_alias_done(self, selection):
        if selection < 0 or selection >= len(self.all_aliases):
            return
        self.alias = self.all_aliases[selection][0]

        self.window.show_input_panel(
            'Enter remote file to open:',
            '',
            self.on_path_done,
            None,
            None
            )

    def on_path_done(self, path):
        alias = self.alias
        del self.alias
        self.window.run_command(
            'remote_edit_open_remote_file',
            {'config_alias': alias, 'path': path}
        )


class RemoteEditOpenRemoteFileCommand(sublime_plugin.WindowCommand):
    def run(
            self,
            config_alias,
            path,
            override_create_if_missing=False,
            create_if_missing=True
        ):
        """
        Given a config alias and a path to a file on a remote server.
        Scp the file to a temp location on the local machine and open
        for editing. Record a record of the file so we know where to
        save it back to on the remote server, on save.
        """
        log('Open: %s "%s" %s %s' % (
            config_alias,
            path,
            override_create_if_missing,
            create_if_missing
            )
        )

        config = get_ssh_config(config_alias, self.window)
        if config is None:
            sublime.error_message('Cound not find config alias "%s".' %
                                                                config_alias)
            return
        if override_create_if_missing or not 'create_if_missing' in config:
            config['create_if_missing'] = create_if_missing
        log('Config: %s' % str(config))

        line_no = '0'
        if ':' in path:
            path, line_no = path.split(':', 1)

        scp_path = '%s:%s' % (config.get('address', config_alias), path)
        if 'username' in config:
            scp_path = '%s@%s' % (config['username'], scp_path)

        view = temp_path = None
        for cur_view in self.window.views():
            settings = cur_view.settings()
            if settings.get('is_remote_edit') and\
                settings.get('scp_path') == scp_path:
                view = cur_view
                temp_path = settings.get('temp_path')
                break

        if temp_path is None or view is None:
            file_name = os.path.basename(path)
            temp_path = tempfile.mkdtemp()
            temp_path = os.path.join(temp_path, file_name)

            scp(scp_path, temp_path, config['create_if_missing'])

            if not os.path.exists(temp_path):
                return

            temp_path_line_no = '%s:%s' % (temp_path, line_no)
            view = self.window.open_file(
                temp_path_line_no,
                sublime.ENCODED_POSITION
            )
            settings = view.settings()
            settings.set('scp_path', scp_path)
            settings.set('temp_path', temp_path)
            settings.set('create_if_missing', config['create_if_missing'])
            settings.set('is_remote_edit', True)
        log('Opened: "%s"' % scp_path)
        log('Temp: "%s"' % temp_path)
        self.window.focus_view(view)


class RemoteEditListener(sublime_plugin.EventListener):
    def on_post_save(self, view):
        """
        When a remote file is saved, save it back to the remote server.
        """
        settings = view.settings()
        if settings.get('is_remote_edit') and\
            settings.has('scp_path') and\
            settings.has('temp_path'):
            log('Saved: "%s"' % settings.get('scp_path'))
            scp(
                settings.get('temp_path'),
                settings.get('scp_path'),
                settings.get('create_if_missing', False)
            )

    def on_close(self, view):
        """
        When a remote file is closed delete the local temp file and directory.
        We also no longer keep a record of it in our remote files list.
        """
        settings = view.settings()
        if settings.get('is_remote_edit') and\
            settings.has('scp_path') and\
            settings.has('temp_path'):
            log('Closed: "%s"' % settings.get('scp_path'))
            log('Deleted: "%s"' % os.path.dirname(settings.get('temp_path')))
            os.unlink(settings.get('temp_path'))
            os.rmdir(os.path.dirname(settings.get('temp_path')))
