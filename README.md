RemoteEdit
==========

Open a file from a remote server locally, edit and seemlessly save back remotely again.

Feed it a preconfigured alias for a remote machine and a path on that machine from the command line or
use the GUI prompt to connect to your preconfigured servers and walk their directories.
You can also provide a server that is not preconfigured at this stage.

This will scp that file to a temp location locally for editing but will save all save events to the remote server too.

When you close the file, the local temp file is deleted.

NOTE: If sublime is closed and reopened, the temp file no longer has it's connection with the remote machine and it's source.
All saves will only happen to the local file at that stage.


## Installation:


### Git

Clone this repository into your Sublime Text *Packages* directory.

    git clone https://github.com/sligodave/sublime_remote_edit.git RemoteEdit


## Configure:

### Settings file:

In the file:

    Packages/User/RemoteEdit.sublime-settings

Create an alias, an alias points to a configuration for a specific server.

```json
	{
		"debug": false,
		"ssh_configs": {
			"ALIASNAME": {
				// Address of the remote server
				// Not required, will default to the "ALIAS_NAME" string
				"address": "IPADDRESS_OR_SERVERNAME",
				// Username to log into server with
				// Not required, the command line scp will default it to current user
				"username": "USERNAME_ON_REMOTE_MACHINE"
				// NOTE: Remember, to authenticate you need to have your pub key
				// registered in the remote server ssh's authorized_keys file.,
				"create_if_missing": false
			},
		}
	}
```

NOTE: no passwords are supported, you need to register your public key with the server.

[Passwordless ssh](http://www.linuxproblem.org/art_9.html)

Once you have your keys generated you can use this each time to send your pub key to a remote machine:

```bash
    cat ~/.ssh/id_rsa.pub | ssh USERNAME@REMOTE_MACHINE 'cat >> .ssh/authorized_keys'
```

### Project file:

In your current project file, you can also add aliases:

```json
	{
		"folders":
		[
			{
			}
		],
		"remote_edit":
		{
			"ssh_configs":
			{
				"ALIASNAME":
				{
					"address": "IPADDRESS_OR_SERVERNAME",
					"username": "USERNAME_ON_REMOTE_MACHINE",
					"create_if_missing": false
				}
			}
		}
	}
```


## Usage:

### With GoTo Anywhere command:

    "Remote Edit: Open Remote File Prompt"

Will prompt for an "alias" and then allows you to walk on the remote machine.

OR

You can use this to provide a new server that is not already configured.


### From command line:

Add the script to your path.
Invoke it with:

    > subl_remote_edit ALIAS PATH_ON_REMOTE_MACHINE


NOTE: If alias doesn't exist, it's the same as an empty alias configuration. In that case, the alias will be treated like the address of the server and everything else will default.


## Other Commands in GoTo Anywhere Panel:

    "Remote Edit: Reload All Remote Files"

Will reload all remote files.

    "Remote Edit: Reload Current Remote File"

Will reload the current file if it's a remote file.


## NOTES:

This is a work in progress!

Requires your ssh public key to be registered with the remote machines ssh

Requires scp to be available on the command line

It's working well but there may be bugs.

While sublime is open the local temp file will remember where it came from, so it'll save back when a save happens.
However, if you close sublime and open it again, that link is lost. So you are left with only a local copy of the file with no knowledge of it's remote source. I may change this and record the link in an external file at some stage.

Closing and reopening the temp file will also break the link it has to it's remote origin.

Basically, a temp file remembers it's remote origin as long as it remains open and sublime text remains open.


## ToDo:



## Issues and suggestions:

Fire on any issues or suggestions you have.


## Copyright and license
Copyright 2013 David Higgins

[MIT License](LICENSE)
