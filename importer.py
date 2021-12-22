import sys
import subprocess
import pkg_resources

class Importer:

	@staticmethod
	def verifyLibs(required):
		installed = {pkg.key for pkg in pkg_resources.working_set}
		missing = required - installed

		if missing:
			print("Installing dependencies...")
			python = sys.executable
			subprocess.check_call([python, '-m', 'pip', 'install', *missing], stdout=subprocess.DEVNULL)