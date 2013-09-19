RemoteEdit
==========

Open a file from a remote server locally, edit and save back remotely again.

## Installation:


### Git

Clone this repository into your Sublime Text *Packages* directory.

    git clone https://github.com/sligodave/sublime_remote_edit.git RemoteEdit


## Configure:

### Settings file:

In the file:

Packages/User/RemoteEdit.sublime-settings

Create aliass, an alias points to a configuration for a specific server.

```
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
				// registered in the remote server ssh's authorized_keys file.
			},
		}
	}
```

Take note though, no passwords are supported, you need to register your public key with the server.

    [Passwordless ssh](http://www.linuxproblem.org/art_9.html)

### Project file:

In your current project file, you can also add aliases:

```
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

Will prompt for an "alias" and then a "path" on the remote machine. 

### From command line:

Add the script to your path.
Invoke it with:

    > subl_remote_edit ALIAS PATH_ON_REMOTE_MACHINE


## NOTES:

This is a work in progress!

Requires your ssh public key to be registered with the remote machines ssh

Requires scp to be available on the command line

It's working away but there may be bugs.

While sublime is open the local temp file will remember where it came from, so it'll save back when a save happens.
However, if you close sublime and open it again, that link is lost. So you are left with only a local copy of the file with no knowledge of it's remote source. I may change this and record the link in an external file at some stage.


## Issues and suggestions:

Fire on any issues or suggestions you have.


## Copyright and license
Copyright 2013 David Higgins

[MIT License](LICENSE)
