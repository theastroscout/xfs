# XFS
File Synchronization With Your Remote Server Via SSH. Sublime Text 3 Plugin.

<br/>

# Requirements
1. MacOS
2. Sublime Text 3

<br/>

# Installation
1. Clone repository to your directory 
```
git clone https://github.com/hqdaemon/xfs XFS
```

2. Place XFS Folder into your Sublime Text 3 Packages Directory
```
/Users/YOUR_USER_NAME/Library/Application\ Support/Sublime\ Text\ 3/Packages/
```

<br/>

# Setup
1. Set configuration file

![Configuration](img/set-configuration.jpg?raw=true)

2. Place your specification and save file
```json
{
	"remoteDir": "/REMOTE_PATH_TO_SYNC/",
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
Folder and files have different methods.

![Usage](img/usage.jpg?raw=true)

<br />
<br />
<br />
<br />

## MIT License

Copyright (c) HQ • [hqmode.com](https://hqmode.com)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.