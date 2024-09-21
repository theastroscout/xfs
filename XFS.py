import sublime
import sublime_plugin
import os
import subprocess
from shutil import copyfile, rmtree
import json
import re

def statusbar(msg):
	sublime.active_window().status_message(' >>> [ XFS ] '+msg)
	print(msg)

# Upload Files Or Folders
def upload(conf):
	mkdirPath = conf['remoteDir']+conf['_clearDir'];

	ls = subprocess.Popen(['ssh', conf['ssh'], 'mkdir -p '+mkdirPath], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

	if conf['_fileName']:
		remoteDir = conf['remoteDir']+conf['_clearDir']+'/'+conf['_fileName']
		localDir = conf['_localDir']+conf['_clearDir']+'/'+conf['_fileName']
		cmd = 'rsync --chmod=a+rwx,g-w,o-w -a "'+localDir+'" "'+conf['ssh']+':\"'+remoteDir+'\""'
		ls = subprocess.Popen(cmd, shell=True)
		print('UPLOAD',cmd)
		statusbar('File Uploaded Complete 3')
	else:
		remoteDir = conf['remoteDir']+conf['_clearDir']+'/'
		localDir = conf['_localDir']+conf['_clearDir']+'/'
		cmd = 'rsync --chmod=a+rwx,g-w,o-w -a '+conf['excludePattern']+' "'+localDir+'" '+conf['ssh']+':"'+remoteDir + '"'
		ls = subprocess.Popen(cmd, shell=True)
		print('Upload Folder', cmd)
		statusbar('@XFS >>>> Folder Uploaded')

# Download Files Or Folders
def download(conf, self):
	if conf['_fileName']:
		remoteDir = conf['remoteDir']+conf['_clearDir']+'/'+conf['_fileName']
		localDir = conf['_localDir']+conf['_clearDir']+'/'+conf['_fileName']
		cmd = 'rsync -a "'+conf['ssh']+':\"'+remoteDir+'\"" "' + localDir + '"'
		ls = subprocess.Popen(cmd, shell=True)
		statusbar('File Downloaded Complete')
	else:
		statusbar('Folder Downloading...')
		remoteDir = conf['remoteDir']+conf['_clearDir']+'/'
		localDir = conf['_localDir']+conf['_clearDir']+'/'
		cmd = 'rsync -a '+conf['excludePattern']+' "'+conf['ssh']+':\"'+remoteDir+'\"" "'+localDir+'"'
		ls = subprocess.Popen(cmd, shell=True)
		statusbar('Folder Downloaded Complete')

	return True

# Delete Files Or Folders
def delete(conf,self,syncType=False):
	if conf['_fileName']:
		cmd = 'ssh ' + conf['ssh'] + ' rm '+conf['remoteDir']+conf['_clearDir']+'/'+conf['_fileName']
		ls = subprocess.Popen(cmd, shell=True)
		
		if syncType == 'both':
			filePath = conf['_localDir']+conf['_clearDir']+'/'+conf['_fileName']
			if os.path.exists(filePath):
				os.remove(filePath)

			sublime.set_timeout(lambda: self.window.run_command('revert'), 10)
			statusbar('Remote & Local Files Deleted Complete')
		else:
			statusbar('Remote File Deleted Complete')
	else:
		cmd = 'ssh ' + conf['ssh'] + ' rm -rf '+conf['remoteDir']+conf['_clearDir']
		ls = subprocess.Popen(cmd, shell=True)

		if syncType == 'both':
			targetFolder = conf['_localDir']+conf['_clearDir']
			if os.path.exists(targetFolder):
				rmtree(targetFolder)
			statusbar('Remote & Local Folders Deleted Complete')
		else:
			statusbar('Remote Folder Deleted Complete')

	return True

# Synchronize between Remote & Local Folders
def sync(conf,target=False):	
	localDir = conf['_localDir']+conf['_clearDir']
	remoteDir = conf['remoteDir']+conf['_clearDir']
	if re.search('/$', localDir) is None:
		localDir += '/'

	if re.search('/$', remoteDir) is None:
		remoteDir += '/'

	if target == 'remote':
		cmd = 'rsync --chmod=a+rwx,g-w,o-w -avc --delete '+conf['excludePattern']+' "'+localDir+'" "'+conf['ssh']+':\"'+remoteDir + '\""'
		ls = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out, err =  ls.communicate()
		out = out.decode('UTF-8')
		print(out)
		statusbar('Remote Folder Synchronized With Local Successfully')
	else:
		cmd = 'rsync -avc --delete '+conf['excludePattern']+' "'+conf['ssh']+':\"'+remoteDir+'\"" "'+localDir+'"'
		print('CMD:', cmd)
		ls = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out, err =  ls.communicate()
		out = out.decode('UTF-8')
		print(out)
		statusbar('Local Folder Synchronized With Remote Successfully')

global renameConf
# Rename Files Or Folders
def rename(newName=False):
	global renameConf
	if not newName:
		renameConf = False
		return False
	
	conf = renameConf
	if conf['_fileName']:
		remoteDir = conf['remoteDir']+conf['_clearDir']+'/'
		oldRemoteFile = remoteDir+conf['_fileName']
		newRemoteFile = remoteDir+newName
		cmd = 'ssh ' + conf['ssh'] + ' mv '+oldRemoteFile+' '+newRemoteFile
		ls = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

		localDir = conf['_localDir']+conf['_clearDir']+'/'
		oldLocalFile = localDir+conf['_fileName']
		newLocalFile = localDir+newName
		os.rename(oldLocalFile, newLocalFile)

		statusbar('File Renamed Successfully')
	else:
		rootChanged = False
		oldFolderName = os.path.basename(conf['_clearDir'])

		if conf['_filePath'] == conf['_clearDir']:
			rootChanged = True
			oldRemoteFolder = conf['remoteDir']
		else:
			oldRemoteFolder = conf['remoteDir']+conf['_clearDir']+'/'

		newRemoteFolder = re.sub(oldFolderName+'/$',newName+'/',oldRemoteFolder)

		oldLocalFolder = conf['_filePath']
		newLocalFolder = re.sub(oldFolderName+'$',newName,oldLocalFolder)

		cmd = 'ssh ' + conf['ssh'] + ' mv '+oldRemoteFolder+' '+newRemoteFolder

		ls = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out, err =  ls.communicate()
		out = out.decode('UTF-8')
		err = err.decode('UTF-8')

		if len(err):
			statusbar('\nAn Error Has Occurred While Folder Renaming')
			print(err)
		else:
			if rootChanged:
				confPath = conf['_localDir']+'xfs-config.json'
				f = open(confPath, 'r')
				clearConf = json.load(f)
				f.close()
				clearConf['remoteDir'] = newRemoteFolder
				with open(confPath, 'w') as outfile:
					json.dump(clearConf, outfile, indent=4)

			os.rename(oldLocalFolder, newLocalFolder)
			statusbar('Folder Renamed Successfully')

# Get Configuration File
def getConfig(path):
	chunks = path.split('/')
	while len(chunks):
		localDir = '/'.join(chunks)
		if os.path.isfile(localDir + '/xfs-config.json'):
			f = open(localDir + '/xfs-config.json',)
			conf = json.load(f)
			f.close()

			conf['_filePath'] = path
			conf['_localDir'] = localDir
			if os.path.isfile(path):
				conf['_fileName'] = os.path.basename(path)
				conf['_clearDir'] = os.path.dirname(path.replace(localDir,''))
			else:
				conf['_fileName'] = False
				conf['_clearDir'] = path.replace(localDir,'')

			
			print('>>>>',conf['_clearDir'])
			if conf['_clearDir']+'/' == conf['_localDir']:
				conf['_clearDir'] = ''

			if len(conf['exclude']) > 1:
				exclude = ','.join('"{0}"'.format(e) for e in conf['exclude'])
				conf['excludePattern'] = '--exclude={'+exclude+'}'
			elif len(conf['exclude']) == 1:
				conf['excludePattern'] = '--exclude "'+conf['exclude'][0]+'"'
			else:
				conf['excludePattern'] = ''

			return conf;
			break
		chunks.pop()		

	return False

# Upload On Save
class XfsSyncCommand(sublime_plugin.ViewEventListener):
	def on_post_save(self):
		conf = getConfig(self.view.file_name())
		if not conf or not conf['upload_on_save']:
			return False
		upload(conf)

# Upload File
class XfsUploadFileCommand(sublime_plugin.WindowCommand):
	def run(self, paths=[]):
		conf = getConfig(paths[0])
		if not conf:
			return False
		upload(conf)

	def is_visible(args, paths=[]):
		if os.path.isdir(paths[0]) or not getConfig(paths[0]):
		 	return False
		else:
			return True

# Download File
class XfsDownloadFileCommand(sublime_plugin.WindowCommand):
	def run(self, paths=[]):
		conf = getConfig(paths[0])
		if not conf:
			return False
		download(conf, self)

	def is_visible(args, paths=[]):
		if os.path.isdir(paths[0]) or not getConfig(paths[0]):
		 	return False
		else:
			return True

# Upload Folder
class XfsUploadFolderCommand(sublime_plugin.WindowCommand):
	def run(self, paths=[]):
		conf = getConfig(paths[0])
		if not conf:
			return False

		upload(conf)

	def is_visible(args,paths=[]):
		if os.path.isfile(paths[0]) or not getConfig(paths[0]):
		 	return False
		else:
			return True

# Downlload Folder
class XfsDownloadFolderCommand(sublime_plugin.WindowCommand):
	def run(self, paths=[]):
		conf = getConfig(paths[0])
		if not conf:
			return False

		download(conf, self)

	def is_visible(args,paths=[]):
		if os.path.isfile(paths[0]) or not getConfig(paths[0]):
		 	return False
		else:
			return True

# Sync Local Folder
class XfsSyncLocalFolderCommand(sublime_plugin.WindowCommand):
	def run(self, paths=[]):
		conf = getConfig(paths[0])
		if not conf:
			return False
		sync(conf, 'local')

	def is_visible(args,paths=[]):
		if os.path.isfile(paths[0]) or not getConfig(paths[0]):
		 	return False
		else:
			return True

# Sync Remote Folder
class XfsSyncRemoteFolderCommand(sublime_plugin.WindowCommand):
	def run(self, paths=[]):
		conf = getConfig(paths[0])
		if not conf:
			return False
		sync(conf, 'remote')

	def is_visible(args,paths=[]):
		if os.path.isfile(paths[0]) or not getConfig(paths[0]):
		 	return False
		else:
			return True

# Delete Remote File
class XfsDeleteRemoteFileCommand(sublime_plugin.WindowCommand):
	def run(self, paths=[]):
		conf = getConfig(paths[0])
		if not conf:
			return False
		delete(conf, self, 'remote')

	def is_visible(args,paths=[]):
		if os.path.isdir(paths[0]) or not getConfig(paths[0]):
		 	return False
		else:
			return True

# Delete Remote & Local File
class XfsDeleteBothFilesCommand(sublime_plugin.WindowCommand):
	def run(self, paths=[]):
		conf = getConfig(paths[0])
		if not conf:
			return False
		delete(conf, self, 'both')

	def is_visible(args,paths=[]):
		if os.path.isdir(paths[0]) or not getConfig(paths[0]):
		 	return False
		else:
			return True

# Delete Remote Folder
class XfsDeleteRemoteFolderCommand(sublime_plugin.WindowCommand):
	def run(self, paths=[]):
		conf = getConfig(paths[0])
		if not conf:
			return False
		delete(conf, self, 'remote')

	def is_visible(args,paths=[]):
		if os.path.isfile(paths[0]) or not getConfig(paths[0]):
		 	return False
		else:
			return True

# Delete Remote & Local Folders
class XfsDeleteBothFoldersCommand(sublime_plugin.WindowCommand):
	def run(self, paths=[]):
		conf = getConfig(paths[0])
		if not conf:
			return False
		delete(conf, self, 'both')

	def is_visible(args,paths=[]):
		if os.path.isfile(paths[0]) or not getConfig(paths[0]):
		 	return False
		else:
			return True

# Rename File
class XfsRenameFileCommand(sublime_plugin.WindowCommand):
	def run(self, paths=[]):
		conf = getConfig(paths[0])
		if not conf:
			return False
		global renameConf
		renameConf = conf
		self.window.show_input_panel('Rename File',conf['_fileName'],rename,None,rename)

	def is_visible(args,paths=[]):
		if os.path.isdir(paths[0]) or not getConfig(paths[0]):
		 	return False
		else:
			return True	

# Rename Folder
class XfsRenameFolderCommand(sublime_plugin.WindowCommand):
	def run(self, paths=[]):
		conf = getConfig(paths[0])
		if not conf:
			return False
		global renameConf
		renameConf = conf
		self.window.show_input_panel('Rename Folder',os.path.basename(conf['_clearDir']),rename,None,rename)

	def is_visible(args,paths=[]):
		if os.path.isfile(paths[0]) or not getConfig(paths[0]):
		 	return False
		else:
			return True		

# Configuration
class XfsConfigurationCommand(sublime_plugin.WindowCommand):
	def run(self, paths=[]):
		print('SETTING UP CONFIG')
		if len(paths):
			confPath = paths[0]+'/xfs-config.json'
			if not os.path.isfile(confPath):
				defaultConf = sublime.packages_path() + '/XFS/XFS.default-config'
				print('Create New Config From: ', defaultConf, 'To:', confPath)
				copyfile(defaultConf, confPath)

			self.window.open_file(confPath, sublime.ENCODED_POSITION)

	def is_visible(args,paths=[]):
		return True