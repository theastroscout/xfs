# XFS
Sync files with remote server using Rsync via SSH. Sublime Text 3 Plugin.

<br/>

# Requirements
- Sublime Text 3
- Rsync

<br/>

# Installation
1. Clone repository to your directory 
```
git clone https://github.com/theastroscout/xfs XFS
```

2. Place XFS Folder into your Sublime Text 3 Packages Directory
```
/Users/YOUR_USER_NAME/Library/Application\ Support/Sublime\ Text\ 3/Packages/
```

<br/>

# Setup

![Configuration](img/set-configuration.jpg?raw=true)

```json
{
	"remoteDir": "/REMOTE_PATH_TO_SYNC",
	"ssh": "USER_NAME@HOST_NAME",
	"upload_on_save": false,
	"exclude": [
		"node_modules",
		".git",
		".DS_Store",
		"Thumbs.db",
		"/venv/",
		".svn",
		".hg",
		"_darcs",
		".sublime-(project|workspace)",
		"xfs-config.json"
	]
}
```

<br/>

# Usage

![Usage](img/usage.jpg?raw=true)

<br />
<br />
<br />
<br />

## CC0 1.0 Universal (CC0 1.0) Public Domain Dedication

The person who associated a work with this deed has dedicated the work to the public domain by waiving all of his or her rights to the work worldwide under copyright law, including all related and neighbouring rights, to the extent allowed by law.

You can copy, modify, distribute, and perform the work, even for commercial purposes, all without asking permission.

The work is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the work or the use or other dealings in the work.

For more information, see <https://creativecommons.org/publicdomain/zero/1.0/>